# ADOPTION — Jalur Penerapan & Biaya

> Komponen *Adoption, Feasibility and Scalability* bernilai 10% dan sebelumnya tidak punya rumah di repo ini. Dokumen ini adalah **lembar kerja**, bukan esai: sebagian besar isinya diisi dari jawaban wawancara (UV-01..04), lalu diringkas menjadi tabel di paper §4.6.

---

## 1. Pertanyaan yang pasti ditanyakan juri

Isi jawabannya dari data, bukan dugaan. Sumber jawaban ditulis di kolom terakhir.

| Pertanyaan | Jawaban | Sumber |
|---|---|---|
| Apakah foto harus dikirim ke server? | | Arsitektur |
| Bagaimana kalau sinyal buruk / tidak ada internet? | | Arsitektur + UV |
| Siapa yang mengoperasikan servernya? | | UV (petugas gizi) |
| Siapa yang membayar? | | UV + §3 |
| Berapa lama pelatihan kader? | | UV usability |
| Apakah alur menambah antrean di hari penimbangan? | | UV metrik waktu per input |
| Siapa yang menyetujui penerapan alat baru? | | UV pertanyaan C15 |
| Bagaimana data tersinkronisasi antar Posyandu dan puskesmas? | | Arsitektur |
| HP seperti apa yang benar-benar dipakai kader? | | UV pertanyaan C14 |

## 2. Tabel jalur adopsi (masuk paper §4.6)

> **Status: hipotesis.** Tabel di bawah adalah rancangan awal jalur adopsi, bukan jalur yang telah tervalidasi. Isi dan mitigasinya wajib diperbarui berdasarkan hasil UV serta keputusan arsitektur sebelum masuk paper.

| Tahap | Pengguna | Infrastruktur | Hambatan | Mitigasi |
|---|---|---|---|---|
| Pilot | 1 Posyandu | HP kader + server puskesmas | Konektivitas | Input manual + antrean sinkronisasi offline |
| Kecamatan | Beberapa Posyandu | Server puskesmas / cloud | Pelatihan kader | Modul onboarding singkat |
| Kabupaten | Dinas kesehatan | Deployment terkelola | Integrasi data & tata kelola | API + perjanjian pengendalian data |

## 3. Estimasi biaya penerapan

Isi dengan angka nyata; kalau tidak diketahui, tulis "belum diketahui" — jangan mengarang.

| Komponen | Biaya awal | Biaya berulang | Catatan |
|---|---|---|---|
| Alas ukur ber-marker ArUco | | — | Cetak vinyl/banner; hitung per Posyandu |
| Smartphone | | — | Asumsi memakai HP kader yang sudah ada (verifikasi lewat UV) |
| Server / hosting | | per bulan | Puskesmas atau cloud kecil |
| Pelatihan kader | | per angkatan | Durasi dari hasil UV |
| Pemeliharaan | | per tahun | |
| **Total per Posyandu** | | | |

Bandingkan dengan biaya alat ukur antropometri standar sebagai konteks, bukan sebagai klaim penghematan.

## 4. Dependensi di luar kendali tim

- Persetujuan etik dan informed consent untuk pengambilan citra balita
- Persetujuan dinas kesehatan / puskesmas untuk penerapan
- Ketentuan perlindungan data pribadi yang berlaku
- Ketersediaan alas ukur standar di lokasi

Menyebut dependensi ini secara terbuka lebih baik daripada menghilangkannya: rubrik menilai *feasibility*, dan rencana yang mengabaikan hambatan terbaca sebagai rencana yang belum diperiksa.
