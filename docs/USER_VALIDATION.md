# USER VALIDATION — Protokol & Hasil

> Validasi pengguna bersifat *nice to have* dalam penilaian, tetapi disebut sebagai poin plus besar, dan bentuknya bebas — cabang/unit lokal juga sah selama dapat memvalidasi permasalahan yang diangkat. Karena bobot Value Creation adalah komponen terbesar (20%) dan sub-kriteria *Impact evidence* di dalamnya secara khusus mengharapkan bukti nyata, ini adalah pengembalian tertinggi per jam kerja dalam periode semifinal.
>
> Hasil lengkap ditempatkan di **lampiran paper**, yang tidak dihitung terhadap batas 12 halaman.

---

## 1. Empat jenis validasi — jangan dicampur

| Jenis | Yang dibuktikan | Yang **tidak** dibuktikan |
|---|---|---|
| **Problem validation** | Kesalahan pengukuran & kesulitan prioritisasi memang terjadi | Bahwa solusi kami akurat |
| **Workflow validation** | Produk masuk ke alur penimbangan bulanan tanpa menambah beban | Bahwa produk akan diadopsi luas |
| **Usability feedback** | Antarmuka dapat dipahami pengguna sasaran | Bahwa keluaran benar |
| **Expert review** | Penjelasan model dinilai berguna dan masuk akal oleh ahli | Validitas klinis model |

**Clinical/model validation belum dilakukan** dan harus dinyatakan demikian di paper.

---

## 2. Target responden

| Peran | Target | Menjawab |
|---|---|---|
| Kader Posyandu | 3–5 orang | Problem pengukuran, usability alur kader |
| Petugas gizi / bidan puskesmas | 1–2 orang | Problem prioritisasi, usability dashboard |
| Ahli gizi / akademisi gizi | 1 orang | Expert review, kewajaran ambang & fitur |
| Orang tua balita | 2–3 orang (opsional) | Penerimaan pengambilan citra, kekhawatiran privasi |

Kirim ke 8–12 kontak; asumsikan tingkat respons sekitar 40%.

---

## 3. Etika & dokumentasi

Wajib, tanpa pengecualian:

- Minta izin **sebelum** merekam; minta izin terpisah sebelum mengutip.
- Anonimkan nama dan nomor telepon. Cantumkan **peran dan wilayah umum**, bukan identitas lengkap (contoh: "Kader Posyandu, Kota Bandung, R1").
- Jangan memasukkan tangkapan layar WhatsApp mentah yang memuat nomor, foto profil, atau nama.
- Jangan mengambil atau meminta foto balita.
- Sampaikan sejak awal bahwa ini proyek akademik/kompetisi mahasiswa, bukan program resmi pemerintah.

Bukti yang disimpan: transkrip teranonimkan, formulir isian, catatan sesi, dan lembar persetujuan lisan tercatat.

---

## 4. Draf pesan outreach (WhatsApp / pesan singkat)

> Selamat siang Ibu/Bapak, mohon maaf mengganggu. Saya [nama], mahasiswa Institut Teknologi Bandung. Bersama dua rekan, saya sedang mengembangkan alat bantu untuk kegiatan Posyandu — untuk membantu pencatatan pengukuran balita dan membantu petugas gizi menentukan anak mana yang perlu ditindaklanjuti lebih dulu.
>
> Sebelum melanjutkan, kami ingin memastikan bahwa yang kami buat memang sesuai dengan kondisi di lapangan. Apakah Ibu/Bapak berkenan berbagi pengalaman sekitar 20 menit, lewat telepon atau tatap muka? Kami tidak meminta data balita apa pun, hanya ingin mendengar bagaimana kegiatan pengukuran dan penentuan prioritas berjalan sehari-hari.
>
> Ini kegiatan akademik dan bukan program pemerintah. Identitas Ibu/Bapak tidak akan kami cantumkan. Terima kasih banyak atas waktunya.

Untuk ahli gizi/akademisi, ganti paragraf kedua:

> Kami ingin meminta pandangan Ibu/Bapak atas rancangan sistem ini — khususnya apakah faktor-faktor yang kami gunakan untuk menyusun prioritas masuk akal secara praktik gizi, dan apakah cara sistem menjelaskan alasannya cukup berguna bagi tenaga kesehatan.

---

## 5. Panduan wawancara (20 menit)

Pertanyaan disusun agar responden **tidak digiring**: bagian problem ditanyakan sebelum produk diperlihatkan.

### Bagian A — Kondisi saat ini (7 menit, sebelum produk ditunjukkan)
1. Bisa diceritakan bagaimana proses penimbangan dan pengukuran balita berjalan di Posyandu Ibu/Bapak?
2. Alat apa yang dipakai untuk mengukur panjang/tinggi badan? Kondisinya bagaimana?
3. Bagian mana yang paling sulit saat mengukur balita?
4. Pernah ada hasil ukur yang terasa meragukan? Apa yang dilakukan saat itu?
5. Setelah data terkumpul, siapa yang menentukan anak mana yang ditindaklanjuti lebih dulu, dan atas dasar apa?
6. Ketika bantuan atau PMT terbatas, bagaimana cara memilih penerimanya?
7. Apakah riwayat pertumbuhan bulan-bulan sebelumnya ikut dipertimbangkan? Bagaimana caranya?

### Bagian B — Reaksi terhadap produk (8 menit, tunjukkan alur nyata)
8. *(tunjukkan alur kader)* Menurut Ibu/Bapak, langkah ini bisa dilakukan sambil kegiatan penimbangan berjalan, atau justru menambah beban?
9. Bagian mana yang membingungkan?
10. Kalau sistem menolak foto dan meminta ulang, apakah itu mengganggu? Berapa kali masih wajar?
11. *(tunjukkan dashboard)* Apakah daftar seperti ini membantu, atau justru menambah pekerjaan?
12. *(tunjukkan penjelasan SHAP)* Apakah alasan seperti ini cukup jelas? Apa yang perlu ditambahkan agar Ibu/Bapak percaya pada urutannya?
13. Apa yang akan membuat Ibu/Bapak **tidak** memakai alat ini?

### Bagian C — Kelayakan (5 menit)
14. HP yang dipakai kader sehari-hari seperti apa? Sinyal di lokasi Posyandu bagaimana?
15. Siapa yang biasanya harus menyetujui penggunaan alat baru seperti ini?
16. Kalau orang tua tahu anaknya difoto untuk pengukuran, kira-kira reaksinya bagaimana?
17. Kalau ada satu hal saja yang bisa kami perbaiki, apa yang paling berguna?

### Pengukuran usability (saat responden mencoba produk)

Angka sederhana ini jauh lebih kuat daripada pertanyaan "apakah Ibu/Bapak suka":

| Metrik | Cara ukur |
|---|---|
| Task completion rate | Berapa responden menyelesaikan satu input tanpa bantuan |
| Waktu per input | Stopwatch, dari buka halaman sampai data tersimpan |
| Jumlah bantuan | Berapa kali responden bertanya atau perlu diarahkan |
| Jumlah retake foto | Berapa kali foto diambil ulang sampai lolos QC |
| Kemudahan 1–5 | Ditanyakan setelah mencoba, bukan sebelum |
| Titik kebingungan | "Bagian mana yang paling membingungkan?" |

**Yang dicatat setiap sesi:** kutipan verbatim (untuk lampiran, setelah izin), hambatan yang disebut, dan setiap ketidaksesuaian antara asumsi tim dan kenyataan. Ketidaksesuaian yang ditemukan justru bahan terkuat untuk section Discussion — menunjukkan tim mendengarkan, bukan mencari konfirmasi.

---

## 6. Formulir singkat (untuk responden yang tak sempat wawancara)

Pertanyaan disusun **berbasis perilaku**, bukan tingkat persetujuan terhadap klaim tim. Menanyakan "apakah kesalahan pengukuran adalah masalah nyata" hanya mengukur kesopanan responden; menanyakan "seberapa sering pengukuran diulang" menghasilkan bukti.

1. Dalam satu kegiatan Posyandu, kira-kira berapa kali pengukuran perlu diulang karena hasilnya diragukan? *(tidak pernah / 1–2 / 3–5 / lebih)*
2. Seberapa sulit mengukur panjang atau tinggi badan balita dibanding menimbang? *(lebih mudah / sama / lebih sulit / jauh lebih sulit)*
3. Saat menentukan anak yang ditindaklanjuti, faktor apa saja yang biasanya dipakai? *(isian bebas, boleh lebih dari satu)*
4. Seberapa sering riwayat tiga kunjungan terakhir ikut diperiksa saat menentukan tindak lanjut? *(selalu / sering / kadang / jarang / tidak pernah)*
5. Berapa kali pengambilan ulang foto yang masih dapat diterima sebelum terasa mengganggu? *(1 / 2 / 3 / lebih)*
6. Berapa tambahan waktu per anak yang masih wajar? *(< 15 detik / 15–30 detik / 30–60 detik / lebih)*
7. Hal terpenting yang perlu diperbaiki dari alat ini: ______

---

## 7. Log validasi

| ID | Tanggal | Peran responden | Wilayah | Metode | Jenis validasi | Izin kutip | Ringkasan temuan |
|---|---|---|---|---|---|---|---|
| UV-01 | | | | | Problem | ☐ | |
| UV-02 | | | | | Workflow | ☐ | |
| UV-03 | | | | | Usability | ☐ | |
| UV-04 | | | | | Expert review | ☐ | |

---

## 8. Cara memakai hasil di paper

- **§4.5 Results** — ringkasan temuan: berapa responden, peran apa, temuan utama, dan **temuan yang bertentangan dengan asumsi tim**.
- **§5 Discussion** — perubahan desain apa yang dilakukan sebagai akibat masukan. Ini yang paling bernilai: menunjukkan validasi benar-benar memengaruhi produk, bukan hiasan.
- **Lampiran B** — protokol, panduan wawancara, transkrip teranonimkan, rekap formulir.

Kalimat pelaporan yang aman:

> Validasi melibatkan N responden ([peran]). Temuan mengonfirmasi bahwa [problem] dialami di lapangan dan bahwa [alur] sesuai dengan kegiatan bulanan Posyandu. Validasi ini bersifat problem, workflow, dan usability; validitas klinis sistem belum diuji.
