"""Estimasi panjang badan TANPA referensi skala (DEC-016) -- bukan pengukuran.

Foto tanpa alas berukuran diketahui TIDAK dapat diukur secara absolut
(scale ambiguity: S/d = s/f). Mode ini memberi PERKIRAAN kasar dengan
dua prior, dipilih lewat gerbang fisiologis:

1. Prior kepala (top-down): skala = `NEWBORN_HEAD_CM / diameter_kepala_px`
   -- akurat bila kamera mendekati tegak lurus (kepala tampak bulat).
2. Prior perspektif (oblique): skala = `camera_height_cm / focal_px`
   -- model pinhole sederhana dengan asumsi tinggi kamera dan focal
   panjang; focal diestimasi dari lebar citra (lensa HP ~0.72 x width).

Gerbang: rasio diameter-kepala/panjang-badan bayi fisiologis ~0.15-0.35.
Bila rasio terukur di dalam rentang itu, kepala dipercaya (band +-15%);
bila tidak (foto miring/samping), dipakai prior perspektif (band +-30%).

Hasil SELALU diberi confidence rendah dan tidak pernah boleh disajikan
sebagai pengukuran (RESPONSIBLE_AI.md, DEC-016). Ini fitur eksplorasi
untuk demo, bukan klaim paper.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from cv.segment import ColorSegmenter, endpoints_from_mask

# Prior medis: diameter kepala bayi baru lahir (OCF ~34-36 cm / pi).
NEWBORN_HEAD_CM = 11.0
# Asumsi tinggi kamera dari bidang alas untuk foto amatir (parameter).
DEFAULT_CAMERA_HEIGHT_CM = 60.0
# Heuristik focal panjang HP: f_px ≈ 0.72 x lebar citra (FOV ~65-75 deg).
DEFAULT_FOCAL_FRACTION = 0.72
# Rentang fisiologis rasio diameter kepala : panjang badan.
HEAD_RATIO_MIN, HEAD_RATIO_MAX = 0.15, 0.32
# CATATAN: gate STRICT (<, bukan <=). Bila kepala lebih besar dari zona
# kepala (0.32 x span), lebar terukur jenuh di ~0.32 x span; MAX 0.32
# menjamin kepala non-fisiologis selalu jatuh ke prior perspektif.
ESTIMATE_CONFIDENCE = 0.3   # selalu rendah: ini perkiraan, bukan ukuran


@dataclass
class EstimateResult:
    ok: bool
    length_cm: float | None = None
    confidence: float = 0.0
    method: str = "head_prior"
    uncertainty_rel: float = 0.15
    reasons: list = field(default_factory=list)
    head_diameter_px: float | None = None
    span_px: float | None = None


def estimate_length_no_reference(
        image: np.ndarray,
        head_cm: float = NEWBORN_HEAD_CM,
        camera_height_cm: float = DEFAULT_CAMERA_HEIGHT_CM,
        focal_px: float | None = None) -> EstimateResult:
    """Perkiraan panjang badan dari satu foto tanpa referensi skala.

    Hanya sah sebagai ESTIMASI kasar; confidence 0.3, band +-15% (prior
    kepala) atau +-30% (prior perspektif). Gagal (ok=False) bila
    foreground tidak terdeteksi.
    """
    if image is None or image.size == 0:
        return EstimateResult(ok=False, reasons=["citra kosong"])

    # 1. Foreground: warna tepi bingkai = latar dominan (selimut/kasur).
    bg_color = ColorSegmenter._estimate_mat_color(image)
    seg = ColorSegmenter(mat_color=bg_color).segment(image)
    if not seg.ok:
        return EstimateResult(ok=False, reasons=[seg.reason])

    ends = endpoints_from_mask(seg.mask)
    if ends is None:
        return EstimateResult(ok=False, reasons=["siluet terlalu kecil"])

    # Span TUBUH yang robust: proyeksi piksel ke sumbu PCA, ambil rentang
    # persentil 1-99 -- lengan/kaki yang menjulur tidak menggembungkan span.
    span_px = _robust_span(seg.mask)
    if span_px <= 1.0:
        return EstimateResult(ok=False, reasons=["span badan tidak valid"])

    # 2. Kepala: diameter = lebar maksimum kulit di zona ujung siluet
    #    (scan dari ujung, berhenti pada konstriksi leher). Bahu/badan yang
    #    berpakaian tidak mengganggu karena profil dihitung pada piksel
    #    KULIT saja.
    head_px = _head_diameter_px(image, seg.mask, span_px)

    # 3. Gerbang fisiologis + kebulatan: prior kepala hanya untuk kamera
    #    mendekati tegak lurus (kepala tampak bulat, rasio ~0.15-0.32).
    if head_px is not None:
        ratio = head_px / span_px
        if HEAD_RATIO_MIN < ratio < HEAD_RATIO_MAX:
            length_cm = span_px * head_cm / head_px
            return EstimateResult(
                ok=True, length_cm=round(length_cm, 1),
                confidence=ESTIMATE_CONFIDENCE, method="head_prior",
                uncertainty_rel=0.15,
                head_diameter_px=round(head_px, 1), span_px=round(span_px, 1),
            )

    # 4. Fallback: prior perspektif (foto miring/samping atau tanpa kulit).
    # focal_px=0 (falsy) sengaja berarti "tidak diberikan" -> pakai heuristik;
    # nilai eksplisit 0 tidak pernah valid sebagai focal panjang.
    f_px = focal_px if focal_px else DEFAULT_FOCAL_FRACTION * image.shape[1]
    if not (np.isfinite(f_px) and f_px > 0
            and np.isfinite(camera_height_cm) and camera_height_cm > 0):
        return EstimateResult(ok=False, reasons=["parameter perspektif tidak valid"])
    length_cm = span_px * camera_height_cm / f_px
    reasons = []
    if head_px is not None:
        reasons.append(f"rasio kepala {head_px / span_px:.2f} di luar rentang "
                       f"fisiologis; prior kepala ditolak")
    return EstimateResult(
        ok=True, length_cm=round(length_cm, 1),
        confidence=ESTIMATE_CONFIDENCE, method="perspective_prior",
        uncertainty_rel=0.30, reasons=reasons,
        head_diameter_px=round(head_px, 1) if head_px else None,
        span_px=round(span_px, 1),
    )


def _robust_span(mask: np.ndarray, q: float = 0.005) -> float:
    """Panjang siluet sepanjang sumbu utama, robust terhadap ekstremitas.

    Proyeksi piksel mask ke sumbu PCA; rentang persentil q..(1-q) dipakai
    supaya lengan/kaki yang menjulur (massa kecil) tidak menggembungkan
    hasil, tanpa memangkas ujung-ujung shape yang bersih (q kecil).
    """
    ys, xs = np.nonzero(mask)
    if len(xs) < 16:
        return 0.0
    pts = np.column_stack([xs.astype(np.float64), ys.astype(np.float64)])
    center = pts.mean(axis=0)
    cov = np.cov(pts.T)
    eigvals, eigvecs = np.linalg.eigh(cov)
    axis = eigvecs[:, int(np.argmax(eigvals))]
    proj = (pts - center) @ axis
    lo, hi = np.quantile(proj, q), np.quantile(proj, 1 - q)
    return float(hi - lo)

def _head_diameter_px(image: np.ndarray, foreground: np.ndarray, span_px: float,
                      zone_frac: float = 0.32, neck_frac: float = 0.75,
                      bin_px: float = 8.0) -> float | None:
    """Diameter kepala dari profil lebar KULIT di zona ujung siluet.

    Sumbu badan dari PCA; piksel kulit (YCrCb) diproyeksikan ke sumbu dan
    sumbu tegak lurusnya; lebar per-bin dihitung. Dari tiap ujung, scan
    ke dalam: lebar maksimum berjalan sebelum konstriksi pertama (leher,
    < `neck_frac` x maksimum berjalan) = diameter kepala. Ujung dengan
    lebar kandidat terbesar dipilih (wajah vs kaki). None bila tidak ada
    kulit. Bahu/badan berpakaian tidak mengganggu: profil hanya dari
    piksel kulit.
    """
    ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
    skin = ((ycrcb[:, :, 1] >= 133) & (ycrcb[:, :, 1] <= 173)
            & (ycrcb[:, :, 2] >= 77) & (ycrcb[:, :, 2] <= 127)) & foreground
    ys, xs = np.nonzero(skin)
    if len(xs) < 64:
        return None
    pts = np.column_stack([xs.astype(np.float64), ys.astype(np.float64)])
    center = pts.mean(axis=0)
    cov = np.cov(pts.T)
    evals, evecs = np.linalg.eigh(cov)
    axis = evecs[:, int(np.argmax(evals))]
    perp = np.array([-axis[1], axis[0]])
    proj = (pts - center) @ axis
    pperp = (pts - center) @ perp
    zone = zone_frac * span_px

    best = 0.0
    for end in (float(proj.min()), float(proj.max())):
        sel = np.abs(proj - end) <= zone
        if int(sel.sum()) < 16:
            continue
        lo = float(proj[sel].min())
        bins: dict[int, list[float]] = {}
        for p, q in zip(proj[sel], pperp[sel]):
            bins.setdefault(int((p - lo) / bin_px), []).append(q)
        # Scan selalu DARI ujung siluet ke dalam: untuk ujung max, bin
        # dibalik (naik dari ujung). Tanpa ini, ujung max ter-scan dari
        # leher ke kepala dan torso yang lebih lebar bisa dikira kepala.
        keys = sorted(bins, reverse=True) if end == float(proj.max()) \
            else sorted(bins)
        run_max = 0.0
        head_w = 0.0
        for k in keys:
            w = float(np.ptp(bins[k]))
            if w > run_max:
                run_max = w
            elif w < neck_frac * run_max:
                break            # konstriksi leher: kepala berakhir
            head_w = run_max
        best = max(best, head_w)
    return best if best >= 16 else None
