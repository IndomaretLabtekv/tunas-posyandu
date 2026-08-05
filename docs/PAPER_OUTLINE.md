# PAPER OUTLINE — Proposal Semifinal

**Format:** NeurIPS 2015 · **Batas:** 12 halaman konten (references & lampiran tidak dihitung) · **Keluaran:** PDF

Judul dipertahankan dari concept paper penyisihan, dengan penambahan nama produk pada materi presentasi dan video. Pemenang tahun sebelumnya konsisten memakai judul akademik formal berbahasa Indonesia sementara produknya punya nama brand tersendiri — pola yang sama diikuti di sini.

---

## 1. Alokasi halaman

| Section | Halaman | Perubahan dari concept paper |
|---|---:|---|
| Abstract | 0,3 | **Tulis ulang total** — dari "diusulkan" menjadi hasil |
| 1 Pendahuluan | 1,3 | Dipadatkan; tambah kontribusi eksplisit |
| 2 Kajian Teori | 1,2 | Dipadatkan; pertajam §2.4 diferensiasi |
| 3 Metodologi | 3,0 | Diperbarui agar cocok implementasi; tambah trade-off |
| 4 Results and Discussion | **4,5** | **Baru** |
| 5 Limitations & Future Work | 0,8 | **Baru** |
| 6 Kesimpulan | 0,4 | Ditulis ulang |
| **Total** | **~11,5** | Sisakan margin dari batas 12 |
| References | — | Tidak dihitung |
| Lampiran A–D | — | Tidak dihitung |

**Prinsip alokasi.** Concept paper lama memakai 5 halaman untuk Pendahuluan + Kajian Teori + Metodologi. Di semifinal, porsi terbesar harus berpindah ke Results karena di situlah dua komponen 20% dinilai. Memadatkan Kajian Teori bukan kerugian: yang diminta rubrik adalah pembanding, bukan panjangnya tinjauan pustaka.

---

## 2. Kerangka per section

### Abstract
Empat kalimat: problem → apa yang dibangun → hasil kunci (angka nyata) → batasan. Hilangkan seluruh kata "diharapkan", "direncanakan", "target".

### 1 Pendahuluan
1.1 Urgensi stunting (pertahankan angka yang sudah ada)
1.2 Dua celah: akurasi pengukuran & prioritisasi intervensi
1.3 Ringkasan produk
1.4 **Kontribusi** — daftar bernomor 4–5 butir, masing-masing menunjuk ke section Results yang membuktikannya. Section ini paling sering dilewati peserta dan paling membantu juri menemukan nilai paper dengan cepat.

### 2 Kajian Teori
Pertahankan struktur lama, padatkan. Yang harus ditambah:
- Posisi eksplisit terhadap aplikasi pencatatan Posyandu eksisting
- Posisi terhadap penelitian estimasi antropometri berbasis citra yang berhenti pada estimasi dimensi
- **Tabel perbandingan** solusi eksisting × dimensi (akurasi input, prioritisasi, explainability, kebutuhan perangkat). Tabel ini melayani sub-kriteria *Meaningful differentiation* (15%) jauh lebih efisien daripada paragraf.
- Tabel itu harus berisi **sistem dan penelitian yang benar-benar ada, dengan sitasi** — bukan klaim umum bahwa "aplikasi lain hanya mencatat". Kandidat yang paling relevan untuk diverifikasi dan disebut namanya: sistem pencatatan gizi berbasis masyarakat yang dipakai secara nasional (mis. ePPGBM), aplikasi pemantauan tumbuh kembang komersial, dan penelitian estimasi antropometri berbasis citra atau depth sensor. Menyebut incumbent dengan namanya jauh lebih kuat daripada menyebut "aplikasi pencatatan biasa".

> **Penggunaan nama produk di paper.** Ketiga paper juara 2025 tidak pernah menyebut nama brand mereka di dalam paper — seluruhnya memakai "sistem", "solusi ini", atau "produk yang diusulkan". Ikuti pola itu: sebut **Tunas** tepat satu kali saat memperkenalkan implementasi (mis. *"Kami mengimplementasikan sistem tersebut sebagai prototipe web responsif bernama Tunas"*), setelah itu kembali ke "sistem"/"prototipe". Judul paper tetap akademik formal tanpa nama brand.

### 3 Metodologi
3.1 Konsep produk & alur pengguna — dua peran, diagram arsitektur, **cakupan versi ini dinyatakan eksplisit** (protokol telentang, usia 0–23 bulan)
3.2 Data — kohort sintetis, alasan, batasan (ringkas dari `DATA_CARD.md`)
3.3 Kanal visual — QC, rektifikasi perspektif, ekstraksi endpoint, konversi HAZ. **Nyatakan apa yang dikontrol dan apa yang tidak dikoreksi** (offset bidang tubuh)
3.4 Kanal tabular — blok fitur snapshot / lintasan / kontekstual
3.5 Formulasi target & model — definisi target prospektif, horizon, ambang operasional, protokol split
3.6 **Trade-off desain** — subsection tersendiri. Isi: keypoint vs segmentasi untuk endpoint; homografi vs kalibrasi kamera penuh; gradient boosting vs model urutan/deret waktu; ambang QC ketat vs longgar (akurasi vs cakupan). Setiap trade-off diakhiri "cocok pada kondisi X, tidak cocok pada kondisi Y". Sub-kriteria *Technical depth and justification* secara eksplisit meminta ini
3.7 Implementasi sistem — stack, struktur, reproduksibilitas

### 4 Results and Discussion — **section terpenting**
4.1 Evaluasi kanal visual
- MAE pada objek proksi, kondisi ideal vs tidak ideal
- Galat terhadap sudut kamera → dasar ambang penolakan QC
- Detection rate & reject rate
- Latency
- **Pernyataan eksplisit bahwa ini bukan validasi pada balita**

4.2 Evaluasi model prioritisasi
- Tabel utama: B0/B1/B2/M1/M2/M3 × metrik
- Ablasi blok fitur → bukti langsung klaim kebaruan lintasan
- Precision@K / Recall@K pada anggaran tindak lanjut 5%, 10%, 20%
- Kalimat dampak: *"Dengan kapasitas tindak lanjut 20%, model lintasan menangkap X% kasus deteriorasi dibanding Y% bila prioritas hanya didasarkan pada HAZ terkini (B0)."* — inilah *before → after* yang terkuantifikasi

4.3 Ketahanan & efisiensi
- Metrik terhadap level noise pengukuran & tingkat missing
- Performa pada skenario fallback (kanal visual tidak tersedia)
- Latency & estimasi biaya penerapan

4.4 Analisis kegagalan
- Confusion matrix; karakteristik false negative
- Failure mode kanal visual dan penanganannya
- Kasus nyata yang ditemukan saat pengujian

4.5 Validasi pengguna
- N responden, peran, metode
- Temuan yang mengonfirmasi asumsi **dan** yang membantahnya
- Perubahan desain yang dilakukan akibat masukan

4.6 Diskusi & jalur adopsi
- Apa arti hasil ini bagi kader dan petugas gizi
- **Tabel jalur adopsi** (wajib — sub-kriteria *adoption pathway* & *scalability* sulit dinilai dari prosa):

  | Tahap | Pengguna | Infrastruktur | Hambatan | Mitigasi |
  |---|---|---|---|---|
  | Pilot | 1 Posyandu | HP kader + server puskesmas | Konektivitas | Input manual + antrean sinkronisasi offline |
  | Kecamatan | Beberapa Posyandu | Server puskesmas / cloud | Pelatihan kader | Modul onboarding singkat |
  | Kabupaten | Dinas kesehatan | Deployment terkelola | Integrasi data & tata kelola | API + perjanjian pengendalian data |

- Jawaban eksplisit atas pertanyaan yang pasti muncul: apakah foto harus dikirim ke server, siapa yang mengoperasikan dan membayar, berapa lama pelatihan kader, apakah alur menambah antrean, siapa yang menyetujui penerapan
- Estimasi biaya penerapan per Posyandu

### 5 Limitations & Future Work
Daftar seluruh baris `Implemented = No` dari `CLAIMS_MATRIX.md`, ditulis sebagai batasan yang disadari. Section ini menaikkan skor, bukan menurunkannya: juri menilai *reliability* dan *responsible AI*, dan tim yang tahu batas sistemnya lebih dipercaya daripada tim yang tidak menyebutkan satu pun.

### 6 Kesimpulan
Tiga kalimat. Apa yang dibangun, apa yang terbukti, apa langkah berikutnya.

### Lampiran (tidak dihitung halaman)
- **A** — Detail generator data sintetis
- **B** — Protokol & transkrip validasi pengguna (teranonimkan)
- **C** — Tabel hasil lengkap & hyperparameter
- **D** — Tangkapan layar produk & panduan reproduksi

---

## 3. Peta rubrik → lokasi bukti

| Sub-kriteria | Bobot | Dijawab di |
|---|---:|---|
| Value Creation & Demonstrated Impact | 20% | §1.1–1.2, §4.2 (metrik @K), §4.5, §4.6, Lampiran B |
| Adoption, Feasibility & Scalability | 10% | §3.1, §4.3 (biaya), §4.6, §5 |
| Innovation & Meaningful Differentiation | 15% | §2.4 (tabel pembanding), §3.5, §4.2 (ablasi lintasan) |
| Functional Product & UX | 10% | §3.1, §3.7, §4.5, video, repo |
| AI Implementation & Technical Excellence | 20% | §3.3–3.6 (terutama §3.6 trade-off), §4.1–4.3 |
| Evaluation, Reliability & Responsible AI | 10% | §4.1–4.4, §5, `RESPONSIBLE_AI.md` |
| System Design & Reproducibility | 5% | §3.7, README, Hugging Face |
| Product Demonstration & Presentability | 10% | Video |

---

## 4. Aturan bahasa

Ganti seluruhnya:

| Jangan | Pakai |
|---|---|
| diusulkan, direncanakan, diharapkan | kami mengimplementasikan, sistem menghasilkan |
| akan dikumpulkan | dikumpulkan / dibangkitkan |
| target MAE di bawah 1 cm | MAE terukur X cm pada objek proksi |
| model akan mengklasifikasikan | model mencapai … dibanding baseline … |

Kecuali di section 5 (Future Work), di mana bentuk prospektif justru wajib.

---

## 5. Checklist sebelum export

- [ ] Konten ≤ 12 halaman; references & lampiran terpisah
- [ ] Setiap angka punya ID eksperimen di `EXPERIMENTS.md`
- [ ] Setiap fitur yang disebut ada di `CLAIMS_MATRIX.md` dengan `Implemented = Yes`
- [ ] Tidak ada kalimat yang mengklaim validitas klinis
- [ ] Section Kontribusi menunjuk ke bukti
- [ ] Gambar terbaca saat dicetak hitam-putih
- [ ] Nama file mengikuti konvensi panitia — **konfirmasi dulu, belum ada aturan resmi untuk semifinal**
