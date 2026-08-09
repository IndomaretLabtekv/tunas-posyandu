# MODEL CARD

Dua komponen model dalam Tunas didokumentasikan terpisah karena sifat, evaluasi, dan failure mode-nya berbeda.

---

## Bagian 1 — Pipeline estimasi antropometri (kanal visual)

### Ringkasan
Pipeline geometri, bukan model tunggal: deteksi marker ArUco → rektifikasi bidang alas → quality control → segmentasi subjek → ekstraksi endpoint sepanjang sumbu tubuh → konversi ke sentimeter → konversi ke HAZ (LMS WHO). QC postur berbasis geometri siluet merupakan jalur utama; model pose pretrained bersifat **auxiliary dan bersyarat** — hanya masuk produk bila lolos CV-06 (DEC-006). Pose tidak pernah menjadi sumber angka ukur.

### Penggunaan yang dimaksudkan
Membantu kader Posyandu memperoleh estimasi panjang badan telentang pada kondisi tangkap yang terkendali, sebagai pendamping (bukan pengganti) pengukuran manual.

### Penggunaan di luar cakupan
- Pengukuran tinggi badan berdiri
- Pengukuran tanpa alas ber-marker
- Pengukuran dari citra yang gagal quality control
- Diagnosis status gizi tanpa penilaian tenaga kesehatan

### Data evaluasi

| Dataset | Membuktikan |
|---|---|
| `proxy_objects_v1` | Akurasi geometri & konversi ukuran (termasuk CV-00 plane-offset) |
| `proxy_subjects_v1` | Segmentasi bentuk tubuh, endpoint kepala/kaki, QC postur, failure case |

**Bukan** balita nyata dalam kondisi Posyandu.

### Metrik
| Metrik | Kondisi ideal | Kondisi tidak ideal |
|---|---|---|
| MAE (cm) | — | — |
| MAPE (%) | — | — |
| Galat endpoint kepala (cm) | — | — |
| Galat endpoint kaki (cm) | — | — |
| Detection rate marker (%) | — | — |
| Reject rate QC (%) | — | — |
| Latency (ms, CPU) | — | — |
| **Coverage** (% citra yang diterima QC) | — | — |
| MAE **pada citra yang diterima** | — | — |

Angka MAE tidak pernah dilaporkan sendirian: sistem menerapkan *selective prediction*, sehingga MAE hanya bermakna bila disertai coverage (CV-11). MAE rendah yang diperoleh setelah membuang citra sulit tanpa melaporkan berapa yang dibuang bukan hasil yang sah.

### Failure mode yang diketahui
| Failure | Penyebab | Penanganan sistem |
|---|---|---|
| Marker tidak terbaca | Pencahayaan buruk, marker terlipat/kotor, marker terpotong | Citra ditolak, kader diminta ulang |
| Kamera terlalu miring | Pengambilan tergesa | Geometry QC menolak; UI memberi panduan |
| Galat sisa akibat offset bidang tubuh | Tubuh tidak tepat pada bidang marker | Tidak dikoreksi penuh; dibatasi lewat protokol jarak & sudut; galat sisa dilaporkan |
| Subjek tidak lurus / tungkai tertekuk | Balita bergerak | QC siluet (kelengkungan sumbu, deviasi) menandai; pose QC menambah sinyal bila lolos CV-06; skor kepercayaan turun |
| Titik ukur berada di atas bidang marker | Geometri (parallax) | Tidak dikoreksi penuh; dibatasi lewat protokol tinggi kamera & posisi bingkai hasil CV-00 (DEC-011) |
| Oklusi (selimut, pakaian tebal, tangan pengasuh) | Kondisi lapangan | Segmentasi tidak stabil → estimasi ditandai berkepercayaan rendah |
| Alas berwarna tidak seragam | Alas tidak standar | Segmentasi memburuk; QC menolak |

### Batasan
Seluruh angka MAE berasal dari objek dan subjek proksi. Akurasi pada balita nyata dalam kondisi Posyandu **belum diukur** dan tidak diklaim.

---

## Bagian 2 — Model prioritisasi risiko (kanal tabular)

### Ringkasan
LightGBM yang memprediksi kemungkinan **deteriorasi pertumbuhan pada horizon ke depan**, dari fitur snapshot, lintasan, dan kontekstual pada kunjungan ≤ `t`. Keluaran: probabilitas kontinu untuk pengurutan prioritas + kategori risiko + atribusi SHAP.

### Penggunaan yang dimaksudkan
Membantu petugas gizi puskesmas **mengurutkan** tindak lanjut ketika kapasitas intervensi lebih kecil daripada jumlah anak yang dipantau.

### Penggunaan di luar cakupan
- Menetapkan status gizi (itu ditentukan standar WHO atas hasil ukur, bukan oleh model)
- Menolak atau menghentikan intervensi bagi anak berskor rendah
- Menggantikan penilaian klinis
- Dipakai pada populasi yang karakteristiknya jauh berbeda dari kohort pelatihan tanpa kalibrasi ulang

### Data pelatihan & evaluasi
`posyandu_synth_v1`. Split grouped by `child_id` + temporal holdout. Detail di `DATA_CARD.md` dan `DECISIONS.md` DEC-003.

### Pembanding
Seluruhnya pada target dan split identik, dan seluruhnya menghasilkan **skor kontinu** agar dapat diurutkan dan dibandingkan pada metrik @K (DEC-012):

- **B0** — ranking `−HAZ_t`; snapshot-only proxy baseline, bukan bukti praktik Posyandu yang terobservasi
- **B1** — ranking `w₁·(−HAZ_t) + w₂·(−slope_HAZ)`; bobot dari validation split
- **B2** — logistic regression
- **M1 / M2 / M3** — LightGBM snapshot / +lintasan / +kontekstual

Aturan biner `HAZ_t < −2` tetap dilaporkan sebagai pembanding pada metrik klasifikasi, tetapi tidak dipakai sebagai baseline ranking.

### Metrik

Grouped child holdout, mean ± sample SD atas lima seed. Hasil temporal dan
angka mentah per seed ada di [`FINAL_TABULAR_RESULTS.md`](FINAL_TABULAR_RESULTS.md)
dan `results/tabular/final/`.

| Metrik | B0 | B1 | B2 | M1 | M2 | M3 |
|---|---|---|---|---|---|---|
| AUPRC | .1626±.0464 | .1797±.0436 | .1622±.0403 | .2291±.0546 | **.2735±.0947** | .2268±.0556 |
| Recall (Top-20%) | .2096±.1002 | .2989±.0967 | .2741±.0364 | .4124±.0655 | **.4821±.0994** | .4590±.0820 |
| Precision (Top-20%) | .1042±.0466 | .1500±.0401 | .1417±.0309 | .2125±.0475 | **.2500±.0691** | .2375±.0600 |
| F1 (Top-20%) | .1384±.0625 | .1986±.0545 | .1859±.0339 | .2790±.0530 | **.3277±.0818** | .3115±.0694 |
| Recall@10% | .1143±.0496 | .1363±.0391 | .1623±.0335 | .2392±.0728 | .2587±.1034 | **.2667±.0223** |
| Precision@10% | .1167±.0543 | .1417±.0475 | .1667±.0417 | .2417±.0618 | **.2750±.1337** | **.2750±.0475** |
| Recall@20% | .2096±.1002 | .2989±.0967 | .2741±.0364 | .4124±.0655 | **.4821±.0994** | .4590±.0820 |
| Raw Brier | — | — | .2041±.0127 | .0948±.0109 | .0942±.0099 | **.0939±.0107** |
| Latency single-row, median / p95 (ms) | — | — | — | — | 1.143 / 1.562 | — |

Metrik @K adalah yang paling dekat dengan kondisi nyata: kapasitas tindak lanjut petugas terbatas, sehingga yang penting adalah berapa kasus tertangkap dalam K prioritas teratas.

### Robustness, tie sensitivity, dan efficiency

- Noise panjang tambahan 2 cm menurunkan AUPRC M2 dari 0,2735 menjadi 0,1536 pada grouped dan dari 0,2976 menjadi 0,1860 pada temporal (mean lima seed).
- Ketika panjang/HAZ kunjungan terkini tidak tersedia, AUPRC menjadi 0,1465 grouped dan 0,2017 temporal. Coverage skor tetap 100% karena model dapat menangani nilai kosong; kualitas ranking tetap turun.
- Missing panjang tambahan 30% menghasilkan AUPRC 0,2447 grouped dan 0,2477 temporal.
- Model tersimpan berukuran 14.150 byte. Pada environment WSL2/Intel Core Ultra 7 155H, score + exact Top-20% untuk 240 anak memiliki median 0,959 ms dan p95 1,484 ms. Angka ini tidak digeneralisasi ke perangkat lain.
- Cutoff-score ties membuat Recall@K sensitif terhadap membership. Worst observed range adalah 0,0000–0,1538 pada grouped seed 42, K=5%; aturan produksi exact-K + `child_id` tetap tidak berubah.
- Schema frozen memuat `measured_by_cv_t`. TAB-08 tidak menyamakan ukuran manual valid dengan ukuran hilang dan tidak membuktikan invariansi skor terhadap flag sumber pengukuran.

Detail lengkap: `docs/FINAL_TABULAR_RESULTS.md` serta artefak TAB-08, TAB-10, dan TAB-12 di `results/tabular/final/`.

### Failure mode yang diketahui
| Failure | Konteks | Penanganan |
|---|---|---|
| Anak dengan riwayat kunjungan sangat pendek | Balita baru terdaftar | Fitur lintasan kosong → model turun ke perilaku snapshot; UI menandai keterbatasan |
| Kunjungan tidak teratur | Absen berbulan-bulan | Fitur jarak kunjungan disertakan; kepercayaan diturunkan |
| Pergeseran distribusi | Populasi berbeda dari kohort pelatihan | Perlu kalibrasi ulang; disebut eksplisit sebagai syarat penerapan |
| Ketidakseimbangan kelas | Kasus deteriorasi jarang | Dilaporkan dengan AUPRC dan metrik @K, bukan accuracy |
| Pengukuran panjang/HAZ terkini tidak tersedia | Foto gagal dan belum ada ukuran manual valid | Model tetap dapat memberi skor dari riwayat, tetapi ranking memburuk pada TAB-08; minta pengukuran manual valid bila tersedia |
| Banyak skor sama di batas kapasitas | Daun LightGBM menghasilkan probabilitas identik | Exact-K dan `child_id` menjaga reproduksibilitas; tampilkan sensitivitas membership dari TAB-12 saat menginterpretasi Recall@K |

### Explainability
SHAP menunjukkan **kontribusi fitur terhadap keluaran model**. SHAP bukan penjelasan sebab-akibat dan bukan penjelasan medis. Antarmuka menyajikannya sebagai "faktor yang paling memengaruhi skor", disertai keterangan tersebut.

### Batasan
Hasil diperoleh pada kohort sintetis. Model merekonstruksi pola yang ditanamkan simulasi; validitas klinis dan robustness pada populasi nyata belum dibuktikan. Ambang kategori risiko bersifat operasional dan perlu dikalibrasi bersama ahli gizi. Latency hanya berlaku pada hardware yang direkam, dan metric @K dapat sensitif terhadap tie pada skor cutoff.
