# RESPONSIBLE AI

Dokumen ini menjadi dasar pembahasan pada sub-kriteria *Evaluation, Reliability and Responsible AI*, dan mengikat cara produk berperilaku — bukan sekadar pernyataan di paper.

---

## 1. Posisi sistem

**Tunas adalah alat bantu skrining dan pendukung keputusan.** Tunas tidak menetapkan diagnosis, tidak menetapkan status gizi secara final, dan tidak memutuskan siapa yang menerima atau tidak menerima intervensi. Keputusan berada pada tenaga kesehatan.

Konsekuensi desain yang mengikuti dari posisi ini:

- Setiap estimasi visual menampilkan nilai ukur dan tingkat kepercayaannya, sehingga dapat diperiksa dan dikoreksi kader.
- Kader selalu dapat menimpa hasil estimasi dengan hasil ukur manual.
- Mode ESTIMASI tanpa referensi (DEC-016) memberi angka KASAR ber-band
  ketidakpastian untuk foto tanpa alas; tidak ada gerbang semantik subjek
  (foreground non-manusia besar pun dapat menghasilkan estimasi) -- angka
  ini tidak pernah diklaim sebagai pengukuran.
- Dashboard menyajikan **urutan prioritas**, bukan instruksi tindakan.
- Anak berskor rendah tetap tampil dalam daftar pemantauan; sistem tidak pernah menyembunyikan anak.

### Kontrak skrining 0–23 bulan

Workflow ini mendukung `0 <= age_days <= 730`, menggunakan panjang badan
telentang (*recumbent length*), dan tidak mengimplementasikan tinggi berdiri.
Hasil screening selalu diberi label **indikasi gangguan pertumbuhan — perlu
verifikasi**. Label ini bukan diagnosis dan bukan konfirmasi stunting.

Tanggung jawab peran dikunci sebagai berikut:

- `mother` mengirim data pemeriksaan pertumbuhan anak;
- `kader` menangani kontak, kunjungan rumah, pengukuran ulang, dan catatan
  tindak lanjut;
- `nutritionist` (ahli gizi/Puskesmas) meninjau hasil terverifikasi dan
  memutuskan intervensi atau rujukan.

Pengukuran yang dikirim ibu berstatus `unverified`. Pengukuran menjadi
`verified` hanya setelah dikonfirmasi kader atau tenaga kesehatan, dan sumber
konfirmasi harus terlihat pada riwayat kasus.

Status kasus mengikuti transisi tertutup berikut:

```text
submitted → normal
submitted → needs_review → assigned → home_visit → verified_risk
verified_risk → referred → resolved
needs_review → resolved
```

Tidak ada transisi lain yang diizinkan; `resolved` bersifat terminal. Status
`needs_review` tidak boleh dirender sebagai `stunting` atau diagnosis.

## 2. Privasi & data pribadi

### Dalam versi semifinal
- Tidak ada citra balita nyata yang dikumpulkan, disimpan, atau didistribusikan.
- Data kunjungan yang dipakai bersifat sintetis; tidak ada individu nyata yang dapat diidentifikasi.
- Validasi pengguna, **apabila berhasil dilakukan** pada versi semifinal, hanya melibatkan responden dewasa (kader, petugas gizi, bidan, atau ahli gizi); identitas dianonimkan dan persetujuan diminta sebelum perekaman maupun pengutipan (lihat `USER_VALIDATION.md`). Status pelaksanaannya ada di log UV-01..04 — selama log itu kosong, tidak ada klaim validasi yang boleh dibuat.

### Yang disyaratkan sebelum penerapan nyata
- Persetujuan etik institusional dan informed consent orang tua/wali untuk setiap pengambilan citra.
- Citra diproses untuk memperoleh angka ukur, lalu dihapus atau disimpan dengan retensi terbatas — bukan disimpan tanpa batas.
- Pemisahan identitas anak dari artefak citra; enkripsi saat transit dan saat diam.
- Kepatuhan terhadap ketentuan perlindungan data pribadi yang berlaku.
- Kejelasan siapa pengendali data: puskesmas/dinas kesehatan, bukan pengembang.

## 3. Bias & keadilan

| Sumber bias potensial | Dampak | Mitigasi versi ini | Yang masih terbuka |
|---|---|---|---|
| Kualitas kamera & pencahayaan berbeda antar Posyandu | Posyandu dengan perangkat lebih buruk lebih sering ditolak QC | Fallback manual memastikan anak tetap terskor | Uji lintas perangkat nyata |
| Warna kulit, pakaian, alas tidak standar | Segmentasi memburuk pada kondisi tertentu | Alas standar berwarna seragam; estimasi ditandai saat tidak stabil | Evaluasi lintas subjek beragam |
| Ketidakhadiran tidak acak (anak dari keluarga rentan lebih sering absen) | Anak paling berisiko justru punya data paling sedikit | Fitur jarak kunjungan disertakan; keterbatasan ditampilkan di UI | Strategi penjangkauan aktif |
| Fitur sosial ekonomi sebagai prediktor | Risiko memperkuat stigma atau menjadi proksi diskriminatif | Kontribusi fitur ditampilkan terbuka lewat SHAP sehingga dapat diaudit petugas | Perlu keputusan kebijakan apakah fitur ini layak dipakai — harus melibatkan ahli gizi & dinas kesehatan |
| Kohort sintetis mencerminkan asumsi pembuatnya | Bias generator menjadi bias model | Proses pembangkitan didokumentasikan penuh | Validasi pada data nyata |

Catatan jujur: penggunaan indikator sosial ekonomi sebagai prediktor adalah **pilihan yang perlu dipertanggungjawabkan**, bukan pilihan netral. Paper harus membahasnya, bukan menyembunyikannya di daftar fitur.

## 3b. Evaluasi yang menyertai klaim keandalan

Dua analisis berikut wajib ada karena tanpa keduanya angka performa mudah menyesatkan:

- **Coverage–error trade-off (CV-11).** Ambang QC yang ketat menurunkan MAE tetapi juga menurunkan cakupan. Laporkan keduanya berpasangan: berapa persen citra diterima, dan berapa MAE pada citra yang diterima.
- **Sensitivity analysis per irisan (TAB-11).** Metrik dipecah per jenis kelamin, kelompok usia, panjang riwayat kunjungan, tingkat missing, dan kelompok SES sintetis. Ini **bukan** bukti fairness pada populasi nyata dan harus disebut sebagai *sensitivity analysis pada simulasi*.

## 4. Keandalan

| Risiko | Penanganan |
|---|---|
| Estimasi salah diterima sebagai kebenaran | Nilai kepercayaan ditampilkan; hasil di bawah ambang ditandai; kader diminta ukur ulang |
| Kanal visual gagal total di lapangan | Fallback manual: kanal tabular tetap menghasilkan skor |
| Model dipakai pada populasi berbeda | Dinyatakan sebagai syarat: kalibrasi ulang sebelum penerapan di wilayah baru |
| Ketergantungan berlebih pada urutan sistem | Dashboard menyajikan alasan dan riwayat, bukan hanya angka, agar petugas menilai ulang |
| Kesalahan diam pada konversi Z-score | Diverifikasi terhadap kasus rujukan WHO sebagai unit test |

## 5. Batas klaim (mengikat untuk paper dan video)

Yang **tidak boleh** dinyatakan:
- Bahwa sistem mendiagnosis atau mengonfirmasi stunting; sistem hanya memberi
  **indikasi gangguan pertumbuhan — perlu verifikasi**
- Bahwa akurasi klinis telah terbukti
- Bahwa MAE pada balita nyata telah diukur
- Bahwa ambang risiko telah tervalidasi secara klinis
- Bahwa SHAP menjelaskan penyebab risiko gizi anak

Yang **boleh** dinyatakan:
- Bahwa pipeline berjalan end-to-end dan dapat direproduksi
- Bahwa galat geometri telah diukur pada objek berukuran diketahui, pada kondisi ideal dan tidak ideal
- Bahwa pada kohort sintetis, pemanfaatan lintasan pertumbuhan meningkatkan metrik dibanding pendekatan snapshot dan prioritas berbasis HAZ terkini
- **Bila didukung UV-01/UV-02:** bahwa responden yang benar-benar diwawancarai mengonfirmasi relevansi problem dan/atau kesesuaian alur kerja. Sebut peran yang benar-benar hadir — kalau hanya kader yang diwawancarai, jangan menulis "kader dan petugas gizi"

## 6. Yang akan dilakukan sebelum pilot nyata

1. Persetujuan etik dan protokol informed consent
2. Kalibrasi ambang risiko bersama ahli gizi
3. Validasi MAE terhadap antropometer standar pada subjek balita
4. Uji lintas perangkat dan lintas lokasi
5. Perjanjian pengendalian data dengan dinas kesehatan
6. Pelatihan kader dan mekanisme pelaporan kesalahan
