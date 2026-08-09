"""Demo kanal visual: pipeline + citra overlay hasil (buat video & verifikasi).

Jalankan (env datsci aktif):
    python scripts/demo_cv.py                    # alas polos sintetis (markerless)
    python scripts/demo_cv.py <foto.jpg>         # foto asli (harus ada alas polos)

Keluaran: results/cv/demo_overlay.png -- citra masukan + 4 sudut alas
terdeteksi (hijau), mask segmentasi (kuning), endpoint kepala/tumit (merah),
dan teks hasil ukur; atau teks DITOLAK + alasan bila QC/gate menolak.

CATATAN PRIVASI: jangan taruh foto balita nyata di repo publik (klaim
RESPONSIBLE_AI.md); pakai boneka/proxy untuk artefak yang di-commit.
"""

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root
sys.path.insert(0, "tests")  # helper citra sintetis

from cv.aruco import draw_overlay, rectify
from cv.estimate import estimate_length_no_reference
from cv.mat_corners import detect_mat_corners
from cv.pipeline import measure_length
from cv.quality import ImageQC
from cv.segment import ColorSegmenter
from _cv_synth import SPEC, STANDARD_MAT_COLOR, synth_plain_mat_with_body

RECT_PX_PER_CM = 10.0


def _load_input(path: str | None) -> tuple[np.ndarray, str, float | None, object, object]:
    """(citra, sumber, panjang_asli_cm_atau_None, segmenter, image_qc)."""
    if path is None:
        img, _, _, body_cm = synth_plain_mat_with_body()
        return (img, "sintetis (alas polos)", body_cm,
                ColorSegmenter(mat_color=STANDARD_MAT_COLOR), ImageQC(min_blur_var=1.0))
    img = cv2.imread(path)
    if img is None:
        raise SystemExit(f"tidak bisa membaca {path}")
    return img, path, None, ColorSegmenter(), ImageQC()


def _draw_result(out: np.ndarray, r, ground_truth: float | None, source: str,
                 estimate=None) -> None:
    if r.ok:
        (x1, y1), (x2, y2) = r.endpoints_px
        cv2.circle(out, (x1, y1), 6, (0, 0, 255), -1)
        cv2.circle(out, (x2, y2), 6, (0, 0, 255), -1)
        cv2.line(out, (x1, y1), (x2, y2), (0, 0, 255), 2)
        label = f"length={r.length_cm} cm | {r.model} | conf={r.confidence}"
        cv2.putText(out, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                    0.9, (0, 0, 255), 2)
    elif estimate is not None and estimate.ok:
        band = round(estimate.length_cm * estimate.uncertainty_rel, 1)
        msg = (f"ESTIMASI ~{estimate.length_cm} cm (tanpa alas, +-{band} cm, "
               f"{estimate.method})")
        cv2.putText(out, msg, (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (0, 0, 255), 2)
        cv2.putText(out, f"DITOLAK sebagai pengukuran: {r.qc_reasons[0] if r.qc_reasons else '?'}",
                    (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    else:
        cv2.putText(out, f"DITOLAK: {r.qc_reasons[0] if r.qc_reasons else '?'}",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)


def main() -> None:
    img_path = sys.argv[1] if len(sys.argv) > 1 else None
    img, source, ground_truth, seg, qc = _load_input(img_path)

    r = measure_length(img, SPEC, segmenter=seg, image_qc=qc)
    estimate = None
    if not r.ok and "alas tidak terdeteksi" in "; ".join(r.qc_reasons):
        # Mode ESTIMASI (DEC-016): tanpa referensi skala, bukan pengukuran.
        estimate = estimate_length_no_reference(img)
        if estimate.ok:
            band = round(estimate.length_cm * estimate.uncertainty_rel, 1)
            print(f"[{source}] ESTIMASI ~{estimate.length_cm} cm "
                  f"(tanpa alas, +-{band} cm, {estimate.method})")
        else:
            print(f"[{source}] DITOLAK: {r.qc_reasons}")
    elif r.ok:
        gt = f" (asli={ground_truth} cm)" if ground_truth is not None else ""
        print(f"[{source}] terukur={r.length_cm} cm{gt} | model={r.model} "
              f"| confidence={r.confidence} | lat={r.latency_s}s")
    else:
        print(f"[{source}] DITOLAK: {r.qc_reasons}")

    det = detect_mat_corners(img, SPEC, mat_color=STANDARD_MAT_COLOR)
    out = draw_overlay(img, det)

    if r.ok:
        # Mask segmentasi (koordinat citra teregistrasi) di-warp balik ke citra
        # asli agar overlay sejajar dengan foto.
        rect = rectify(img, det, SPEC, px_per_cm=RECT_PX_PER_CM)
        mask = (seg.segment(rect).mask.astype(np.uint8)) * 255
        scale = np.array([[RECT_PX_PER_CM, 0, 0], [0, RECT_PX_PER_CM, 0],
                          [0, 0, 1]], dtype=np.float64)
        mask_orig = cv2.warpPerspective(mask, np.linalg.inv(scale @ det.homography),
                                        (img.shape[1], img.shape[0]))
        overlay = out.copy()
        overlay[mask_orig > 0] = (0, 200, 255)          # BGR: kuning-oranye
        out = cv2.addWeighted(overlay, 0.45, out, 0.55, 0)

    _draw_result(out, r, ground_truth, source, estimate)

    out_path = Path("results/cv/demo_overlay.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), out)
    print(f"overlay tersimpan: {out_path}")


if __name__ == "__main__":
    main()
