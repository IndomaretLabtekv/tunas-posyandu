"""Runner eksperimen kanal visual pada foto asli (experiments/src -> results).

Cara pakai (env datsci):
    python scripts/run_cv_experiments.py

Membaca semua gambar di experiments/src/**, menjalankan pipeline kanal
visual untuk tiap foto, lalu menulis:
- experiments/results/overlay/<nama>.png  (overlay deteksi/hasil/penolakan)
- experiments/results/report.csv          (tabel hasil lengkap)

Kolom report:
- group       : subfolder sumber (mats / babies / ...)
- image       : nama berkas
- det_nocolor : deteksi alas tanpa signature warna (keseragaman saja)
- det_color   : deteksi alas dengan signature warna standar produk
- reason      : alasan penolakan (bila gagal)
- length_cm   : hasil ukur (bila lolos)
- confidence  : confidence pipeline
- model       : segmenter yang dipakai
- latency_ms  : waktu pipeline
"""

import csv
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root

from cv.aruco import MatSpec, draw_overlay, rectify
from cv.mat_corners import PRODUCT_MAT_COLOR, PRODUCT_MAT_SPEC, detect_mat_corners
from cv.pipeline import measure_length
from cv.quality import ImageQC
from cv.segment import ColorSegmenter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "experiments" / "src"
OUT = ROOT / "experiments" / "results"
EXT = {".jpg", ".jpeg", ".png"}


def _draw_result(out: cv2.Mat, r) -> None:
    if r.ok:
        (x1, y1), (x2, y2) = r.endpoints_px
        cv2.circle(out, (x1, y1), 6, (0, 0, 255), -1)
        cv2.circle(out, (x2, y2), 6, (0, 0, 255), -1)
        cv2.line(out, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.putText(out, f"length={r.length_cm} cm | {r.model} | conf={r.confidence}",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
    else:
        msg = f"DITOLAK: {r.qc_reasons[0] if r.qc_reasons else '?'}"
        cv2.putText(out, msg, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)


def main() -> None:
    images = sorted(p for p in SRC.rglob("*") if p.suffix.lower() in EXT)
    if not images:
        raise SystemExit(f"tidak ada gambar di {SRC}")
    overlay_dir = OUT / "overlay"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    # Overlay ditulis per-grup sumber; grup 'babies' di-gitignore (privasi).

    rows = []
    for path in images:
        img = cv2.imread(str(path))
        if img is None:
            print(f"[skip] tidak terbaca: {path}")
            continue

        det_plain = detect_mat_corners(img, PRODUCT_MAT_SPEC)
        det_prod = detect_mat_corners(img, PRODUCT_MAT_SPEC, mat_color=PRODUCT_MAT_COLOR)

        t0 = time.perf_counter()
        res = measure_length(
            img, PRODUCT_MAT_SPEC,
            segmenter=ColorSegmenter(mat_color=PRODUCT_MAT_COLOR),
            image_qc=ImageQC(),
        )
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)

        overlay = draw_overlay(img, det_prod if det_prod.ok else det_plain)
        if res.ok:
            rect = rectify(img, det_prod, PRODUCT_MAT_SPEC, px_per_cm=10.0)
            mask = (ColorSegmenter(mat_color=PRODUCT_MAT_COLOR)
                    .segment(rect).mask.astype("uint8")) * 255
            scale = np.array([[10, 0, 0], [0, 10, 0], [0, 0, 1]], dtype=np.float64)
            mask_orig = cv2.warpPerspective(mask, np.linalg.inv(scale @ det_prod.homography),
                                            (img.shape[1], img.shape[0]))
            ov = overlay.copy()
            ov[mask_orig > 0] = (0, 200, 255)
            overlay = cv2.addWeighted(ov, 0.45, overlay, 0.55, 0)
        _draw_result(overlay, res)
        group_dir = overlay_dir / path.parent.name
        group_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(group_dir / f"{path.stem}.png"), overlay)

        rows.append({
            "group": path.parent.name,
            "image": path.name,
            "det_nocolor": det_plain.ok,
            "det_color": det_prod.ok,
            "reason": "; ".join(res.qc_reasons) if not res.ok else "",
            "length_cm": res.length_cm if res.ok else "",
            "confidence": res.confidence if res.ok else "",
            "model": res.model,
            "latency_ms": latency_ms,
        })
        status = f"{res.length_cm} cm" if res.ok else f"DITOLAK ({res.qc_reasons})"
        print(f"[{path.parent.name}] {path.name}: {status} ({latency_ms} ms)")

    with open(OUT / "report.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n{len(rows)} foto -> {OUT / 'report.csv'} + overlay/")


if __name__ == "__main__":
    main()
