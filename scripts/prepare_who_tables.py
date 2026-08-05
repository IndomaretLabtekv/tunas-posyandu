"""Ubah berkas tabel WHO menjadi skema kanonik `data/who/lhfa_lms.csv`.

Nilai LMS TIDAK di-hardcode di repositori ini. Unduh sendiri dari
WHO Child Growth Standards (Length/height-for-age, boys & girls, tabel harian
atau bulanan dengan kolom L, M, S), lalu jalankan skrip ini.

    python -m scripts.prepare_who_tables \
        --boys  raw/lhfa_boys_0-to-2-years_zscores.txt \
        --girls raw/lhfa_girls_0-to-2-years_zscores.txt \
        --out   data/who/lhfa_lms.csv

Skrip menerima .txt/.tsv/.csv/.xlsx dan mendeteksi pemisah secara otomatis.
Membaca .xlsx membutuhkan `openpyxl` (sudah ada di requirements.txt).
Kolom usia boleh bernama Day/Days/Month/Months (case-insensitive); bila dalam
bulan, dikonversi ke hari memakai 30.4375 hari/bulan.

Setelah selesai, WAJIB jalankan:

    pytest tests/test_who_lms.py -q

dan isi `tests/who_reference_cases.csv` dengan beberapa kasus rujukan resmi
WHO. Verifikasi terhadap rujukan resmi adalah DEC-009 -- tanpa itu, seluruh
angka hilir bisa salah tanpa ketahuan.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

DAYS_PER_MONTH = 30.4375
CANONICAL = ["sex", "age_days", "L", "M", "S"]


def _read_any(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".xlsx":
        try:
            return pd.read_excel(path, engine="openpyxl")
        except ImportError as exc:  # pragma: no cover
            raise SystemExit("Butuh openpyxl: pip install openpyxl") from exc
    if path.suffix.lower() == ".xls":
        raise SystemExit(
            "Format .xls lama tidak didukung. Buka di Excel/LibreOffice lalu "
            "simpan ulang sebagai .xlsx atau .csv."
        )
    # sep=None + engine='python' -> deteksi pemisah otomatis (tab/koma/spasi)
    return pd.read_csv(path, sep=None, engine="python")


def _normalize(df: pd.DataFrame, sex: str) -> pd.DataFrame:
    cols = {c.strip().lower(): c for c in df.columns}

    for lms in ("l", "m", "s"):
        if lms not in cols:
            raise SystemExit(
                f"Kolom '{lms.upper()}' tidak ditemukan. Kolom tersedia: {list(df.columns)}. "
                "Pastikan mengunduh tabel yang memuat parameter LMS, bukan tabel persentil saja."
            )

    if "day" in cols or "days" in cols:
        age_col = cols.get("day") or cols.get("days")
        age_days = pd.to_numeric(df[age_col], errors="coerce")
    elif "month" in cols or "months" in cols:
        age_col = cols.get("month") or cols.get("months")
        age_days = pd.to_numeric(df[age_col], errors="coerce") * DAYS_PER_MONTH
    else:
        raise SystemExit(
            f"Kolom usia (Day/Month) tidak ditemukan. Kolom tersedia: {list(df.columns)}"
        )

    out = pd.DataFrame({
        "sex": sex,
        "age_days": age_days,
        "L": pd.to_numeric(df[cols["l"]], errors="coerce"),
        "M": pd.to_numeric(df[cols["m"]], errors="coerce"),
        "S": pd.to_numeric(df[cols["s"]], errors="coerce"),
    })
    return out.dropna().sort_values("age_days").reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--boys", required=True, type=Path)
    ap.add_argument("--girls", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=Path("data/who/lhfa_lms.csv"))
    ap.add_argument("--max-age-days", type=int, default=730,
                    help="Batas usia MVP (protokol recumbent, DEC-005).")
    args = ap.parse_args()

    frames = [
        _normalize(_read_any(args.boys), "M"),
        _normalize(_read_any(args.girls), "F"),
    ]
    df = pd.concat(frames, ignore_index=True)
    before = len(df)

    # Dicek SEBELUM filtering. Kalau drop_duplicates dijalankan lebih dulu,
    # pemeriksaan ini tidak akan pernah gagal dan baris dengan nilai M yang
    # bertentangan akan dipilih salah satu tanpa peringatan.
    dupes = df.duplicated(["sex", "age_days"], keep=False)
    if dupes.any():
        sample = df.loc[dupes, CANONICAL].head(10).to_dict("records")
        raise SystemExit(
            f"Duplikasi pasangan sex-age_days pada berkas sumber. Contoh: {sample}"
        )

    # Pertahankan SATU baris pertama di atas batas usia sebagai interpolation
    # anchor. Tanpa ini, tabel bulanan WHO (bulan 0-24) terpotong di bulan 23
    # = 700.06 hari, sehingga usia 701-730 hari tidak dapat diinterpolasi
    # padahal who_lms.MAX_AGE_DAYS = 730. Baris anchor TIDAK membuat usia
    # > 730 hari menjadi sah -- penolakannya tetap di who_lms._validate_age.
    within = df[df["age_days"] <= args.max_age_days]
    anchors = (
        df[df["age_days"] > args.max_age_days]
        .sort_values(["sex", "age_days"])
        .groupby("sex", as_index=False)
        .head(1)
    )
    df = (
        pd.concat([within, anchors], ignore_index=True)
        .sort_values(["sex", "age_days"])
        .reset_index(drop=True)
    )

    if df.empty:
        raise SystemExit("Hasil kosong setelah filter usia. Periksa berkas sumber.")
    if (df["M"] <= 0).any() or (df["S"] <= 0).any():
        raise SystemExit("Ditemukan M atau S <= 0. Berkas sumber kemungkinan salah kolom.")

    # Seluruh validasi dilakukan SEBELUM menulis. Script yang gagal tidak boleh
    # meninggalkan artefak setengah jadi -- file rusak yang tertinggal akan
    # terpakai diam-diam pada run berikutnya.
    present = set(df["sex"].unique())
    if present != {"M", "F"}:
        raise SystemExit(
            f"Jenis kelamin tidak lengkap: ditemukan {sorted(present)}, dibutuhkan ['F', 'M']."
        )
    coverage = df.groupby("sex")["age_days"].max()
    short = coverage[coverage < args.max_age_days]
    if not short.empty:
        raise SystemExit(
            f"Cakupan usia kurang: {short.to_dict()}. Tabel berakhir sebelum "
            f"{args.max_age_days} hari sehingga usia menjelang batas MVP tidak dapat "
            "diinterpolasi. Pastikan berkas sumber memuat sampai 24 bulan."
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    df[CANONICAL].to_csv(args.out, index=False)

    print(f"Tersimpan: {args.out}  ({len(df)} baris, dari {before} sebelum filter usia)")
    for sex, g in df.groupby("sex"):
        print(f"  {sex}: usia {g.age_days.min():.0f}-{g.age_days.max():.0f} hari, "
              f"M {g.M.min():.2f}-{g.M.max():.2f} cm")
    print("\nLangkah berikutnya: pytest tests/test_who_lms.py -q")


if __name__ == "__main__":
    main()
