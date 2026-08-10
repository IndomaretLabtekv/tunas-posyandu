# TODO Master — Per 8 Agustus 2026 (Sabtu)

> Update dokumen ini setiap kali sesuatu selesai. Sinkronkan dengan `02_docs/CLAIMS_MATRIX.md` dan `02_docs/EXPERIMENTS.md`.

## Konteks waktu

- Deadline: **10 Agustus 2026** (jam belum dikonfirmasi, asumsi 23:59 WIB)
- Ketua tim (mengerjakan kanal tabular + paper) memiliki keterbatasan waktu karena ada komitmen lomba lain di luar kota — **verifikasi ulang tanggal & durasi ketidaktersediaan saat melanjutkan sesi ini**
- Wawancara pengguna pertama: kantor RW, pagi hari, dengan ketua kader Posyandu + kemungkinan Bu RW

## A. Kanal Tabular — status: kode selesai, eksekusi belum

| # | Tugas | Status | Blocker |
|---|---|---|---|
| A1 | Unduh tabel LMS WHO resmi (length/height-for-age, L/M/S, boys & girls, **prioritaskan tabel harian**) | ⬜ Belum | — |
| A2 | `python -m scripts.prepare_who_tables --boys <file> --girls <file>` | ⬜ Belum | Butuh A1 |
| A3 | Isi `05_tests/who_reference_cases.csv` (copy dari `.template`), minimal 8 kasus dari WHO Anthro atau tabel z-score resmi | ⬜ Belum | Butuh A1 |
| A4 | `pytest tests/ -q` → target **0 skipped** (DEC-009 terpenuhi) | ⬜ Belum | Butuh A3 |
| A5 | `python -m data.generate_synth --n-children 5000 --seed 42` | ⬜ Belum | Butuh A4 |
| A6 | Jalankan `tabular.train` untuk grouped DAN temporal split, idealnya multi-seed (42–46) pada **kohort yang sama** | ⬜ Belum | Butuh A5 |
| A7 | (Opsional, lebih kuat) Generate ulang kohort dengan seed berbeda untuk uji sensitivitas generator, bukan cuma sensitivitas split | ⬜ Belum | Butuh A6 |
| A8 | Catat hasil ke `02_docs/EXPERIMENTS.md` (TAB-01 s.d. TAB-11) — dari file CSV hasil run, BUKAN dari angka di chat manapun | ⬜ Belum | Butuh A6 |
| A9 | Centang baris terkait di `02_docs/CLAIMS_MATRIX.md` (C-B1 s.d. C-B15) setelah diverifikasi | ⬜ Belum | Butuh A8 |
| A10 | Upload dataset final + model weights (`primary_model.joblib`) ke Hugging Face | ⬜ Belum | Butuh A6 |

**Semua kode tabular (`03_code_tabular/`) sudah lulus 228 test dan telah melalui 5+ putaran review berlapis** — lihat `08_process_and_review_log/` untuk daftar bug yang sudah ditemukan & diperbaiki. Jangan tulis ulang dari nol.

## B. Kanal CV — status: sebagian kode, sesi foto belum jalan

| # | Tugas | Status | Penanggung jawab |
|---|---|---|---|
| B1 | Cetak marker ArUco (`python -m cv.evaluate markers`), susun alas ukur, **ukur jarak antar sudut luar marker dengan meteran** | ⬜ Belum | Anggota CV |
| B2 | **Sesi foto CV-00** — matriks elevasi (0/5/10/15cm) × tinggi kamera (100/150/200cm) × posisi bingkai (pusat/tepi), minimal versi cepat 2×2 dulu | ⬜ Belum | Anggota CV — **butuh fisik, tidak bisa dari laptop** |
| B3 | `python -m cv.evaluate template` lalu isi manifest CSV per foto | ⬜ Belum | Butuh B2 |
| B4 | `python -m cv.evaluate run --manifest ... --mat-width-cm ... --mat-height-cm ...` | ⬜ Belum | Butuh B3 |
| B5 | **Keputusan gerbang DEC-011**: baca output `gate_decision()`, pilih 1 dari 4 mitigasi, catat di `02_docs/DECISIONS.md` | ⬜ Belum | Butuh B4 — **keputusan tim, bukan cuma teknis** |
| B6 | Tulis `cv/quality.py` — blur detection, marker readability, framing check | ⬜ Belum | Bisa ditulis paralel tanpa B2 |
| B7 | Tulis `cv/segment.py` — segmentasi subjek dari alas, ekstraksi endpoint | ⬜ Belum | Bisa ditulis paralel |
| B8 | Tulis `cv/posture.py` — QC postur berbasis siluet (wajib) + pose pretrained opsional (gated CV-06) | ⬜ Belum | Bisa ditulis paralel |
| B9 | Tulis `cv/pipeline.py` — orkestrasi citra → hasil ukur + confidence | ⬜ Belum | Butuh B6-B8 selesai |
| B10 | Kumpulkan `proxy_subjects_v1` (boneka/manekin/anggota tim berbaring) untuk klaim segmentasi & postur | ⬜ Belum | **Kalau tidak sempat, hapus klaim ini dari paper (DEC-013)** |
| B11 | Rekam & edit video demo (target 4:10, lihat `02_docs/VIDEO_SCRIPT.md`) | ⬜ Belum | 9 Agustus |

**Modul CV yang sudah ada (`04_code_cv/aruco.py`, `geometry.py`, `evaluate.py`) sudah 228 test lulus, termasuk 24 test CV pada citra sintetis** — tidak butuh foto asli untuk verifikasi logikanya, hanya untuk mengukur galat nyata (B2).

## C. Fullstack / Web App — status TIDAK DIKETAHUI dari sesi ini

Ini dikerjakan anggota tim lain dan **tidak dilaporkan progresnya ke sesi chat yang menghasilkan paket ini**. Yang harus diverifikasi segera saat melanjutkan:

| # | Tugas | Status |
|---|---|---|
| C1 | `api/` — FastAPI: main, routes, schemas, store | ❓ Tanyakan progress |
| C2 | `web/` — frontend responsif, mode Kader & Petugas Gizi (role selector, BUKAN auth penuh) | ❓ Tanyakan progress |
| C3 | Fallback input manual saat kanal visual gagal | ❓ Tanyakan progress |
| C4 | Thin vertical slice: unggah → backend → dashboard (DEC-008) | ❓ **Ini harusnya sudah jalan sejak hari pertama** |
| C5 | Integrasi SHAP (baca `tab09_shap_top_children.csv` atau load `primary_model.joblib` + panggil `Explainer`) | ❓ |
| C6 | Smoke test end-to-end (SYS-02) | ❓ |

**Risiko terbesar proyek saat ini:** kalau C4 belum jalan, ini prioritas nomor satu di atas apa pun di kanal tabular/CV — tanpa produk berjalan, kehilangan skor di Functional Product (10%), Demo (10%), dan sebagian AI Implementation (20%).

## D. Paper & Dokumentasi

| # | Tugas | Status |
|---|---|---|
| D1 | Tulis §4 Results and Discussion lengkap (bergantung A8) | ⬜ |
| D2 | §2.4 tabel pembanding dengan sitasi nyata (verifikasi status ePPGBM sebagai incumbent) | ⬜ |
| D3 | Abstract, §1.4 Kontribusi, §5 Limitations & Future Work | ⬜ |
| D4 | §4.5 Validasi pengguna dari hasil wawancara + Lampiran B (transkrip teranonimkan) | ⬜ — tulis SEGERA setelah wawancara selagi masih segar |
| D5 | `02_docs/ADOPTION.md` diisi dari jawaban wawancara (masih kosong/template) | ⬜ |
| D6 | Audit `02_docs/CLAIMS_MATRIX.md` baris per baris sebelum submit — setiap baris `Implemented=No` harus `Paper=Future Work` dan `Demo=—` | ⬜ |
| D7 | README diuji setup dari clone bersih oleh anggota lain (SYS-01) | ⬜ |
| D8 | Export PDF, cek ≤12 halaman konten | ⬜ |
| D9 | Submit — **sore hari 10 Agustus**, jangan mepet 23:59 (jam belum dikonfirmasi) | ⬜ |

## E. Item admin yang masih menggantung

- [ ] Konfirmasi jam deadline pasti ke panitia (via WhatsApp grup)
- [ ] Konfirmasi konvensi nama file proposal semifinal
- [ ] Konfirmasi apakah skor preliminary dibawa ke semifinal
- [ ] Pastikan repo GitHub tetap **private** sampai deadline lewat, lalu ubah public
- [ ] Pastikan minimal 2 orang (bukan cuma ketua tim) punya akses: Overleaf, Hugging Face, akun submit panitia
- [ ] **Tulis `HANDOVER.md`** kalau ketua tim akan tidak dapat dihubungi penuh dalam periode kritis — siapa mengerjakan apa, di mana file, siapa submit

## Prioritas kalau waktu benar-benar mepet (potong dalam urutan ini)

1. Variasi kondisi CV-08 dikurangi (cukup 2-3 sudut)
2. Ablasi dipangkas jadi M1 vs M2 saja (skip M3/kontekstual)
3. `proxy_subjects_v1` dilewati, klaim segmentasi/postur dihapus dari paper (DEC-013)
4. Dashboard tanpa filter kompleks

**Yang TIDAK BOLEH dipotong dalam kondisi apa pun:** alur end-to-end produk (thin vertical slice), fallback manual, tabel perbandingan baseline (B0 vs M2 minimal), dan video demo. Keempatnya menyangkut komponen rubrik yang tidak bisa dikompensasi dari tempat lain.
