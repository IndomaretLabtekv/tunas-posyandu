# Log Hasil Eksperimen (Provisional — Semua dari Data Sintetis Simulasi)

> **PERINGATAN KERAS:** Semua angka di file ini dihasilkan dari **tabel LMS simulasi buatan sendiri** (bukan tabel WHO resmi), untuk keperluan verifikasi kode saja. **JANGAN disalin ke paper, `EXPERIMENTS.md`, atau video dalam bentuk apa pun.** Angka final harus dihasilkan ulang setelah `A1-A5` di `TODO_MASTER.md` selesai (tabel WHO resmi + kohort 5000 anak + `0 skipped`).
>
> File ini ada supaya sesi lanjutan tahu **arah dan besaran kasar** hasil, serta paham kesalahan unit evaluasi yang pernah terjadi — bukan sebagai sumber angka final.

## Eksperimen 1 — kohort 1.200 anak, evaluasi PER KUNJUNGAN (SALAH, sebelum bug unit ditemukan)

```
model               auprc  recall@20%  precision@20%  lift@20%     f1   brier
B0_haz_only        0.1572      0.1650         0.1319     0.825  0.1466    NaN
B1_haz_slope       0.1464      0.1699         0.1358     0.850  0.1509    NaN
B2_logreg          0.2068      0.2680         0.2141     1.340  0.2380  0.2462
RULE_haz_lt_-2     0.1535      0.1520         0.1214     0.760  0.2756  0.3084
M1_snapshot        0.2317      0.3121         0.2493     1.560  0.2883  0.1338
M2_plus_trajectory 0.3335      0.4314         0.3446     2.157  0.3823  0.1299
M3_plus_contextual 0.3222      0.4036         0.3225     2.018  0.3585  0.1302
```

**Kesimpulan yang ditarik saat itu (SALAH/tidak lengkap):** "M3 lebih buruk dari M2, blok kontekstual tidak membantu." Kesimpulan ini berasal dari evaluasi yang tidak membatasi satu baris per anak — satu anak dengan banyak kunjungan bisa dominan dalam top-20%. Setelah bug unit-evaluasi diperbaiki (lihat Eksperimen 3), kesimpulan ini terbalik.

**Nilai yang tetap valid dari eksperimen ini:** B0 lift < 1 (praktik prioritas berdasarkan HAZ terkini saja LEBIH BURUK dari acak untuk memprediksi deteriorasi masa depan) — pola ini konsisten muncul di eksperimen berikutnya juga, jadi kemungkinan besar riil secara struktural (anak dengan HAZ rendah cenderung stabil rendah, bukan terus memburuk; sedangkan anak yang memburuk sering masih di rentang "normal" pada waktu prediksi).

## Eksperimen 2 — kohort 3.000 anak, evaluasi per KUNJUNGAN (sebelum unit fix, run kedua)

```
grouped  (val 9.759 kunjungan, test 9.767 kunjungan)
  B0=0.227  B1=0.293  B2=0.267  M1=0.387  M2=0.587  M3=0.547   (recall@20%)

temporal (val 6.382, test 9.787)
  B0=0.256  B1=0.408  B2=0.298  M1=0.391  M2=0.543  M3=0.490
```

Urutan sudah lebih stabil dibanding Eksperimen 1 (n lebih besar → varians lebih kecil), tapi **tetap dari evaluasi per-kunjungan**, jadi angka absolutnya tidak dipakai untuk kesimpulan final.

## Eksperimen 3 — kohort 3.000 anak, evaluasi PER ANAK (SETELAH bug unit diperbaiki — metodologi benar)

```
grouped  (test: 3.830 kunjungan -> 240 anak setelah select_index_visits)
  B0=0.226  M1=0.194  M2=0.355  M3=0.452   (recall@20%)

temporal (test: 3.863 kunjungan -> 1.063 anak)
  B0=0.219  M1=0.303  M2=0.407  M3=0.432
```

**Perubahan penting dari Eksperimen 1/2:** Pada evaluasi per-anak yang benar, M1 kadang JATUH DI BAWAH B0 (grouped: M1=0.194 < B0=0.226) — kebalikan dari kesan sebelumnya bahwa "semua model M mengalahkan baseline". Ini kemungkinan sinyal bahwa **n=240 pada grouped test terlalu kecil** (dengan prevalensi ~16%, itu cuma ~38 kasus positif) sehingga metrik sangat berayun antar seed — BUKAN berarti M1 benar-benar buruk.

## Eksperimen 4 — kohort 2.000 anak, dengan primary_model + SHAP (setelah semua fix metodologi)

Contoh penjelasan SHAP satu anak (untuk verifikasi format, bukan hasil final):

```
child_id  priority_rank  priority_score  rank  label                             shap    arah
C01287                1        0.289598     1  Status panjang badan saat ini    0.1599  menaikkan
C01287                1        0.289598     2  Perubahan sejak kunjungan lalu   0.1149  menaikkan
C01287                1        0.289598     3  Kecepatan perubahan pertumbuhan  0.0544  menaikkan
C01287                1        0.289598     4  Lama sejak pertumbuhan terbaik   0.0442  menaikkan
C01287                1        0.289598     5  Titik terendah pertumbuhan       0.0257  menaikkan
```

Global importance (dari fixture test, BUKAN kohort produksi): fitur yang benar-benar dominan dalam pembangkitan label berhasil terdeteksi SHAP sebagai fitur teratas — ini bukti bahwa mekanisme SHAP bekerja benar, bukan hasil yang dilaporkan ke paper.

## Kesimpulan metodologis yang BOLEH dipakai sebagai arahan (bukan angka pasti)

1. **B0 (prioritas berdasarkan HAZ terkini saja) secara struktural lemah** untuk memprediksi deteriorasi masa depan — pola ini konsisten di semua run. Ini alasan kuat untuk narasi "before → after" di paper: praktik saat ini (proxy: B0) memang tidak menangkap anak yang akan memburuk.
2. **M2 (snapshot + trajectory) secara konsisten mengungguli M1 (snapshot saja)** di hampir semua kondisi run yang benar secara metodologi — ini pendukung utama klaim nilai tambah fitur lintasan pertumbuhan.
3. **M3 (+ kontekstual) hasilnya TIDAK STABIL** — kadang di atas M2, kadang di bawah, tergantung ukuran kohort dan unit evaluasi. **Jangan berasumsi arahnya sebelum menjalankan ulang dengan data final.** Kalau tetap tidak stabil di data final, ini temuan yang JUJUR untuk dilaporkan (bukan disembunyikan) — sekaligus alasan tambahan mempertimbangkan tidak memakai `ses_index` sebagai prediktor (isu fairness di `RESPONSIBLE_AI.md`).
4. **n kohort final harus cukup besar.** Rekomendasi TODO: 5.000 anak, bukan 1.200–3.000 yang dipakai untuk uji coba kode. Dengan prevalensi ~16% dan test set per-anak yang mengecil signifikan setelah `select_index_visits`, n kecil menghasilkan metrik yang sangat berisik.
5. **Galat parallax kanal visual (teoretis, dari `cv/geometry.py`) kemungkinan besar signifikan** — model pinhole sederhana menunjukkan galat 3-8 cm pada kondisi kamera realistis (tinggi 100-150cm, elevasi titik ukur 5-10cm). Kemungkinan besar CV-00 empiris akan gagal toleransi 1cm murni tanpa mitigasi tambahan (lihat DEC-011).

## Cara menghasilkan ulang angka final (checklist)

```bash
# 1. Tabel WHO
python -m scripts.prepare_who_tables --boys <file_who_boys> --girls <file_who_girls>

# 2. Isi tests/who_reference_cases.csv (minimal 8 kasus dari WHO Anthro/tabel resmi)

# 3. Verifikasi
python -m pytest tests/ -q   # target: SEMUA passed, 0 skipped

# 4. Generate kohort final
python -m data.generate_synth --n-children 5000 --seed 42

# 5. Jalankan eksperimen kedua skema
python -m tabular.train --split grouped  --out results/grouped
python -m tabular.train --split temporal --out results/temporal

# (Opsional tapi direkomendasikan) multi-seed untuk stabilitas
for s in 42 43 44 45 46; do
  python -m tabular.train --split grouped  --seed $s --out results/grouped_seed_$s
  python -m tabular.train --split temporal --seed $s --out results/temporal_seed_$s
done

# 6. Catat SEMUA angka ke 02_docs/EXPERIMENTS.md dari file CSV di results/,
#    BUKAN dari dokumen ini atau dari chat manapun.
```
