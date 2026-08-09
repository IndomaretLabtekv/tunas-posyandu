"""Runner eksperimen kanal visual (CV-00 sampai CV-04).

CV-00 adalah **gerbang arsitektur** (DEC-011): hasilnya menentukan apakah
protokol telentang di DEC-005 dapat dipertahankan. Jalankan sebelum pipeline
visual dibangun lebih jauh.

Alur kerja:

1.  Cetak marker:  `python -m cv.evaluate markers --out data/markers`
2.  Susun alas, ukur jarak antar sudut luar marker dengan meteran.
3.  Foto sesuai matriks di `configs/exp_cv_00.yaml`, catat tiap baris ke
    manifest CSV (template: `python -m cv.evaluate template --out manifest.csv`).
4.  Analisis: `python -m cv.evaluate run --manifest manifest.csv --out results/cv`

Manifest wajib memuat, per citra:

    image_path            lokasi berkas
    true_length_cm        panjang objek diukur meteran
    object_elevation_cm   elevasi TITIK YANG DIUKUR di atas alas (0 = menempel)
    camera_height_cm      jarak kamera ke bidang alas
    frame_position        center | edge
    lighting              indoor | outdoor
    p1_x,p1_y,p2_x,p2_y   koordinat piksel kedua ujung objek (opsional)

Kalau koordinat ujung tidak diisi, hanya deteksi marker dan geometry QC yang
dievaluasi -- itu sudah cukup untuk CV-01 sampai CV-04, tetapi belum untuk
mengukur MAE.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from cv.aruco import MatSpec, detect_markers, save_marker_sheet
from cv.geometry import (
    GeometryQC,
    camera_tilt_deg,
    expected_bias_cm,
    measure_length_cm,
    off_center_fraction,
)

MANIFEST_COLUMNS = [
    "image_path", "true_length_cm", "object_elevation_cm", "camera_height_cm",
    "frame_position", "lighting", "p1_x", "p1_y", "p2_x", "p2_y", "notes",
]


def manifest_template() -> pd.DataFrame:
    """Kerangka manifest dengan satu baris contoh (hapus sebelum dipakai)."""
    return pd.DataFrame([{
        "image_path": "data/cv00/IMG_0001.jpg",
        "true_length_cm": 60.0,
        "object_elevation_cm": 0.0,
        "camera_height_cm": 120.0,
        "frame_position": "center",
        "lighting": "indoor",
        "p1_x": "", "p1_y": "", "p2_x": "", "p2_y": "",
        "notes": "CONTOH -- hapus baris ini",
    }], columns=MANIFEST_COLUMNS)


def analyze_image(path: Path, spec: MatSpec, qc: GeometryQC, row: pd.Series) -> dict:
    """Analisis satu citra: deteksi, QC, dan (bila ada titik ujung) pengukuran."""
    out = {
        "image_path": str(path),
        "true_length_cm": row.get("true_length_cm", np.nan),
        "object_elevation_cm": row.get("object_elevation_cm", np.nan),
        "camera_height_cm": row.get("camera_height_cm", np.nan),
        "frame_position": row.get("frame_position", ""),
        "lighting": row.get("lighting", ""),
        "detected": False, "n_markers": 0, "qc_passed": False,
        "tilt_deg": np.nan, "reprojection_px": np.nan,
        "measured_length_cm": np.nan, "error_cm": np.nan, "abs_error_cm": np.nan,
        "expected_bias_cm": np.nan, "off_center": np.nan, "reason": "",
    }

    image = cv2.imread(str(path))
    if image is None:
        out["reason"] = "berkas tidak terbaca"
        return out

    det = detect_markers(image, spec)
    out["n_markers"] = len(det.found_ids)
    out["detected"] = det.ok
    if not det.ok:
        out["reason"] = det.reason
        return out

    check = qc.check(det, spec, row.get("camera_height_cm"))
    out.update({"qc_passed": check["passed"], "tilt_deg": check["tilt_deg"],
                "reprojection_px": check["reprojection_px"],
                "reason": "; ".join(check["reasons"])})

    coords = [row.get(c) for c in ("p1_x", "p1_y", "p2_x", "p2_y")]
    if all(pd.notna(c) and str(c) != "" for c in coords):
        p1 = (float(coords[0]), float(coords[1]))
        p2 = (float(coords[2]), float(coords[3]))
        measured = measure_length_cm(det, p1, p2)
        out["measured_length_cm"] = round(measured, 2)
        out["off_center"] = round(
            off_center_fraction(det, np.mean([p1, p2], axis=0), image.shape), 3
        )
        true_len = row.get("true_length_cm")
        if pd.notna(true_len):
            err = measured - float(true_len)
            out["error_cm"] = round(err, 2)
            out["abs_error_cm"] = round(abs(err), 2)
            h, z = row.get("camera_height_cm"), row.get("object_elevation_cm")
            if pd.notna(h) and pd.notna(z) and float(z) < float(h):
                out["expected_bias_cm"] = round(
                    expected_bias_cm(float(true_len), float(h), float(z)), 2
                )
    return out


def run_cv00(manifest: pd.DataFrame, spec: MatSpec, qc: GeometryQC) -> pd.DataFrame:
    missing = set(["image_path"]) - set(manifest.columns)
    if missing:
        raise ValueError(f"Manifest kehilangan kolom: {sorted(missing)}")
    rows = [analyze_image(Path(r["image_path"]), spec, qc, r) for _, r in manifest.iterrows()]
    return pd.DataFrame(rows)


def summarize(results: pd.DataFrame) -> pd.DataFrame:
    """Ringkasan yang menjadi isi Tabel 1 paper: coverage DAN galat bersama-sama.

    MAE tidak pernah dilaporkan sendirian. MAE rendah yang diperoleh setelah
    diam-diam membuang citra sulit bukan hasil yang sah -- yang jujur adalah
    melaporkan berapa persen citra diterima dan MAE pada citra yang diterima
    (CV-11, selective prediction).
    """
    n = len(results)
    if n == 0:
        raise ValueError("Tidak ada hasil untuk diringkas.")
    accepted = results[results["qc_passed"]]
    measured = accepted[accepted["abs_error_cm"].notna()]
    stats = {
        "n_images": n,
        "detection_rate": round(float(results["detected"].mean()), 4),
        "qc_pass_rate_coverage": round(float(results["qc_passed"].mean()), 4),
        "n_measured": len(measured),
    }
    if len(measured):
        stats.update({
            "mae_cm_on_accepted": round(float(measured["abs_error_cm"].mean()), 3),
            "median_abs_error_cm": round(float(measured["abs_error_cm"].median()), 3),
            "p90_abs_error_cm": round(float(measured["abs_error_cm"].quantile(0.9)), 3),
            "mean_signed_error_cm": round(float(measured["error_cm"].mean()), 3),
            "max_abs_error_cm": round(float(measured["abs_error_cm"].max()), 3),
        })
    return pd.DataFrame([stats]).T.rename(columns={0: "value"})


def by_condition(results: pd.DataFrame, columns=("object_elevation_cm", "camera_height_cm",
                                                 "frame_position", "lighting")) -> pd.DataFrame:
    """Galat per kondisi tangkap -- inti error analysis paper 4.1 / 4.4."""
    rows = []
    for col in columns:
        if col not in results.columns:
            continue
        for value, grp in results.groupby(col, dropna=True):
            meas = grp[grp["abs_error_cm"].notna()]
            rows.append({
                "condition": col,
                "value": value,
                "n": len(grp),
                "detection_rate": round(float(grp["detected"].mean()), 3),
                "qc_pass_rate": round(float(grp["qc_passed"].mean()), 3),
                "mae_cm": round(float(meas["abs_error_cm"].mean()), 3) if len(meas) else np.nan,
                "mean_signed_error_cm": round(float(meas["error_cm"].mean()), 3) if len(meas) else np.nan,
                "expected_bias_cm": round(float(meas["expected_bias_cm"].mean()), 3) if len(meas) else np.nan,
            })
    return pd.DataFrame(rows)


def gate_decision(summary: pd.DataFrame, tolerance_cm: float = 1.0) -> str:
    """Keputusan gerbang DEC-011, dirakit dari angka nyata.

    Empat opsi mitigasi sudah ditetapkan di muka, jadi hasil buruk tidak
    berarti scope dibahas ulang -- tinggal pilih dan catat.
    """
    s = summary["value"]
    if "mae_cm_on_accepted" not in s.index:
        return ("Belum ada pengukuran panjang (koordinat ujung objek kosong). "
                "CV-00 belum dapat memutuskan gerbang DEC-011.")
    mae = float(s["mae_cm_on_accepted"])
    cov = float(s["qc_pass_rate_coverage"])
    if mae <= tolerance_cm and cov >= 0.7:
        return (f"LULUS: MAE {mae:.2f} cm pada coverage {cov:.0%}. Protokol telentang "
                "(DEC-005) dapat dipertahankan tanpa mitigasi tambahan.")
    if mae <= tolerance_cm:
        return (f"LULUS BERSYARAT: MAE {mae:.2f} cm, tetapi coverage hanya {cov:.0%}. "
                "Ambang QC terlalu ketat atau protokol pengambilan sulit dipenuhi. "
                "Pertimbangkan mitigasi DEC-011 opsi 1 (tinggi kamera minimum).")
    return (f"TIDAK LULUS: MAE {mae:.2f} cm melebihi toleransi {tolerance_cm} cm "
            f"(coverage {cov:.0%}). Pilih satu mitigasi DEC-011 dan catat di DECISIONS.md: "
            "(1) tinggi kamera minimum, (2) reference bar pada elevasi tubuh, "
            "(3) koreksi empiris dengan batasan tertulis, "
            "(4) hasil visual sebagai estimasi awal yang wajib dikonfirmasi manual.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("markers", help="cetak berkas marker ArUco")
    m.add_argument("--out", type=Path, default=Path("data/markers"))
    m.add_argument("--size-px", type=int, default=400)

    t = sub.add_parser("template", help="buat template manifest CSV")
    t.add_argument("--out", type=Path, default=Path("data/cv00/manifest.csv"))

    r = sub.add_parser("run", help="jalankan analisis CV-00")
    r.add_argument("--manifest", type=Path, required=True)
    r.add_argument("--out", type=Path, default=Path("results/cv"))
    r.add_argument("--mat-width-cm", type=float, required=True)
    r.add_argument("--mat-height-cm", type=float, required=True)
    r.add_argument("--max-tilt-deg", type=float, default=GeometryQC.max_tilt_deg)
    r.add_argument("--tolerance-cm", type=float, default=1.0)

    args = ap.parse_args()

    if args.cmd == "markers":
        spec = MatSpec(width_cm=60.0, height_cm=100.0)
        paths = save_marker_sheet(spec, args.out, args.size_px)
        print("Marker tersimpan:")
        for p in paths:
            print(" ", p)
        print("\nCetak keempatnya pada ukuran fisik yang SAMA, tempel di sudut alas,")
        print("lalu UKUR jarak antar sudut luarnya dengan meteran. Angka hasil ukur")
        print("itulah yang dipakai sebagai --mat-width-cm dan --mat-height-cm.")
        return

    if args.cmd == "template":
        args.out.parent.mkdir(parents=True, exist_ok=True)
        manifest_template().to_csv(args.out, index=False)
        print(f"Template tersimpan: {args.out}")
        print("Isi satu baris per citra, lalu jalankan `python -m cv.evaluate run`.")
        return

    spec = MatSpec(width_cm=args.mat_width_cm, height_cm=args.mat_height_cm)
    qc = GeometryQC(max_tilt_deg=args.max_tilt_deg)
    manifest = pd.read_csv(args.manifest)

    results = run_cv00(manifest, spec, qc)
    summary = summarize(results)
    conditions = by_condition(results)

    args.out.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.out / "cv00_per_image.csv", index=False)
    summary.to_csv(args.out / "cv00_summary.csv")
    conditions.to_csv(args.out / "cv00_by_condition.csv", index=False)

    print("\n=== CV-00 ringkasan ===")
    print(summary.to_string())
    print("\n=== per kondisi ===")
    print(conditions.to_string(index=False))
    print("\n=== keputusan gerbang DEC-011 ===")
    print(gate_decision(summary, args.tolerance_cm))
    print(f"\nArtefak: {args.out}")
    print("Catat angka ke EXPERIMENTS.md dari file CSV, bukan dari layar ini.")


if __name__ == "__main__":
    main()
