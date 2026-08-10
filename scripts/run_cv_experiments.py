"""Runner eksperimen kanal visual pada foto asli (experiments/src -> results).

Cara pakai (env datsci):
    python scripts/run_cv_experiments.py

Membaca semua gambar di experiments/src/**, menjalankan pipeline kanal
visual untuk tiap foto, lalu menulis:
- experiments/results/overlay/<group>/<nama>.png  (overlay, grup babies
  di-gitignore demi privasi)
- experiments/results/report.csv                  (tabel hasil lengkap)

Konfigurasi per gambar: `experiments/manifest.csv` (opsional) dengan kolom
image, mat_width_cm, mat_height_cm, mat_color_b/g/r (BGR, sama dengan
konvensi cv/). Gambar tanpa baris manifest memakai spesifikasi produk
(60x100 cm, warna standar). Contoh baris untuk foto yoga mat biru
(Wikimedia, standar 183x61 cm):
    Gaim_Yoga_Mat_1_2019-05-15.jpg,183,61,199,66,37

Kolom report:
- group       : subfolder sumber (mats / babies / ...)
- image       : nama berkas
- det_nocolor : deteksi alas tanpa signature warna (keseragaman saja)
- det_color   : deteksi alas dengan signature warna (spec per manifest)
- reason      : alasan penolakan (bila gagal)
- length_cm   : hasil ukur (bila lolos)
- confidence  : confidence pipeline
- model       : segmenter yang dipakai
- latency_ms  : waktu pipeline
- est_cm      : ESTIMASI tanpa referensi (DEC-016), bila pengukuran ditolak
- est_method  : head_prior / perspective_prior
- est_band    : band ketidakpastian (+-cm)
"""

import csv
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root

from cv.aruco import MatSpec, draw_overlay, rectify
from cv.estimate import measure_or_estimate
from cv.mat_corners import PRODUCT_MAT_COLOR, detect_mat_corners
from cv.pipeline import measure_length
from cv.quality import ImageQC
from cv.segment import ColorSegmenter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "experiments" / "src"
OUT = ROOT / "experiments" / "results"
EXT = {".jpg", ".jpeg", ".png", ".avif"}   # .avif dikonversi via ffmpeg
MANIFEST = ROOT / "experiments" / "manifest.csv"


def _load_manifest() -> dict[str, dict]:
    """manifest.csv -> {nama_gambar: {spec, mat_color}} (kosong bila tak ada)."""
    if not MANIFEST.exists():
        return {}
    out = {}
    with open(MANIFEST, newline="") as f:
        for row in csv.DictReader(f):
            img = row["image"].strip()
            spec = MatSpec(width_cm=float(row["mat_width_cm"]),
                           height_cm=float(row["mat_height_cm"]))
            color = None
            if row.get("mat_color_b", "").strip():
                color = (int(row["mat_color_b"]), int(row["mat_color_g"]),
                         int(row["mat_color_r"]))
            out[img] = {"spec": spec, "mat_color": color}
    return out


def _draw_result(out: cv2.Mat, r, estimate) -> None:
    if r.ok:
        (x1, y1), (x2, y2) = r.endpoints_px
        cv2.circle(out, (x1, y1), 6, (0, 0, 255), -1)
        cv2.circle(out, (x2, y2), 6, (0, 0, 255), -1)
        cv2.line(out, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.putText(out, f"length={r.length_cm} cm | {r.model} | conf={r.confidence}",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
    elif estimate is not None and estimate.ok:
        band = round(estimate.length_cm * estimate.uncertainty_rel, 1)
        cv2.putText(out, f"ESTIMASI ~{estimate.length_cm} cm (+-{band} cm, "
                         f"{estimate.method})",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    else:
        msg = f"DITOLAK: {r.qc_reasons[0] if r.qc_reasons else '?'}"
        cv2.putText(out, msg, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)


def main() -> None:
    images = sorted(p for p in SRC.rglob("*") if p.suffix.lower() in EXT)
    if not images:
        raise SystemExit(f"tidak ada gambar di {SRC}")
    manifest = _load_manifest()
    overlay_dir = OUT / "overlay"
    overlay_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    baby_counter = 0
    for path in images:
        img = cv2.imread(str(path))
        if img is None and path.suffix.lower() == ".avif":
            import shutil
            import subprocess
            if shutil.which("ffmpeg") is None:
                print(f"[skip] {path.name}: butuh ffmpeg untuk .avif "
                      f"(install: apt install ffmpeg / conda install -c "
                      f"conda-forge ffmpeg)")
                continue
            tmp = OUT / "overlay" / "_tmp_avif.png"
            tmp.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["ffmpeg", "-y", "-i", str(path), str(tmp)],
                           check=True, capture_output=True)
            img = cv2.imread(str(tmp))
            tmp.unlink(missing_ok=True)
        if img is None:
            print(f"[skip] tidak terbaca: {path}")
            continue

        cfg = manifest.get(path.name, {})
        spec = cfg.get("spec", MatSpec(width_cm=60.0, height_cm=100.0))
        mat_color = cfg.get("mat_color", PRODUCT_MAT_COLOR)

        det_plain = detect_mat_corners(img, spec)
        det_prod = detect_mat_corners(img, spec, mat_color=mat_color)

        t0 = time.perf_counter()
        pr = measure_or_estimate(
            img, mat_spec=spec, image_path=path,
            segmenter=ColorSegmenter(mat_color=mat_color),
            image_qc=ImageQC(),
            detector=lambda im, sp: detect_mat_corners(im, sp, mat_color=mat_color),
        )
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        res, estimate = pr.measurement, pr.estimate

        # Rasio sisi quad di RUANG PIKsel (independen dari spec -- bukan
        # tautologi homografi). Yoga mat asli ~3.0.
        det_px_ratio = ""
        if det_prod.ok:
            p = det_prod.image_points
            sides = sorted(np.linalg.norm(p[(i + 1) % 4] - p[i]) for i in range(4))
            det_px_ratio = round(sides[2] / max(1.0, sides[0]), 2)


        overlay = draw_overlay(img, det_prod if det_prod.ok else det_plain)
        if res.ok:
            rect = rectify(img, det_prod, spec, px_per_cm=10.0)
            mask = (ColorSegmenter(mat_color=mat_color)
                    .segment(rect).mask.astype("uint8")) * 255
            scale = np.array([[10, 0, 0], [0, 10, 0], [0, 0, 1]], dtype=np.float64)
            mask_orig = cv2.warpPerspective(mask, np.linalg.inv(scale @ det_prod.homography),
                                            (img.shape[1], img.shape[0]))
            ov = overlay.copy()
            ov[mask_orig > 0] = (0, 200, 255)
            overlay = cv2.addWeighted(ov, 0.45, overlay, 0.55, 0)
        _draw_result(overlay, res, estimate)
        group_dir = overlay_dir / path.parent.name
        group_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(group_dir / f"{path.stem}.png"), overlay)

        if path.parent.name == "babies":
            baby_counter += 1
        rows.append({
            "group": path.parent.name,
            "image": (f"baby-{baby_counter:02d}"
                      if path.parent.name == "babies" else path.name),
            "det_nocolor": det_plain.ok,
            "det_color": det_prod.ok,
            "det_px_ratio": det_px_ratio,
            "reason": "; ".join(res.qc_reasons) if not res.ok else "",
            "length_cm": res.length_cm if res.ok else "",
            "confidence": res.confidence if res.ok else "",
            "model": res.model,
            "latency_ms": latency_ms,
            "est_cm": estimate.length_cm if estimate and estimate.ok else "",
            "est_method": estimate.method if estimate and estimate.ok else "",
            "est_band": round(estimate.length_cm * estimate.uncertainty_rel, 1)
                        if estimate and estimate.ok else "",
        })
        if pr.mode == "measurement":
            status = f"{res.length_cm} cm"
        elif pr.mode == "estimate":
            status = f"ESTIMASI ~{estimate.length_cm} cm ({estimate.method})"
        else:
            status = f"DITOLAK ({res.qc_reasons})"
        print(f"[{path.parent.name}] {path.name}: {status} ({latency_ms} ms)")

    with open(OUT / "report.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n{len(rows)} foto -> {OUT / 'report.csv'} + overlay/")


if __name__ == "__main__":
    main()
