# PLAN — Timeline & Pembagian Kerja

**Periode:** 5 → 10 Agustus 2026 · **Deadline:** 10 Agustus 2026 (jam belum dikonfirmasi panitia — asumsi kerja 23.59 WIB)

> **Re-baseline.** Rencana ini semula disusun untuk dimulai 4 Agustus. Karena blok pembuka belum dieksekusi, hari itu hilang: yang tersisa **5 hari kerja efektif**, bukan 6. Konsekuensinya, blok pembuka di §2 dan target 5 Agustus di §3 harus dikejar pada hari yang sama. Kalau tidak tercapai malam ini, jangan menambah jam — potong scope sesuai §4.

---

## Technical Architecture & Implementation Plan

> Sumber kebenaran arsitektur MVP teknis: `docs/superpowers/plans/2026-08-10-pwa-mvp-implementation.md`.
> Implementasi menyimpang dari rencana di beberapa titik (SQLite alih-alih PostgreSQL, tidak ada Docker Compose, dll.). Rencana ini menangkap pemulihan arsitektur dan sisa pekerjaan penyelarasan.

### Phase 1 — Restore defined architecture (COMPLETE)

- [x] Dependencies: `sqlalchemy==2.0.51` + `psycopg2-binary==2.9.10`
- [x] Rewrite `api/store.py` to SQLAlchemy Core — PostgreSQL default (`DATABASE_URL`), SQLite fallback for tests
- [x] Migrate tests from `DB_PATH` to `DATABASE_URL=sqlite+pysqlite:///...`
- [x] Add Docker Compose stack: `postgres`, `backend`, `frontend`
- [x] Add `api/Dockerfile`, `web/Dockerfile`, `web/.dockerignore`, root `.dockerignore`
- [x] Update `Makefile` and `README.md` §5 — Docker Compose as primary path
- [x] Verification: pytest **322 passed, 2 skipped**; frontend build OK; Postgres wiring OK

### Phase 2 — Align implementation with the original MVP plan (PENDING)

- [ ] Add `POST /manual-entry` endpoint and real manual-entry form in Kader page
- [ ] Add `GET /children` list endpoint
- [ ] Move child detail page from `/petugas/[id]` to `/anak/[id]`
- [ ] Create `web/src/lib/types.ts` and `web/src/lib/api.ts` typed API client
- [ ] Extract reusable components: `CaptureButton`, `ManualEntryForm`, `MeasurementResult`, `PriorityCard`, `GrowthChart`, `ShapBars`
- [ ] Add `web/src/app/offline/page.tsx`
- [ ] Replace empty `tests/test_smoke.py` with Docker Compose smoke test

> **Catatan scope:** Phase 1 sengaja mempertahankan pipeline CV nyata dan model M2 lintasan pertumbuhan yang sudah berjalan, alih-alih menggantinya dengan stub/cv_stub.py dan tabular_predict.py dari rencana asli. Phase 2 hanya menyelaraskan rute, komponen, dan UX tanpa mengganti lapisan CV/model.

---

## 0. Item yang menunggu panitia

Jangan diasumsikan sudah terjawab. Tanyakan malam ini di grup:

- [ ] Konvensi penamaan file proposal semifinal (preliminary memakai `TeamName_ConceptPaper.pdf`)
- [ ] Jam batas pengumpulan 10 Agustus
- [ ] Apakah skor preliminary dibawa ke penilaian semifinal
- [ ] Ketersediaan contoh video demo tahun sebelumnya

---

## 1. Peran

| Orang | Jalur | Tanggung jawab utama |
|---|---|---|
| **A** | Impact & Product | Outreach, wawancara, frontend, section Pendahuluan/Validasi/Diskusi, segmen bisnis video |
| **B** | AI Tabular | Generator data, LMS WHO, feature engineering, model + baseline + ablasi, SHAP |
| **C** | CV & Integrasi | ArUco, QC, segmentasi, geometri, FastAPI, integrasi end-to-end |

Rapat sinkronisasi 15 menit, dua kali sehari (pagi & malam). Tidak lebih.

---

## 2. Blok pembuka — jalankan sekarang juga (2–2,5 jam)

Urutan ini dipilih berdasarkan **lead time**, bukan kemudahan. Yang bergantung pada orang lain harus jalan lebih dulu.

| Waktu | Siapa | Tugas |
|---:|---|---|
| 30–45 mnt | Bertiga | **Scope freeze.** Baca `SCOPE.md` dan `DECISIONS.md`, sepakati DEC-005 (protokol pengukuran) dan DEC-006, isi tanda tangan di `SCOPE.md` |
| 20 mnt | A | Kirim 8–12 pesan outreach (`USER_VALIDATION.md` §4). **Ini yang paling tidak bisa ditunda** — jadwal kader di luar kendali tim |
| 5 mnt | A | Kirim 4 pertanyaan ke panitia (bagian 0 di atas) |
| 20 mnt | C | Buat repo, push seluruh `docs/`, undang anggota, buat branch protection sederhana |
| 45 mnt | B + C | **Thin vertical slice**: unggah citra → backend → HAZ placeholder → risiko placeholder → dashboard placeholder. Boleh semua dummy; yang penting jalurnya hidup |
| 20 mnt | B | Kunci skema `posyandu_synth_v1` (`DATA_CARD.md` §2.2) **dan definisi target DEC-010** agar tiga orang tidak menghasilkan label berbeda |
| 30 mnt | C | **CV-00 plane-offset stress test versi cepat** (DEC-011): alas marker + objek pada 2–3 elevasi, 2 tinggi kamera. Cukup untuk tahu apakah arsitektur visual bisa dipertahankan. Versi lengkap besok |

**Definisi selesai blok pembuka:** `SCOPE.md` tertanda tangan, pesan outreach terkirim, repo hidup, definisi target terkunci, ada satu request HTTP yang menempuh seluruh jalur dari unggahan sampai dashboard, dan ada angka awal CV-00.

> Dua hal yang paling menentukan malam ini: **outreach** (karena jadwal orang lain di luar kendali) dan **CV-00** (karena hasilnya menentukan apakah arsitektur kanal visual bisa dipertahankan). Sisanya bisa digeser.

---

## 3. Rencana harian

### 5 Agustus — fondasi (hari ini, setelah blok pembuka)
| PIC | Target |
|---|---|
| B | Generator kohort sintetis jalan (TAB-01); tabel LMS WHO terverifikasi terhadap kasus rujukan (CV-09/DEC-009) |
| C | CV-00 versi lengkap (matriks elevasi × tinggi kamera × posisi bingkai); **putuskan opsi mitigasi DEC-011 dan catat di `DECISIONS.md`**; lanjut CV-01, CV-02 |
| A | **Outreach terkirim ke 8–12 kontak dan minimal 1 jadwal terkonfirmasi** (wawancara dilakukan bila responden tersedia — keberhasilan hari ini tidak dinilai dari respons pihak luar); kerangka paper; halaman unggah/kamera |

**Gate malam:** HAZ dapat dihitung benar dari angka manual; ada satu MAE geometri nyata, sejelek apa pun.

### 6 Agustus — model & CV inti
| PIC | Target |
|---|---|
| B | Feature engineering 3 blok; split grouped + temporal (TAB-02, TAB-03); B0/B1/B2 + M1 jalan (TAB-04 sebagian) |
| C | Segmentasi + ekstraksi endpoint (CV-05); QC blur/marker/framing (CV-03); geometry QC (CV-04); QC postur berbasis siluet (V5a). **Uji CV-06; kalau pose tidak andal, pindahkan ke Future Work hari itu juga** |
| A | Wawancara kedua & ketiga; dashboard prioritas terhubung ke API |

**Gate malam:** ada satu tabel perbandingan model nyata, walau angkanya belum bagus.

### 7 Agustus — integrasi penuh
| PIC | Target |
|---|---|
| Bertiga | Ganti seluruh placeholder dengan modul asli; smoke test end-to-end (SYS-02) |
| B | M2, M3, ablasi (TAB-05); metrik @K (TAB-06) |
| C | Sesi pengambilan `proxy_objects_v1` **dan `proxy_subjects_v1`** (DEC-013): variasi sudut, jarak, pencahayaan, postur, oklusi (CV-07, CV-08) |
| A | SHAP tampil di UI; halaman detail anak |

**Gate malam:** produk bisa didemokan dari awal sampai akhir tanpa intervensi manual.

### 8 Agustus — hasil & penulisan
| PIC | Target |
|---|---|
| B | Robustness & noise (TAB-08); confusion matrix & error analysis (TAB-07); latency (TAB-10) |
| C | Unggah dataset & weights ke Hugging Face; README diuji dari clone bersih oleh anggota lain (SYS-01) |
| A | Tulis §4 Results and Discussion; §4.5 validasi pengguna; lampiran |

**Gate malam:** seluruh angka di `EXPERIMENTS.md` terkunci. Setelah malam ini, tidak ada eksperimen baru kecuali untuk memperbaiki bug.

### 9 Agustus — video & finalisasi
| PIC | Target |
|---|---|
| A | Rekam seluruh segmen; edit; subtitle |
| B | Finalisasi §3.5–3.6 (trade-off), Model Card, Data Card |
| C | Rapikan repo, unit test, panduan reproduksi, lampiran D |
| Bertiga | **Audit `CLAIMS_MATRIX.md` baris per baris** terhadap paper, produk, dan video |

**Gate malam:** video terekspor dengan durasi terukur; draf paper lengkap.

### 10 Agustus — buffer & submit
| Waktu | Tugas |
|---|---|
| Pagi | Perbaikan akhir paper; export PDF; hitung halaman konten |
| Siang | Cek akses video dari akun lain; cek link Hugging Face dari mode incognito |
| **Sore** | **Submit.** Jangan menunggu malam — jam batas belum dikonfirmasi |
| Setelah deadline | Ubah repositori menjadi publik |

---

## 4. Rencana cadangan

Kalau pada malam 7 Agustus integrasi belum tuntas, potong sesuai urutan ini:

1. Halaman detail anak disederhanakan (SHAP ditampilkan sebagai daftar, bukan grafik)
2. Variasi kondisi pada CV-08 dikurangi (cukup 3 sudut, bukan 6)
3. Ablasi dipangkas menjadi M1 vs M3 saja
4. Dashboard tanpa filter

**Yang tidak boleh dipotong dalam kondisi apa pun:** alur end-to-end, fallback manual, tabel perbandingan baseline, dan video demo. Keempatnya masing-masing menyangkut komponen rubrik yang tidak bisa dikompensasi dari tempat lain.

---

## 5. Kesalahan yang paling mungkin terjadi

| Risiko | Tanda awal | Pencegahan |
|---|---|---|
| Integrasi ditunda sampai modul "selesai" | Hari 3 belum ada satu request end-to-end | Thin vertical slice malam ini (DEC-008) |
| Angka eksperimen tidak tercatat | `EXPERIMENTS.md` masih kosong di hari 3 | Isi saat menjalankan, bukan sesudahnya |
| Paper mengklaim lebih dari yang ada | Kalimat "sistem mendeteksi stunting" muncul di draf | Audit `CLAIMS_MATRIX.md` sebelum submit |
| Wawancara tidak terkumpul | Belum ada balasan pada 6 Agustus | Kirim malam ini ke lebih banyak kontak; siapkan formulir singkat sebagai cadangan |
| Video melewati 5 menit | Draf pertama 5:30 | Target 4:10, potong segmen A dulu |
| Setup README tidak jalan di mesin lain | Tidak pernah diuji | SYS-01 pada 8 Agustus, dijalankan orang yang tidak menulisnya |
