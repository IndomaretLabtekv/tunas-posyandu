# VIDEO DEMO — Skrip & Rencana Produksi

> **Durasi wajib 3–5 menit, tanpa toleransi.** Kurang dari 3 menit atau lebih dari 5 menit ditolak — bukan pengurangan poin, tetapi ditolak.
>
> **Target durasi akhir: 4 menit 10 detik.** Jangan menyasar 4:55; margin itu terlalu tipis untuk kesalahan render atau penambahan menit terakhir.
>
> Bobot: 10% dari total nilai. Panitia menyarankan ≥1 menit sisi bisnis dan ≥2 menit demonstrasi produk.

---

## 1. Prinsip

1. **Produk berjalan, bukan slide.** Rekaman layar produk nyata mendominasi. Slide hanya untuk pembuka dan penutup.
2. **Tidak ada mock-up.** Setiap layar yang muncul harus berasal dari sistem yang benar-benar jalan. Menampilkan fitur yang belum ada merusak Demo Credibility.
3. **Audiens umum.** Kriteria *public-facing presentability* menuntut video dipahami orang yang tidak paham AI. Hindari jargon; kalau harus dipakai, jelaskan dalam satu kalimat awam.
4. **Tunjukkan letak AI-nya.** Kriteria demo secara khusus meminta ini. Beri penanda visual saat AI bekerja.
5. **Output apa adanya.** Termasuk saat sistem menolak citra buruk — justru itu bukti sistemnya jujur.

---

## 2. Struktur (total 4:10)

| Segmen | Durasi | Kumulatif | Isi |
|---|---:|---:|---|
| A. Masalah | 0:40 | 0:40 | Sisi bisnis |
| B. Solusi & nilai | 0:35 | 1:15 | Sisi bisnis |
| C. Demo alur kader | 1:15 | 2:30 | Produk |
| D. Demo fallback & QC | 0:30 | 3:00 | Produk |
| E. Demo dashboard & penjelasan | 0:50 | 3:50 | Produk |
| F. Validasi, batasan, penutup | 0:20 | 4:10 | Sisi bisnis |

Sisi bisnis total 1:35, demo produk total 2:35. Keduanya melewati anjuran panitia.

---

## 3. Skrip

### A. Masalah — 0:40
*Visual: kegiatan Posyandu (stok/ilustrasi bebas lisensi), grafik prevalensi.*

> Satu dari lima balita Indonesia mengalami stunting. Deteksi dini bergantung pada satu hal sederhana: mengukur panjang badan anak dengan benar, setiap bulan, di lebih dari tiga ratus ribu Posyandu.
>
> Tapi mengukur balita itu sulit. Anak bergerak, alat ukur tidak selalu terkalibrasi, dan pada anak yang berada dekat ambang pertumbuhan, selisih sekitar satu sentimeter dapat mengubah hasil klasifikasinya.
>
> Masalah kedua muncul setelah datanya terkumpul. Ketika bantuan gizi terbatas, petugas harus memilih: anak mana yang ditangani lebih dulu? Dalam banyak alur skrining, keputusan itu masih sangat bergantung pada pengukuran terkini dan ambang status gizi, sementara lintasan pertumbuhan belum selalu digunakan secara sistematis.

### B. Solusi & nilai — 0:35
*Visual: nama produk **Tunas** dengan descriptor "Skrining Pertumbuhan dan Prioritas Intervensi Posyandu" — descriptor wajib tampil bersama nama, karena "Tunas" sendiri tidak menjelaskan fungsi. Lalu diagram alur sederhana (3 ikon: foto → analisis → daftar prioritas).*

> Tunas menjawab keduanya. Bukan dengan mendiagnosis stunting — itu tetap wewenang tenaga kesehatan — melainkan dengan membantu pengukuran dan penyusunan prioritas tindak lanjut.
>
> Kader memotret balita di atas alas ukur bertanda khusus. Sistem memeriksa kualitas fotonya, menghitung panjang badan, dan mengubahnya ke standar pertumbuhan WHO.
>
> Lalu Tunas membaca riwayat pertumbuhan anak selama beberapa bulan — bukan hanya angka hari ini — dan menyusun daftar prioritas untuk petugas gizi, lengkap dengan alasan di balik setiap urutan.

### C. Demo alur kader — 1:15
*Visual: rekaman layar HP, tanpa potongan pada bagian inti.*

> Ini alur yang dipakai kader. Foto diambil dari atas, dengan empat penanda di sudut alas.
>
> *(unggah/ambil foto)* Sistem memeriksa dulu: apakah fotonya tajam, apakah keempat penanda terbaca, apakah tubuh anak seluruhnya masuk bingkai.
>
> **Di sinilah kanal visual bekerja.** Sistem memisahkan tubuh anak dari alas, menemukan titik ujung kepala dan ujung kaki, lalu memperbaiki kemiringan foto menggunakan keempat penanda sebagai acuan ukuran.
>
> *(Gunakan kata "AI" di sini **hanya** bila segmentasi memakai model neural. Bila endpoint diperoleh lewat threshold warna atau background subtraction klasik, sebut "kanal visual" — dan tunjukkan letak AI saat model risiko dan penjelasannya berjalan di segmen E.)*
>
> Hasilnya: panjang badan dalam sentimeter, dan status pertumbuhan menurut standar WHO. Kader bisa memeriksa dan mengoreksi angkanya sebelum menyimpan — sistem ini membantu, bukan menggantikan.

### D. Fallback & quality control — 0:30
*Visual: sengaja unggah foto buram → penolakan → input manual.*

> Kondisi lapangan tidak selalu ideal. Kalau fotonya buram atau kameranya terlalu miring, sistem menolak dan meminta ulang — lebih baik menolak daripada memberi angka yang salah.
>
> Dan kalau memang tidak memungkinkan memakai kamera, kader tetap bisa memasukkan hasil ukur manual. Sistem tetap berjalan.

### E. Dashboard & penjelasan — 0:50
*Visual: dashboard petugas gizi, klik satu anak.*

> Di sisi puskesmas, petugas gizi melihat daftar balita yang sudah terurut berdasarkan prioritas.
>
> Klik satu nama, dan **di sinilah model AI-nya bekerja**: sistem membaca lintasan pertumbuhan anak dan menunjukkan alasan di balik urutannya — grafik beberapa bulan terakhir, dan faktor-faktor yang paling memengaruhi skornya, misalnya pertumbuhan yang melambat atau penurunan yang berulang.
>
> Dalam simulasi kami, dengan kapasitas tindak lanjut dua puluh persen, pendekatan berbasis lintasan menangkap X persen kasus penurunan pertumbuhan — dibandingkan Y persen bila prioritas hanya didasarkan pada angka terkini.
>
> Ini yang membedakan Tunas dari sekadar aplikasi pencatatan. Anak dengan angka yang masih "aman" hari ini, tetapi terus menurun, bisa muncul lebih tinggi daripada anak dengan angka rendah yang justru sedang membaik.
>
> Petugas tetap yang memutuskan. Tunas hanya menunjukkan urutan dan alasannya.

### F. Validasi, batasan, penutup — 0:20
*Visual: ringkasan validasi + satu kalimat batasan + nama tim.*

> Rancangan ini kami uji bersama [**sebutkan persis siapa yang benar-benar diwawancarai — "tiga kader Posyandu", bukan bentuk jamak umum bila hanya satu responden**] untuk memastikan alurnya sesuai kegiatan bulanan mereka.
>
> Versi ini masih menggunakan data simulasi dan belum diuji secara klinis pada balita — itu langkah kami berikutnya, bersama mitra Posyandu.
>
> Tunas. Ukur tumbuhnya. Dahulukan yang perlu.

---

## 4. Produksi

**Rekaman**
- Rekam per segmen, jangan satu take panjang
- Rekaman layar HP untuk alur kader, layar desktop untuk dashboard
- Audio direkam terpisah kalau memungkinkan; suara ruangan adalah penyebab paling umum video terasa amatir
- Siapkan data demo yang menarik: satu anak dengan HAZ aman tapi menurun, satu anak dengan HAZ rendah tapi membaik — kontras ini yang membuat nilai produk terlihat dalam 10 detik

**Editing**
- Subtitle wajib (banyak juri menonton tanpa suara)
- Sorotan visual saat AI bekerja
- Jangan mempercepat rekaman demo secara mencolok — mengurangi kredibilitas
- Musik latar pelan, volume rendah

**Pemeriksaan akhir**
- [ ] Durasi antara 3:00 dan 5:00 — **ukur pada file final, bukan pada timeline editor**
- [ ] Setiap fitur yang tampil ada di `CLAIMS_MATRIX.md` dengan `Implemented = Yes`
- [ ] Tidak ada mock-up, tidak ada layar yang dibuat-buat
- [ ] Tidak ada data pribadi nyata yang terlihat
- [ ] Diunggah ke YouTube (unlisted) atau Google Drive, **akses diuji dari akun lain**
- [ ] Dapat dipahami oleh orang yang tidak paham AI — uji ke satu orang di luar tim
