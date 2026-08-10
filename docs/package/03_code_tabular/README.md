# Kanal Tabular — Cara Pakai

Status: **kode selesai, 8 modul, semua lulus test.** Belum dijalankan dengan tabel WHO resmi (4 test masih skip). Lihat `08_process_and_review_log/REVIEW_METHODOLOGY_AND_BUG_LOG.md` untuk riwayat bug yang sudah diperbaiki di tiap modul — jangan tulis ulang dari nol kalau menemukan hal yang "terlihat aneh", cek dulu apakah itu keputusan desain yang sudah melalui review.

## Urutan dependency antar modul

```
who_lms.py          <- konversi HAZ, butuh tabel LMS eksternal (tidak disertakan)
    |
target.py           <- definisi label prospektif, butuh kolom haz
    |
splits.py           <- grouped + temporal split, butuh label_available_date dari target.py
    |
features.py         <- 3 blok fitur, butuh haz + splits untuk verifikasi bebas leakage
    |
baselines.py        <- B0/B1/B2/RULE, butuh features
    |
evaluate.py          <- metrik ranking/klasifikasi/kapasitas, dipakai baselines & train
    |
train.py             <- orkestrasi semua di atas -> hasil ke results/tabular/
    |
explain.py            <- SHAP, dipanggil dari train.py (opsional, butuh package `shap`)
```

`generate_synth.py` (di `06_data_and_scripts/`) independen — dipanggil terpisah untuk membuat data uji/kohort, butuh `who_lms.py` untuk konversi HAZ.

## Cara pakai dari nol

```bash
# 1. Install
pip install -r ../10_repo_scaffold/requirements.txt

# 2. Siapkan tabel WHO (unduh sendiri length/height-for-age, L/M/S, boys & girls)
python -m scripts.prepare_who_tables --boys <file_boys> --girls <file_girls>

# 3. Isi tests/who_reference_cases.csv (copy dari template, minimal 8 kasus)

# 4. Verifikasi — HARUS 0 skipped sebelum lanjut
python -m pytest tests/ -q

# 5. Generate kohort
python -m data.generate_synth --n-children 5000 --seed 42

# 6. Jalankan eksperimen
python -m tabular.train --split grouped  --out results/grouped
python -m tabular.train --split temporal --out results/temporal
```

## Artefak yang dihasilkan `train.py` di `results/<nama>/`

| File | Isi |
|---|---|
| `tab04_ranking_comparison.csv` | Tabel utama: semua model ranking × semua metrik |
| `tab04_rule_comparison.csv` | Aturan biner (RULE), metrik klasifikasi saja |
| `tab04_label_drop_report.csv` | Berapa baris dibuang saat pelabelan & kenapa |
| `tab04_manifest.json` | Seed, commit, ukuran split, daftar child_id per split, bobot B1, dll — untuk reproduksibilitas penuh |
| `tab05_ablation.csv` | Subset tabel utama: B0/M1/M2/M3 saja |
| `tab07_error_analysis.csv` | Karakteristik fitur pada TP/FN/FP/TN |
| `tab09_shap_global.csv` | Ranking fitur agregat (kalau `shap` terpasang) |
| `tab09_shap_top_children.csv` | Penjelasan 5 faktor teratas untuk 10 anak prioritas tertinggi, siap dipakai frontend |
| `tab11_slice_report.csv` | Metrik per irisan populasi (jenis kelamin, usia, dst), termasuk `selection_rate` |
| `primary_model.joblib` | Model utama (M2) tersimpan, siap dimuat API via `joblib.load()` |

## Konsep kunci yang HARUS dipahami sebelum mengubah kode ini

1. **Model utama (`primary_model`) adalah M2, ditetapkan DI MUKA di `ExperimentConfig`, bukan dipilih dari hasil test.** Jangan ganti logikanya jadi "pilih yang AUPRC tertinggi" — itu kebocoran.
2. **Evaluasi per ANAK, bukan per kunjungan.** Fungsi `select_index_visits()` mengambil satu baris per anak sebelum dievaluasi. Training tetap pakai semua kunjungan.
3. **`score_type` wajib diisi** di setiap panggilan `evaluate_all()` — `"probability"` / `"ranking"` / `"binary_rule"`. Tidak ada default.
4. **Semua metrik @K (Recall, Precision, Lift, F1) menggunakan `capacity_predictions()` yang sama** — jangan buat jalur perhitungan top-K terpisah untuk metrik baru, itu sumber bug paling sering ditemukan review.
5. **B0 dan B1 tidak boleh menghitung statistik (mean/std/median) dari data yang sedang diberi skor** — harus dari train yang dikunci. Lihat `B1Model` dataclass sebagai pola yang benar.

## Kalau menambah modul baru (mis. fitur baru, model baru)

- Fitur baru wajib tercatat sebagai kolom `prediction_date` + `max_source_date`, dan diuji dengan `assert_features_not_future()`.
- Baseline/model baru wajib skor kontinu (bisa ranking), dievaluasi dengan `score_type` yang benar, dan HARUS diuji tidak bocor lintas batch (lihat pola test di `05_tests/test_train.py::test_skor_b1_tidak_berubah_karena_anggota_batch_lain`).
