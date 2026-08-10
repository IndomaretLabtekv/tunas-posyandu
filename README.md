# Tunas

**Skrining Pertumbuhan dan Prioritas Intervensi Posyandu**

> *Ukur tumbuhnya. Dahulukan yang perlu.*
>
> Tunas membantu pengukuran pertumbuhan balita dan penyusunan prioritas tindak lanjut: estimasi antropometri berbasis citra digabung dengan model prioritisasi berbasis lintasan pertumbuhan, disertai penjelasan per anak.
>
> **Tim IndomaretLabtekV** (Institut Teknologi Bandung) · Datathon 2026 RISTEK Fasilkom UI — Babak Semifinal

---

## 1. Masalah

Dua hambatan nyata di garda terdepan pemantauan gizi balita Indonesia:

1. **Akurasi pengukuran.** Pengukuran panjang/tinggi badan manual di Posyandu rawan galat akibat alat tak terkalibrasi, variasi keterampilan kader, dan sulitnya memosisikan balita. Galat 1–2 cm sudah cukup untuk menggeser klasifikasi status gizi.
2. **Prioritisasi intervensi.** Dengan anggaran, tenaga, dan stok PMT yang terbatas, petugas gizi harus memilih siapa yang ditangani lebih dulu — namun keputusan masih bertumpu pada ambang tunggal di satu titik waktu, mengabaikan lintasan pertumbuhan.

## 2. Solusi

Tunas menggabungkan dua kanal menjadi satu daftar tindakan:

| Kanal | Fungsi |
| --- | --- |
| **Visual** | Foto balita: dengan alas polos berukuran diketahui → pengukuran presisi + HAZ; TANPA alas → estimasi panjang (DEC-016, band ketidakpastian jujur) |
| **Tabular** | Riwayat kunjungan Posyandu → fitur lintasan (growth velocity, tren Z-score, gagal tumbuh berulang) + faktor kontekstual → model risiko **prospektif** |
| **Keluaran** | Dashboard petugas gizi: daftar balita terurut prioritas + faktor penting global + fallback input manual |

Yang membedakan Tunas dari aplikasi pencatatan Posyandu yang ada: sistem ini tidak berhenti di *mencatat*, melainkan **memperbaiki akurasi input** dan **mengurutkan tindak lanjut** ketika sumber daya lebih sedikit daripada kebutuhan.

## 3. Status

Repositori ini adalah implementasi babak semifinal. Lingkup MVP dikunci dan didokumentasikan — lihat [`docs/SCOPE.md`](docs/SCOPE.md).

**Apa yang berjalan dan apa yang belum** dilacak eksplisit di [`docs/CLAIMS_MATRIX.md`](docs/CLAIMS_MATRIX.md). Setiap klaim di paper dan video demo harus punya baris di sana dengan bukti eksperimen yang bisa ditelusuri.

> ⚠️ **Tunas adalah alat bantu skrining (decision support), bukan alat diagnosis.** Keputusan akhir status gizi dan rujukan tetap berada pada tenaga kesehatan. Lihat [`docs/RESPONSIBLE_AI.md`](docs/RESPONSIBLE_AI.md).

## 4. Struktur repositori

```
tunas-posyandu/
├── README.md
├── docs/                  # dokumen rujukan (dibaca juri)
│   ├── SCOPE.md           # apa yang masuk MVP, apa yang Future Work
│   ├── DECISIONS.md       # catatan keputusan teknis + alasannya
│   ├── CLAIMS_MATRIX.md   # klaim ↔ implementasi ↔ bukti ↔ paper ↔ demo
│   ├── EXPERIMENTS.md     # log eksperimen (sumber angka di paper)
│   ├── DATA_CARD.md       # asal & batasan data
│   ├── MODEL_CARD.md      # model, metrik, failure mode
│   ├── RESPONSIBLE_AI.md  # privasi, bias, batas penggunaan
│   ├── USER_VALIDATION.md # protokol & hasil validasi pengguna
│   ├── ADOPTION.md        # jalur penerapan & estimasi biaya
│   ├── PAPER_OUTLINE.md   # kerangka paper ↔ rubrik
│   ├── VIDEO_SCRIPT.md    # skrip video demo 3–5 menit
│   └── PLAN.md            # timeline & pembagian kerja
├── cv/                    # deteksi alas (markerless), QC, segmentasi, geometri
├── tabular/               # feature engineering, WHO LMS, model risiko, SHAP
├── api/                   # FastAPI backend
├── web/                   # frontend responsif (mode kader & petugas gizi)
├── data/                  # generator kohort sintetis + skema + sampel
├── configs/               # satu YAML per eksperimen — sumber angka di paper
├── results/               # output eksperimen (CSV/JSON), di-commit
├── notebooks/             # eksplorasi
├── scripts/               # utilitas (unduh artefak HF)
├── tests/
├── Makefile
├── requirements.txt
├── .env.example
└── .gitignore
```

## 5. Setup

### Menjalankan dengan Docker Compose (cara termudah)

Pastikan Docker dan Docker Compose sudah terpasang, lalu:

```bash
cp .env.example .env
make demo
make seed-demo
```

Buka `http://localhost:3000`. Backend tersedia di `http://localhost:8000/docs`.

### Alur demo tiga peran

`make seed-demo` membuat tiga akun login demo pada scope yang sama. Ibu Demo memiliki
2 anak, sedangkan 10 anak komunitas mengisi dashboard Kader dan Ahli Gizi dengan kasus
berstatus workflow beragam.
Perintah ini idempotent sehingga aman dijalankan ulang. Kredensial dibaca dari `DEMO_PASSWORD`
dan dicetak oleh seed command, bukan ditanam sebagai secret produksi.

Pada layar desktop, halaman login menyediakan tombol **Ibu Demo**, **Kader Demo**,
dan **Ahli Gizi Demo** untuk langsung masuk tanpa mengetik kredensial. Shortcut ini
hanya aktif ketika `ENABLE_DEMO_LOGIN=true`; password tetap berada di backend dan
tidak dikirim ke bundle web. Di layar mobile, gunakan form login biasa.

1. Masuk sebagai **Ibu Demo**, kirim pemeriksaan bulanan dengan foto dan berat badan.
2. Masuk sebagai **Kader Demo**, ambil kasus, catat kunjungan rumah, lalu simpan pengukuran verifikasi.
3. Masuk sebagai **Ahli Gizi Demo**, tinjau sumber data, catat intervensi atau rujukan, lalu selesaikan kasus.
4. Masuk kembali sebagai ibu untuk melihat status dan pengukuran terverifikasi pada timeline.

Hasil CV adalah sinyal skrining. UI tidak menyatakannya sebagai diagnosis terkonfirmasi.

### Menjalankan secara lokal (untuk pengembangan cepat)

```bash
# 1. PostgreSQL (bisa via Docker)
docker run -d --name tunas-postgres -e POSTGRES_USER=tunas -e POSTGRES_PASSWORD=tunas -e POSTGRES_DB=tunas -p 5432:5432 postgres:16-alpine

# 2. Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
make run-api

# 3. Frontend (terminal terpisah)
cd web && npm install && cd ..
make run-web

> **Catatan bun:** `bun install` dengan bun 1.3.14 (stable/canary) bisa gagal dengan
> `error: Fail extracting tarball for "next"` — ini regression di streaming
> extractor bun untuk paket >2 MB (lihat oven-sh/bun#34821, #34861).
> Workaround: jalankan dengan env var
> `BUN_INSTALL_STREAMING_MIN_SIZE=100000000 bun install`
> (memaksa extractor buffered). Ikuti `bun upgrade` bila versi fix sudah rilis.
```

Buka `http://localhost:3000`.

Konfigurasi via environment variable:

- `DATABASE_URL` — URL PostgreSQL (default `postgresql://tunas:tunas@localhost:5432/tunas`)
- `MODEL_PATH` — lokasi artefak inferensi JSON (default `results/tabular/final/primary_model.json`)
- `NEXT_PUBLIC_API_URL` — base URL backend untuk frontend (default `http://localhost:8000`)
- `JWT_SECRET` - secret penandatangan token; wajib diganti di luar test
- `JWT_ACCESS_MINUTES` - masa aktif token akses (default 60 menit)
- `DEMO_SCOPE_KEY` - scope bersama untuk akun demo
- `DEMO_PASSWORD` - password lokal untuk akun demo; jangan dipakai di produksi
- `ENABLE_DEMO_LOGIN` - aktifkan endpoint dan shortcut login lokal tiga peran

### Perintah Makefile

```bash
make test        # jalankan seluruh test suite (menggunakan SQLite sementara)
make run-api     # jalankan backend uvicorn
make run-web     # jalankan frontend Next.js dev
make build-web   # build frontend untuk production
make seed-demo   # buat akun dan data awal untuk alur demo tiga peran
make demo        # jalankan seluruh stack dengan Docker Compose
make down        # hentikan stack Docker Compose
```

Versi seluruh dependency di-pin pada `requirements.txt` dan `package-lock.json`.

### Data & bobot model

Dataset sintetis dan trained weights di-host di Hugging Face (link disubmit terpisah):

- Dataset: `<HF_DATASET_URL>`
- Model: `<HF_MODEL_URL>`

```bash
python scripts/download_artifacts.py   # unduh dari Hugging Face ke ./artifacts
```

Tabel LMS length-for-age resmi WHO untuk usia 0–730 hari sudah tersedia di
`data/who/lhfa_lms.csv`. Sumber, checksum, transformasi, dan tabel pembanding
independen dicatat di `data/who/provenance.json`.

### Reproduksi hasil paper

```bash
python -m cv.evaluate   --config configs/exp_cv_00.yaml    # CV-00 plane-offset stress test
python -m tabular.final_experiment --config configs/exp_tabular_final.json
python -m tabular.closure --config configs/exp_tabular_final.json --analysis all
```

Perintah tabular membangkitkan lima kohort sintetis, menjalankan B0/B1/B2/M1/M2/M3
pada grouped dan temporal holdout, lalu menulis seluruh bukti ke
`results/tabular/final/`. Ringkasan terukur ada di
[`docs/FINAL_TABULAR_RESULTS.md`](docs/FINAL_TABULAR_RESULTS.md).
Perintah closure memakai M2 yang dibekukan untuk TAB-08, TAB-10, dan audit tie
TAB-12; ia tidak melakukan tuning atau mengganti aturan ranking produksi.

Verifikasi model tersimpan pada fixture tetap, di proses baru:

```bash
python -m tabular.persist \
  --model results/tabular/final/primary_model.joblib \
  --input results/tabular/final/persistence_fixture.csv \
  --output /tmp/tunas_predictions.csv
```

## 6. Alur demo (untuk penguji)

1. Pilih mode **Kader** → ambil/unggah foto sampel dari `data/samples/` → lihat hasil QC + estimasi panjang badan + HAZ
2. Uji **fallback manual**: unggah foto yang sengaja buram → sistem menolak → masukkan hasil ukur manual → skor risiko tetap dihasilkan
3. Pilih mode **Petugas Gizi** → dashboard prioritas → klik satu anak → lihat faktor penting global dan riwayat pertumbuhan

> Versi ini memakai **pemilih peran (role selector)** untuk keperluan demo, bukan autentikasi penuh. Autentikasi dan manajemen akun berada di Future Work.

## 7. Tim

| Nama | Peran |
| --- | --- |
| Riantama Putra | — |
| Athilla Zaidan Zidna Fann | — |
| Nicholas Wise Saragih Sumbayak | — |

## 8. Lisensi & hak

Hak atas karya tetap milik tim. Repositori bersifat privat selama periode semifinal dan dibuka ke publik setelah deadline penilaian, sesuai ketentuan panitia.
