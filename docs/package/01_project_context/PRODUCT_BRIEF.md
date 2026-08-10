# Product Brief — Tunas

## Identitas (final, jangan dibahas ulang)

> **Tunas**
> **Skrining Pertumbuhan dan Prioritas Intervensi Posyandu**
> *Ukur tumbuhnya. Dahulukan yang perlu.*

- Repo: `tunas-posyandu`
- Ketiga paper juara 2025 (dicek langsung: TracKO, ChickSense, BantuBalik.in) **tidak pernah** menyebut nama brand di dalam paper — hanya di dashboard/video/repo. Paper akademik tetap pakai judul formal, sebut "Tunas" **satu kali** saat memperkenalkan implementasi.

## Masalah yang diangkat (tidak berubah dari concept paper preliminary)

1. **Akurasi pengukuran.** Pengukuran manual panjang/tinggi badan balita di Posyandu rawan galat (alat tak terkalibrasi, variasi keterampilan kader, balita sulit diposisikan). Galat 1–2 cm cukup menggeser klasifikasi status gizi.
2. **Prioritisasi intervensi.** Dengan anggaran/tenaga/PMT terbatas, petugas gizi memilih siapa ditangani duluan — saat ini bertumpu pada ambang tunggal di satu titik waktu, mengabaikan lintasan pertumbuhan.

## Solusi — dua kanal

| Kanal | Fungsi |
|---|---|
| **Visual** | Foto balita di atas alas ber-marker ArUco → QC → rektifikasi perspektif → estimasi panjang → HAZ (WHO) |
| **Tabular** | Riwayat kunjungan → fitur lintasan (velocity, tren Z-score, gagal tumbuh berulang) + kontekstual → model risiko **prospektif** |
| **Keluaran** | Dashboard petugas gizi: daftar prioritas + atribusi SHAP per anak + fallback input manual |

## Positioning yang mengikat semua deliverable

- **Alat bantu skrining, BUKAN diagnosis.** Keputusan akhir tetap di tenaga kesehatan.
- **Data sintetis = bukti kelayakan teknis, BUKAN validitas klinis.** Kalimat pelaporan yang dikunci (lihat `02_docs/DATA_CARD.md` §2.5).
- **SHAP = kontribusi fitur, BUKAN penjelasan sebab-akibat.** UI wajib menampilkan disclaimer.
- **B0 (baseline HAZ) disebut "proxy baseline", BUKAN "praktik eksisting"** — sampai dikonfirmasi lewat wawancara.
- Kapasitas tindak lanjut 20% adalah **skenario operasional**, belum fakta lapangan terkonfirmasi.

## Cakupan MVP (lihat `02_docs/SCOPE.md` untuk detail lengkap)

**Masuk:** web app responsif (mode Kader & Petugas Gizi — pemilih peran, BUKAN autentikasi penuh), protokol pengukuran telentang 0–23 bulan SAJA, ArUco + QC + geometry QC, target prospektif (deteriorasi 3 bulan ±6 minggu, HAZ turun ≥0.5 SD atau melintasi −2), model LightGBM + 3 baseline, SHAP, fallback manual, dashboard prioritas.

**Future Work (dilarang diklaim sebagai fitur):** mode berdiri, fine-tuning pose khusus balita, koreksi parallax penuh, validasi klinis pada balita nyata, on-device inference, integrasi kesehatan nasional, WAZ/WHZ lengkap, mobile app native.

## Keputusan teknis kritis (ringkasan — detail lengkap di `02_docs/DECISIONS.md`)

| ID | Keputusan |
|---|---|
| DEC-001 | Target model prospektif, bukan turunan langsung HAZ saat ini (hindari sirkularitas) |
| DEC-002/012 | Baseline harus skor ranking kontinu (B0=−HAZ, B1=HAZ+slope), bukan aturan biner — supersede oleh DEC-012 |
| DEC-003 | Split grouped by child_id + temporal holdout, wajib verifikasi bebas leakage |
| DEC-004 | "Rektifikasi perspektif + geometry QC", BUKAN "koreksi parallax" — homografi hanya valid pada bidang alas |
| DEC-005 | Protokol **telentang**, 0–23 bulan — **BERSYARAT pada hasil CV-00** |
| DEC-006 | Endpoint dari segmentasi siluet (jalur utama); pose pretrained hanya QC opsional (gated CV-06) |
| DEC-007 | Data sintetis = kelayakan teknis, bukan validitas klinis |
| DEC-008 | Thin vertical slice sebelum modul matang |
| DEC-009 | Verifikasi HAZ terhadap kasus rujukan resmi WHO — **belum terpenuhi**, 4 test masih skip |
| DEC-010 | Definisi target dikunci: horizon 91 hari ±42 hari, HAZ turun ≥0.5 SD atau melintasi −2 |
| DEC-011 | CV-00 sebagai gerbang arsitektur, dengan 4 opsi mitigasi bila gagal |
| DEC-013 | Dataset kedua `proxy_subjects_v1` untuk klaim segmentasi/postur — kalau tidak sempat, klaim dihapus |

## Temuan kuantitatif penting dari eksperimen (data sintetis, BELUM final)

Dengan kohort 3.000 anak, evaluasi per anak (bukan per kunjungan):

```
grouped split:   B0 recall@20%=0.227   M1=0.194   M2=0.355   M3=0.452
temporal split:  B0 recall@20%=0.219   M1=0.303   M2=0.407   M3=0.432
```

**Catatan penting:** Angka ini TIDAK STABIL antar ukuran kohort — versi n=1.200 sebelumnya menunjukkan M2>M3, versi n=3.000 menunjukkan M3≥M2. Kesimpulan sebelumnya soal "M3 lebih buruk" berasal dari unit evaluasi yang salah (per-kunjungan, bukan per-anak) dan sudah diperbaiki. **Jangan salin angka ini ke paper** — semuanya dari tabel LMS simulasi, bukan WHO resmi. Jalankan ulang setelah data final (lihat `07_todo_and_handover/TODO_MASTER.md` item A2).

**Galat teoretis parallax** (model pinhole, sebelum CV-00 empiris):
```
kamera 100cm, elevasi objek 8cm  -> galat ~6.1 cm  (TERLALU BESAR untuk toleransi 1cm)
kamera 200cm, elevasi objek 8cm  -> galat ~2.9 cm  (masih terlalu besar)
tinggi kamera minimum utk <1cm pd elevasi 8cm: ~568 cm (TIDAK PRAKTIS)
```
Ini alasan kuat menduga hasil CV-00 nyata akan gagal toleransi 1cm murni dengan menaikkan tinggi kamera — kemungkinan besar perlu mitigasi DEC-011 opsi 2 (reference bar) atau opsi 4 (estimasi wajib dikonfirmasi manual).
