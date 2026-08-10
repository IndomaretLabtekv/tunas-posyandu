# SCOPE — Lingkup MVP Semifinal

> **Dikunci pada:** ____ Agustus 2026, __:__ WIB · **Disetujui oleh:** ☐ Riantama ☐ Athilla ☐ Nicholas
>
> *(Isi tanggal aktual saat scope benar-benar disepakati bertiga — bukan tanggal dokumen ini dibuat.)*
>
> **Aturan main:** apa pun yang tidak ada di tabel "MASUK MVP" **dilarang** muncul di paper atau video sebagai fitur produk. Boleh disebut di section *Future Work* dengan bahasa yang jelas-jelas prospektif.
>
> Perubahan scope setelah tanggal ini hanya boleh **memotong**, tidak menambah. Setiap perubahan dicatat di `DECISIONS.md`.

---

## 1. Yang tidak berubah dari concept paper penyisihan

Ini penting untuk kepatuhan aturan: perubahan hanya boleh berupa *refinement*, bukan penggantian problem.

| Elemen | Status |
|---|---|
| Problem: akurasi pengukuran antropometri di Posyandu | **Tetap** |
| Problem: prioritisasi intervensi dengan sumber daya terbatas | **Tetap** |
| Pengguna: kader Posyandu + petugas gizi puskesmas | **Tetap** |
| Pendekatan: kanal visual (estimasi antropometri) + kanal tabular (risiko) | **Tetap** |
| Standardisasi WHO (HAZ) sebagai basis status gizi | **Tetap** |
| Explainability sebagai syarat kepercayaan tenaga kesehatan | **Tetap** |
| Fallback manual saat kanal visual gagal | **Tetap** |

Yang berubah adalah **cara mencapainya** (metode, form factor, cakupan versi pertama) — ini eksplisit diizinkan sebagai refinement.

---

## 2. MASUK MVP

### 2.1 Produk

| # | Fitur | Definisi "selesai" |
|---|---|---|
| P1 | Web app responsif, dua peran: Kader & Petugas Gizi | Bisa dibuka di browser HP dan desktop, satu codebase |
| P2 | Alur kader: unggah/ambil foto → hasil ukur → simpan kunjungan | End-to-end tanpa intervensi manual di backend |
| P3 | Fallback input manual | Kader bisa input panjang badan hasil ukur manual; skor risiko tetap keluar |
| P4 | Dashboard petugas gizi: daftar balita terurut prioritas | Bisa difilter, bisa di-drill down per anak |
| P5 | Halaman detail anak: riwayat pertumbuhan + atribusi SHAP | Grafik HAZ antar kunjungan + 3–5 faktor pendorong teratas |
| P6 | Penanganan error & peringatan kepercayaan | Estimasi berkepercayaan rendah ditandai, bukan disembunyikan |

### 2.2 Kanal visual

| # | Komponen | Catatan |
|---|---|---|
| V1 | Deteksi marker ArUco pada alas ukur | 4 marker, jarak fisik diketahui |
| V2 | Rektifikasi perspektif (homografi bidang alas) | Bukan "koreksi parallax umum" — lihat DEC-004 |
| V3 | Quality control citra | Blur (varians Laplacian), keterbacaan 4 marker, kelengkapan tubuh dalam bingkai, **geometry QC** (reprojection error / kemiringan kamera) |
| V4 | Ekstraksi endpoint tubuh pada bidang teregistrasi | Segmentasi subjek terhadap alas berwarna seragam; titik ekstrem sepanjang sumbu tubuh |
| V5a | QC postur berbasis geometri siluet (rasio, kelengkungan sumbu, deviasi, confidence segmentasi) | **Wajib** — jalur utama, tidak bergantung model pose |
| V5b | Pose estimation pretrained sebagai QC tambahan | **Bersyarat**: masuk produk hanya bila lolos CV-06 (DEC-006) |
| V0 | Plane-offset stress test sebagai gerbang arsitektur | **Dijalankan pertama** (CV-00, DEC-011) |
| V6 | Konversi piksel → sentimeter → HAZ (tabel LMS WHO) | Diverifikasi terhadap keluaran referensi resmi WHO |
| V7 | **Satu** protokol pengukuran saja | Lihat DEC-005 |
| V8 | Coverage–error trade-off: pengaruh ambang QC terhadap reject rate, coverage, dan MAE | Selective prediction; laporkan **coverage + MAE pada citra yang diterima**, bukan MAE saja (CV-11) |

### 2.3 Kanal tabular & model

| # | Komponen | Catatan |
|---|---|---|
| T1 | Generator kohort longitudinal sintetis yang transparan | Proses pembangkitan didokumentasikan di `DATA_CARD.md` |
| T2 | Feature engineering: snapshot + lintasan + kontekstual | Tiga blok fitur dipisah agar bisa di-ablasi |
| T3 | Target **prospektif** — definisi terkunci di DEC-010 | Horizon 3 bulan ± 6 minggu; penurunan HAZ ≥ 0,5 SD atau melintasi −2 |
| T4 | Baseline **ranking** B0/B1 + logistic regression B2, target & split identik | Skor kontinu agar dapat dibandingkan pada Precision@K (DEC-012) |
| T5 | Model utama: LightGBM | |
| T6 | Ablation: snapshot → +lintasan → +kontekstual | Ini yang membuktikan klaim kebaruan paper |
| T7 | Metrik prioritisasi: Precision@K, Recall@K, AUPRC | Selain precision/recall/F1 dan confusion matrix |
| T8 | SHAP per prediksi | Disajikan sebagai kontribusi fitur terhadap output model |
| T9 | Split berbasis `child_id` + temporal holdout | Lihat DEC-003 |
| T10 | Sensitivity analysis per irisan (jenis kelamin, kelompok usia, panjang riwayat, tingkat missing, kelompok SES sintetis) | Disebut *sensitivity analysis pada simulasi*, bukan bukti fairness populasi nyata |

### 2.4 Rekayasa

| # | Komponen |
|---|---|
| E1 | README dengan setup instructions yang benar-benar diuji dari nol |
| E2 | Dataset + weights di Hugging Face, link terpisah |
| E3 | Config-driven experiments, seed tetap, split tersimpan |
| E4 | Log eksperimen terisi real-time di `EXPERIMENTS.md` |
| E5 | Smoke test end-to-end |

---

## 3. FUTURE WORK (dilarang diklaim sebagai fitur)

| Item | Alasan dipotong |
|---|---|
| Protokol pengukuran kedua (mode yang tidak dipilih di DEC-005) | Praktis dua sistem CV berbeda: pose, sudut kamera, QC, failure case berbeda |
| Fine-tuning model pose khusus anatomi balita | Butuh dataset citra balita beranotasi + persetujuan etik; tidak mungkin dalam periode semifinal |
| Koreksi parallax penuh (kamera terkalibrasi, depth, multi-view) | Butuh parameter intrinsik & distorsi kamera per perangkat |
| Validasi klinis pada balita nyata | Butuh ethical clearance, informed consent, ground truth antropometer |
| Inferensi on-device (kuantisasi, pruning) | |
| Integrasi platform data kesehatan nasional | Butuh akses dan perjanjian institusional |
| WAZ / WHZ lengkap, lingkar kepala, LILA | Fokus versi pertama pada HAZ |
| Aplikasi mobile native | Web responsif memenuhi kebutuhan yang sama dalam waktu yang tersedia |

---

## 4. Batas penggunaan yang harus disebut konsisten di paper, produk, dan video

1. Tunas adalah **alat bantu skrining**, bukan diagnosis, dan bukan pengambil keputusan intervensi otomatis.
2. Hasil eksperimen pada data sintetis membuktikan **kelayakan teknis pipeline**, bukan validitas klinis.
3. Angka MAE dilaporkan pada **objek proksi berukuran diketahui**, bukan pada balita.
4. Ambang deteriorasi yang dipakai adalah **ambang operasional prototipe**, belum ambang klinis tervalidasi.
5. Validasi pengguna membuktikan **relevansi problem, kesesuaian workflow, dan usability** — bukan akurasi klinis.
