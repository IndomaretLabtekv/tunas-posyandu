# TUNAS — Paket Konteks Lengkap

> Diekspor dari sesi kerja dengan Claude, 4–8 Agustus 2026.
> Kompetisi: Datathon 2026 RISTEK Fasilkom UI — Babak Semifinal.
> **Deadline: 10 Agustus 2026, 23:59 WIB (asumsi, belum dikonfirmasi panitia).**

Baca urutan ini kalau kamu chat baru dan perlu onboarding cepat:

1. **File ini** (5 menit) — gambaran besar
2. `01_project_context/COMPETITION_RULES.md` — aturan lomba, rubrik penilaian
3. `01_project_context/PRODUCT_BRIEF.md` — apa yang dibangun dan kenapa
4. `07_todo_and_handover/TODO_MASTER.md` — apa yang tersisa, siapa mengerjakan apa
5. `02_docs/SCOPE.md` dan `02_docs/DECISIONS.md` — batas produk dan alasan setiap keputusan teknis

---

## 1. Apa ini

**Tunas** — *Skrining Pertumbuhan dan Prioritas Intervensi Posyandu*.

Sistem pendukung keputusan (bukan diagnosis) untuk Posyandu: menggabungkan estimasi panjang badan balita berbasis citra (kanal visual) dengan model prioritisasi berbasis lintasan pertumbuhan (kanal tabular), disertai penjelasan SHAP per anak.

Tim: **IndomaretLabtekV**, 3 mahasiswa Institut Teknologi Bandung.
Repo: `github.com/IndomaretLabtekv/tunas-posyandu` (private sampai deadline lewat).

## 2. Status per tanggal 8 Agustus 2026 (Sabtu, hari ke-4 dari 6)

| Komponen | Status |
|---|---|
| Dokumentasi strategi (12 file `.md`) | **Selesai**, sudah di-commit |
| Kanal tabular (8 modul Python) | **Selesai sebagai kode**, 228 test lulus. Belum dijalankan dengan tabel WHO resmi |
| Kanal CV | **Sebagian** — `aruco.py`, `geometry.py`, `evaluate.py` (runner CV-00) selesai. `quality.py`, `segment.py`, `posture.py`, `pipeline.py` **belum ditulis** |
| Data sintetis final | **Belum digenerate** — menunggu tabel WHO resmi |
| CV-00 (sesi foto fisik) | **Belum dijalankan** — bergantung anggota tim ketiga |
| Web app / API (fullstack) | **Status tidak diketahui dari sesi ini** — dikerjakan anggota lain, belum dilaporkan progresnya ke sesi chat ini |
| Validasi pengguna | Wawancara pertama terjadwal **8 Agustus pagi**, kantor RW |
| Paper | Kerangka ada (`PAPER_OUTLINE.md`), isi §3–§5 belum ditulis |
| Video demo | Belum direkam |
| Hugging Face upload | Belum |

**Kendala kritis:** Ketua tim (yang menjalankan sesi ini) **berangkat ke Malaysia untuk lomba lain pada 7 Agustus pagi** — sehingga sesi wawancara 8 Agustus ini adalah kesalahan tanggal dalam perencanaan sebelumnya (rencana awal bilang "berangkat 7 Agustus", tapi percakapan menunjukkan wawancara terjadi 8 Agustus; **verifikasi ulang tanggal keberangkatan yang sebenarnya saat melanjutkan**). Siapa pun yang melanjutkan chat ini harus mengonfirmasi ulang tanggal dan siapa yang punya akses penuh (Overleaf, GitHub, Hugging Face, form submit panitia).

## 3. Struktur paket ini

```
00_START_HERE/              <- kamu di sini
01_project_context/         aturan lomba, brief produk, nama & positioning
02_docs/                    12 dokumen strategi (SCOPE, DECISIONS, dst) + README repo
03_code_tabular/             8 modul Python kanal tabular (who_lms, target, splits, features,
                             baselines, evaluate, train, explain)
04_code_cv/                  3 modul Python kanal CV (aruco, geometry, evaluate/CV-00 runner)
05_tests/                   228 test pytest, 4 skip menunggu tabel WHO
06_data_and_scripts/        generator kohort sintetis + konversi tabel WHO
07_todo_and_handover/       daftar tugas tersisa per orang, urutan prioritas
08_process_and_review_log/  metodologi kerja: siklus review Claude<->GPT, bug yang
                             ditemukan tiap putaran, pelajaran, cara membangun prompt
09_user_validation/         protokol wawancara, pesan ke RT/kader, pertanyaan
10_repo_scaffold/           scaffold.sh (generator struktur folder repo) + requirements.txt
```

## 4. Cara pakai paket ini di chat baru

Upload seluruh isi zip (atau folder yang relevan) ke chat baru, lalu instruksikan sesuatu seperti:

> "Ini adalah lanjutan proyek Tunas untuk Datathon 2026. Baca `00_START_HERE/00_INDEX_AND_SUMMARY.md`, `07_todo_and_handover/TODO_MASTER.md`, dan `02_docs/SCOPE.md` dulu. Lanjutkan dari [sebutkan tugas spesifik]."

Kode di `03_code_tabular/` dan `04_code_cv/` adalah versi final yang sudah lulus review berlapis (lihat `08_process_and_review_log/`) — jangan ditulis ulang dari nol, cukup dilanjutkan atau di-debug kalau ada error saat dijalankan di environment nyata (Windows, PowerShell).

## 5. Fakta cepat yang sering ditanyakan ulang

- **Nama produk:** Tunas (final, jangan dibahas ulang)
- **Nama repo:** `tunas-posyandu`
- **Model utama:** LightGBM (M2 = snapshot + trajectory), ditetapkan di muka, bukan dipilih dari test set
- **Protokol pengukuran CV:** telentang (recumbent), 0–23 bulan, **bersyarat pada hasil CV-00**
- **Baseline:** B0 (ranking −HAZ), B1 (HAZ+slope), B2 (logistic regression), RULE (HAZ<−2, hanya klasifikasi)
- **Split:** grouped (by child_id) dan temporal (dengan purge label belum matang), evaluasi satu kunjungan indeks per anak
- **Data:** 100% sintetis, dilaporkan sebagai bukti kelayakan teknis, bukan validitas klinis
- **Reliable knowledge cutoff:** tidak relevan di sini — semua konteks lomba ada di `01_project_context/`
