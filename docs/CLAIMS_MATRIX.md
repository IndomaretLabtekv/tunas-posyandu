# CLAIMS MATRIX — Klaim ↔ Implementasi ↔ Bukti ↔ Paper ↔ Demo

> **Fungsi:** mencegah paper, repo, dan video saling bertentangan. Fitur yang diklaim di paper tetapi tidak ada di produk dikenai penalti pada Implementation **dan** Demo; menampilkan mock-up merusak skor Demo Credibility.
>
> **Aturan pengisian:**
> - Kolom *Implemented* hanya boleh `Yes` bila ada orang lain di tim yang sudah menjalankannya dari commit bersih.
> - Kolom *Evidence* harus menunjuk ID eksperimen di `EXPERIMENTS.md` atau file bukti. `None` berarti klaim tidak boleh muncul di paper sebagai hasil.
> - Kolom *Paper* diisi nomor section. Bila `Future Work`, kalimat di paper wajib berbentuk prospektif.
> - Kolom *Demo* diisi timestamp di video. `—` berarti tidak ditampilkan.
>
> **Gate sebelum submit:** setiap baris dengan `Implemented = No` harus punya `Paper = Future Work` dan `Demo = —`. Tidak ada pengecualian.

---

## A. Kanal visual

| ID | Klaim | Implemented | Evidence | Paper | Demo |
|---|---|---|---|---|---|
| C-A0 | Galat akibat offset bidang terukur & dikendalikan lewat protokol | ☐ | CV-00 | §3.3, §4.1 | — |
| C-A1 | Deteksi 4 marker ArUco pada alas ukur | ☐ | CV-01 | §3.3 | |
| C-A2 | Rektifikasi perspektif bidang alas (homografi) | ☐ | CV-02 | §3.3 | |
| C-A3 | Quality control: blur, keterbacaan marker, kelengkapan tubuh | ☐ | CV-03 | §3.3 | |
| C-A4 | Geometry QC: penolakan citra dengan kemiringan kamera berlebih | ☐ | CV-04 | §3.3, §4.1 | |
| C-A5 | Ekstraksi endpoint tubuh berbasis segmentasi | ☐ | CV-05 | §3.3 | |
| C-A6a | QC postur berbasis geometri siluet | ☐ | CV-05 | §3.3 | |
| C-A6b | Pose pretrained sebagai QC tambahan | ☐ *bersyarat CV-06* | CV-06 | §3.3 **atau** Future Work | |
| C-A7 | Estimasi panjang badan, MAE pada objek proksi berukuran diketahui | ☐ | CV-07 | §4.1 | |
| C-A8 | Galat pada kondisi tangkap tidak ideal (sudut & jarak bervariasi) | ☐ | CV-08 | §4.1, §4.4 | |
| C-A9 | Konversi ke HAZ terverifikasi terhadap rujukan WHO | ☐ | CV-09 | §3.3 | |
| C-A14 | Selective prediction: coverage + MAE pada citra yang diterima | ☐ | CV-11 | §4.1, §4.3 | |
| C-A10 | MAE < 1 cm pada balita nyata | **No** | None | Future Work | — |
| C-A11 | Fine-tuning pose khusus anatomi balita | **No** | None | Future Work | — |
| C-A12 | Koreksi parallax penuh | **No** | None | Future Work | — |
| C-A13 | Protokol pengukuran berdiri | **No** | None | Future Work | — |

## B. Kanal tabular & model

| ID | Klaim | Implemented | Evidence | Paper | Demo |
|---|---|---|---|---|---|
| C-B1 | Kohort longitudinal sintetis dengan noise, missing, kunjungan tak teratur | ☐ | TAB-01 | §3.2, DATA_CARD | |
| C-B2 | Fitur lintasan: growth velocity, tren Z-score, gagal tumbuh berulang | ☐ | TAB-02 | §3.4 | |
| C-B3 | Target prospektif (deteriorasi horizon ke depan) | ☐ | TAB-03 | §3.5 | |
| C-B4 | Split grouped by `child_id` + temporal holdout | ☐ | TAB-03 | §3.5, §4.2 | |
| C-B5 | Baseline B0/B1/B2 pada target identik | ☐ | TAB-04 | §4.2 | |
| C-B6 | LightGBM mengungguli baseline pada target yang sama | ☐ | TAB-04 | §4.2 | |
| C-B7 | Ablasi: snapshot → +lintasan → +kontekstual | ☐ | TAB-05 | §4.2 | |
| C-B8 | Metrik prioritisasi Precision@K / Recall@K / AUPRC | ☐ | TAB-06 | §4.2 | |
| C-B9 | Confusion matrix & error analysis | ☐ | TAB-07 | §4.4 | |
| C-B10 | Uji ketahanan terhadap noise pengukuran & missing values | ☐ | TAB-08 | §4.3 | |
| C-B11 | SHAP per anak ditampilkan pada UI | ☐ | TAB-09 | §3.5, §4.5 | |
| C-B12 | Latency inferensi per prediksi | ☐ | TAB-10 | §4.3 | |
| C-B15 | Sensitivity analysis per irisan populasi sintetis | ☐ | TAB-11 | §4.3 | — |
| C-B13 | Validitas klinis model pada populasi nyata | **No** | None | Future Work | — |
| C-B14 | Ambang deteriorasi tervalidasi ahli gizi | **No** | None | Future Work | — |

## C. Produk & sistem

| ID | Klaim | Implemented | Evidence | Paper | Demo |
|---|---|---|---|---|---|
| C-C1 | Web app responsif dua mode | ☐ | SYS-02 + commit | §3.1 | |
| C-C2 | Alur kader end-to-end (foto → hasil → tersimpan) | ☐ | SYS-02 | §3.1 | |
| C-C3 | Fallback input manual saat kanal visual gagal | ☐ | SYS-02 | §3.1, §4.3 | |
| C-C4 | Dashboard prioritas dengan pengurutan | ☐ | SYS-02 | §3.1 | |
| C-C5 | Halaman detail: riwayat pertumbuhan + penjelasan | ☐ | SYS-02 | §3.1 | |
| C-C6 | Penanganan error & penandaan estimasi berkepercayaan rendah | ☐ | SYS-02 | §4.4 | |
| C-C7 | Reproduksi hasil dari repo bersih | ☐ | SYS-01 | §3.6 | — |
| C-C8 | Artefak di Hugging Face | ☐ | Link HF | §3.6 | — |
| C-C9 | Inferensi on-device | **No** | None | Future Work | — |
| C-C10 | Integrasi platform kesehatan nasional | **No** | None | Future Work | — |

## D. Dampak & validasi pengguna

| ID | Klaim | Implemented | Evidence | Paper | Demo |
|---|---|---|---|---|---|
| C-D1 | Validasi problem oleh kader/petugas gizi | ☐ | UV-01 | §4.5, Lampiran B | |
| C-D2 | Validasi kesesuaian workflow | ☐ | UV-02 | §4.5, Lampiran B | |
| C-D3 | Usability feedback atas antarmuka | ☐ | UV-03 | §4.5, Lampiran B | |
| C-D4 | Expert review atas kegunaan penjelasan model | ☐ | UV-04 | §4.5, Lampiran B | |
| C-D5 | Estimasi biaya penerapan | ☐ | `docs/ADOPTION.md` §3 | §4.6 | |
| C-D8 | Adoption pathway konkret (pilot → kecamatan → kabupaten) | ☐ | `docs/ADOPTION.md` + UV-01..04 | §4.6 | — |
| C-D6 | Pilot di Posyandu nyata | **No** | None | Future Work | — |
| C-D7 | Bukti dampak terhadap outcome gizi | **No** | None | Future Work | — |

---

## Checklist gate akhir (isi H-1 sebelum submit)

- [ ] Setiap baris `Implemented = No` → `Paper = Future Work` dan `Demo = —`
- [ ] Setiap angka di paper punya ID eksperimen yang bisa ditelusuri
- [ ] Setiap fitur yang muncul di video ada di baris dengan `Implemented = Yes`
- [ ] Tidak ada tangkapan layar mock-up di paper maupun video
- [ ] Section Limitations paper memuat seluruh baris `No`
