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

- **B0** — ranking `−HAZ_t`; representasi praktik eksisting
- **B1** — ranking `w₁·(−HAZ_t) + w₂·(−slope_HAZ)`; bobot dari validation split
- **B2** — logistic regression
- **M1 / M2 / M3** — LightGBM snapshot / +lintasan / +kontekstual

Aturan biner `HAZ_t < −2` tetap dilaporkan sebagai pembanding pada metrik klasifikasi, tetapi tidak dipakai sebagai baseline ranking.

### Metrik
| Metrik | B0 | B1 | B2 | M1 | M2 | M3 |
|---|---|---|---|---|---|---|
| AUPRC | | | | | | |
| Recall (kelas risiko) | | | | | | |
| Precision | | | | | | |
| F1 | | | | | | |
| Recall@10% | | | | | | |
| Precision@10% | | | | | | |
| Recall@20% | | | | | | |
| Brier score | | | | | | |
| Latency (ms) | | | | | | |

Metrik @K adalah yang paling dekat dengan kondisi nyata: kapasitas tindak lanjut petugas terbatas, sehingga yang penting adalah berapa kasus tertangkap dalam K prioritas teratas.

### Failure mode yang diketahui
| Failure | Konteks | Penanganan |
|---|---|---|
| Anak dengan riwayat kunjungan sangat pendek | Balita baru terdaftar | Fitur lintasan kosong → model turun ke perilaku snapshot; UI menandai keterbatasan |
| Kunjungan tidak teratur | Absen berbulan-bulan | Fitur jarak kunjungan disertakan; kepercayaan diturunkan |
| Pergeseran distribusi | Populasi berbeda dari kohort pelatihan | Perlu kalibrasi ulang; disebut eksplisit sebagai syarat penerapan |
| Ketidakseimbangan kelas | Kasus deteriorasi jarang | Dilaporkan dengan AUPRC dan metrik @K, bukan accuracy |
| Kanal visual tidak tersedia | Fallback manual aktif | Model tetap berjalan pada fitur tabular; performa pada skenario ini dilaporkan terpisah |

### Explainability
SHAP menunjukkan **kontribusi fitur terhadap keluaran model**. SHAP bukan penjelasan sebab-akibat dan bukan penjelasan medis. Antarmuka menyajikannya sebagai "faktor yang paling memengaruhi skor", disertai keterangan tersebut.

### Batasan
Hasil diperoleh pada kohort sintetis. Model merekonstruksi pola yang ditanamkan simulasi; validitas klinis pada populasi nyata belum dibuktikan. Ambang kategori risiko bersifat operasional dan perlu dikalibrasi bersama ahli gizi.
