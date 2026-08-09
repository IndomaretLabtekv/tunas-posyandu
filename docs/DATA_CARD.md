# DATA CARD

Dokumen ini menjelaskan asal, cara pembangkitan, dan batasan seluruh data yang dipakai Tunas. Transparansi di sini adalah syarat agar angka di section Results dapat dinilai secara adil — dan sekaligus perlindungan tim dari tuduhan overclaim.

---

## 1. Ringkasan sumber data

| Dataset | Jenis | Ukuran | Dipakai untuk | Publik? |
|---|---|---|---|---|
| `posyandu_synth_v1` | Kohort kunjungan longitudinal sintetis | ~N anak × ~V kunjungan | Melatih & mengevaluasi model risiko | Ya, Hugging Face |
| `proxy_objects_v1` | Citra objek kaku berukuran diketahui di atas alas marker | ~n citra | Validasi **geometri & konversi ukuran** | Ya, Hugging Face |
| `proxy_subjects_v1` | Boneka/manekin seukuran bayi + anggota tim berbaring | ~n citra | Validasi **segmentasi, endpoint, QC postur, failure case** | Ya, Hugging Face |
| `who_lms` | 1.462 baris LMS harian resmi WHO, usia 0–730 hari | Tabel rujukan | Konversi panjang badan → HAZ | Ya; provenance di `data/who/provenance.json` |

**Tidak ada citra balita nyata yang dikumpulkan, disimpan, atau didistribusikan dalam versi ini.** Lihat `RESPONSIBLE_AI.md`.

---

## 2. `posyandu_synth_v1` — kohort sintetis

### 2.1 Mengapa sintetis

Data antropometri Posyandu tingkat individu bersifat sensitif dan tidak tersedia secara terbuka; mengaksesnya memerlukan izin institusional dan pertimbangan etik yang tidak dapat diselesaikan dalam periode semifinal. Penggunaan data sintetis diperbolehkan dalam kompetisi ini selama pemanfaatannya dapat dijustifikasi dan produk benar-benar berjalan.

### 2.2 Struktur

| Kolom | Tipe | Keterangan |
|---|---|---|
| `child_id` | str | Identitas anak (sintetis) |
| `visit_date` | date | Tanggal kunjungan |
| `birth_date` | date | Tanggal lahir |
| `sex` | enum | M / F |
| `age_days` | int | Turunan dari `birth_date` dan `visit_date`; usia dalam hari adalah satuan kerja seluruh pipeline |
| `weight_kg` | float | Berat badan hasil ukur |
| `length_cm` | float | Panjang badan hasil ukur |
| `measure_mode` | enum | recumbent (MVP) |
| `immunization_on_schedule` | bool | Status **pada kunjungan itu** ("lengkap sesuai usia"), bukan status final sepanjang hidup anak |
| `ses_index` | float | Indikator sosial ekonomi keluarga |
| `birth_weight_kg` | float | |
| `exclusive_bf` | bool \| NA | Hasil ASI eksklusif 6 bulan; **kosong sebelum usia 180 hari** karena belum dapat diketahui |
| `visit_gap_days` | int | Jarak dari kunjungan sebelumnya |
| `measured_by_cv` | bool | Apakah kunjungan memakai kanal visual |
| `haz` | float | HAZ hasil hitung dari `length_cm` **terukur** memakai tabel LMS WHO; kosong bila panjang badan kosong atau usia di luar rentang MVP |

**Variabel laten yang TIDAK dirilis sebagai fitur.** `care_propensity` dan `exclusive_bf_history` hanya dipakai untuk membangkitkan dunia sintetis. Keduanya merepresentasikan hasil akhir yang belum diketahui pada kunjungan awal, sehingga memakainya sebagai fitur sejak usia 0 hari adalah kebocoran waktu. Yang dirilis hanyalah turunannya yang sah pada waktu `t`.

### 2.3 Cara pembangkitan

Didokumentasikan agar pembaca dapat menilai sendiri seberapa jauh hasil model merupakan konsekuensi desain generator.

1. **Lintasan dasar.** Setiap anak diberi lintasan HAZ laten dengan tingkat awal dan kecepatan perubahan yang diambil dari distribusi populasi. Parameternya **dipilih secara heuristik** agar statistik simulasi berada pada orde besaran yang serupa dengan angka nasional — bukan hasil kalibrasi terhadap data nyata.
2. **Heterogenitas.** Sebagian anak diberi perubahan arah lintasan (misal deteriorasi yang dimulai pada usia tertentu) agar tugas prediksi tidak dapat diselesaikan hanya dengan nilai HAZ terkini.
3. **Faktor kontekstual.** Variabel kontekstual memengaruhi *kecenderungan* lintasan secara probabilistik, bukan menentukan label secara deterministik.
4. **Proses pengukuran.** Panjang badan yang tercatat = nilai laten + noise pengukuran (besarnya mencerminkan variasi pengukuran manual di lapangan). Berat badan dibangkitkan dari **heuristik kenaikan berbasis usia** (~3 kg lahir, ~8 kg pada 6 bulan, ~10 kg pada 12 bulan, ~13 kg pada 24 bulan) dengan kaitan moderat terhadap HAZ; ini **bukan kurva WHO** dan bukan model klinis, hanya cukup agar kolom berat berada pada orde besaran yang benar.
5. **Ketidaklengkapan.** Kunjungan dilewat secara acak dan tidak-acak (anak dengan indeks sosial ekonomi rendah lebih sering absen), sebagian kolom kosong.
6. **Label.** Deteriorasi dihitung dari lintasan **setelah** waktu prediksi, bukan dari aturan atas fitur input.

### 2.4 Batasan yang wajib dinyatakan

- Generator adalah **model dunia yang disederhanakan**; ia tidak menangkap seluruh determinan pertumbuhan anak.
- **Statistik prevalensi wajib menyebut unit analisisnya.** Proporsi kunjungan dengan HAZ < −2 berbeda dari proporsi anak pada kunjungan pertama maupun terakhir, karena anak yang lebih rajin hadir menyumbang lebih banyak baris dan lintasan rata-rata menurun. Ketiganya dilaporkan terpisah, disertai coverage agar denominatornya transparan.
- Performa pada kohort ini menunjukkan bahwa pipeline dapat memulihkan pola yang ditanamkan simulasi. **Ini bukti kelayakan teknis, bukan validitas klinis.**
- Perbandingan antar model tetap bermakna karena semua model menghadapi generator yang sama; angka absolutnya tidak dapat dipindahkan ke populasi nyata.
- Ambang deteriorasi yang dipakai adalah ambang operasional prototipe dan perlu dikalibrasi bersama ahli gizi.

### 2.5 Kalimat pelaporan yang dikunci

> Pada kohort longitudinal sintetis, model merekonstruksi pola risiko yang ditanamkan dalam simulasi. Eksperimen ini memvalidasi kelayakan teknis pipeline serta memungkinkan perbandingan antar pendekatan pada kondisi yang terkendali, tetapi belum membuktikan validitas klinis pada populasi balita nyata.

---

## 3. `proxy_objects_v1` — citra validasi geometri

### 3.1 Isi

Citra objek kaku berukuran diketahui (diukur dengan meteran) diletakkan di atas alas ber-marker ArUco, difoto pada kombinasi jarak dan sudut kamera yang bervariasi.

| Variabel | Rentang |
|---|---|
| Panjang objek | ~30–95 cm (mencakup rentang panjang badan 0–23 bulan) |
| Jarak kamera | dicatat per citra |
| Sudut kamera terhadap normal bidang | 0° hingga miring ekstrem |
| Pencahayaan | dalam & luar ruangan |
| Ketebalan objek | dicatat — variabel kunci untuk analisis galat sisa |

### 3.2 Mengapa objek proksi, bukan balita

Memotret balita memerlukan persetujuan etik dan informed consent orang tua yang tidak dapat diperoleh secara sah dalam periode semifinal. Validasi **geometri** tidak memerlukan subjek manusia: yang diuji adalah ketepatan konversi piksel ke sentimeter pada bidang teregistrasi.

### 3.3 `proxy_subjects_v1` — citra validasi segmentasi & postur

Objek kaku tidak dapat membuktikan bahwa segmentasi menemukan ujung kepala dan ujung kaki pada bentuk tubuh, bahwa QC postur mendeteksi tungkai tertekuk, atau bahwa sistem menangani oklusi. Karena itu dataset kedua diperlukan.

| Variabel | Rentang |
|---|---|
| Subjek | Boneka seukuran bayi, manekin, anggota tim dewasa berbaring (untuk uji postur & segmentasi, bukan untuk MAE panjang badan balita) |
| Pakaian | Tanpa pakaian tebal, dengan pakaian tebal, berselimut sebagian |
| Posisi kaki | Lurus, satu tertekuk, keduanya tertekuk, rapat, terbuka |
| Oklusi | Tangan pengasuh di bahu, sebagian tubuh tertutup |
| Pencahayaan | Dalam & luar ruangan |

Untuk boneka dan manekin, panjang sebenarnya diketahui sehingga galat endpoint tetap dapat diukur. Untuk subjek dewasa, yang dievaluasi adalah keandalan segmentasi dan QC postur, bukan MAE.

**Bila dataset ini tidak sempat dikumpulkan,** klaim segmentasi dan QC postur dihapus dari paper (DEC-013).

### 3.4 Apa yang **tidak** dibuktikan kedua dataset ini

- Akurasi pada tubuh balita nyata dalam kondisi Posyandu (proporsi tubuh bayi, gerakan spontan, pakaian lapangan, penanganan oleh pengasuh)
- Keandalan segmentasi pada **balita nyata** — subjek dewasa dan boneka hanya memvalidasi mekanisme, bukan populasi sasaran
- MAE < 1 cm pada balita — klaim ini **tidak dibuat** dalam paper semifinal

---

## 4. Versi & lisensi

| Versi | Tanggal | Perubahan |
|---|---|---|
| v1 | — | Rilis awal |
| v1-final | 9 Agustus 2026 | Lima kohort final (seed 42, 314, 1618, 2026, 2718), masing-masing 1.200 anak |

Data sintetis dan citra proksi dirilis bersama repositori untuk keperluan reproduksi. Tabel LMS WHO merupakan rujukan publik milik WHO dan hanya digunakan sebagai standar konversi.
