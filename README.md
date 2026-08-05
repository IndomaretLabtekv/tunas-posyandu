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
|---|---|
| **Visual** | Foto balita di atas alas ber-marker ArUco → quality control → rektifikasi perspektif → estimasi panjang badan → konversi ke HAZ (standar WHO) |
| **Tabular** | Riwayat kunjungan Posyandu → fitur lintasan (growth velocity, tren Z-score, gagal tumbuh berulang) + faktor kontekstual → model risiko **prospektif** |
| **Keluaran** | Dashboard petugas gizi: daftar balita terurut prioritas + atribusi SHAP per anak + fallback input manual |

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
├── cv/                    # ArUco, quality control, segmentasi, geometri
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

> Diisi saat implementasi berjalan. Target: seseorang yang belum pernah melihat repo ini bisa menjalankan produk end-to-end dalam < 10 menit.

### Prasyarat

- Python 3.11+
- Node.js 20+ (frontend)
- (opsional) GPU — tidak wajib, pipeline berjalan di CPU

### Instalasi

```bash
git clone <REPO_URL>
cd tunas-posyandu

# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd web && npm install && cd ..
```

### Menjalankan (selama pengembangan)

```bash
# Terminal 1 — backend
uvicorn api.main:app --reload --port 8000

# Terminal 2 — frontend
cd web && npm run dev
```

Buka `http://localhost:5173`. Salin `.env.example` menjadi `.env` bila perlu mengubah konfigurasi.

> Target sebelum submission: menyediakan satu perintah `make demo` yang menjalankan seluruh stack. Perintah itu **belum tersedia** dan tidak dicantumkan sampai benar-benar diuji.

Versi seluruh dependency di-pin pada `requirements.txt` dan `package-lock.json`.

### Data & bobot model

Dataset sintetis dan trained weights di-host di Hugging Face (link disubmit terpisah):

- Dataset: `<HF_DATASET_URL>`
- Model: `<HF_MODEL_URL>`

```bash
python scripts/download_artifacts.py   # unduh dari Hugging Face ke ./artifacts
```

### Reproduksi hasil paper

```bash
python -m cv.evaluate   --config configs/exp_cv_00.yaml    # CV-00 plane-offset stress test
python -m tabular.train --config configs/exp_tab_04.yaml   # → hasil Tabel 2 paper
```

> Setiap perintah di atas tersedia setelah eksperimen terkait dijalankan dan config-nya di-commit. Status tiap eksperimen ada di [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md); config yang belum ada berarti eksperimennya belum berjalan. Seluruh eksperimen memakai seed tetap dan split yang disimpan.

## 6. Alur demo (untuk penguji)

1. Pilih mode **Kader** → ambil/unggah foto sampel dari `data/samples/` → lihat hasil QC + estimasi panjang badan + HAZ
2. Uji **fallback manual**: unggah foto yang sengaja buram → sistem menolak → masukkan hasil ukur manual → skor risiko tetap dihasilkan
3. Pilih mode **Petugas Gizi** → dashboard prioritas → klik satu anak → lihat penjelasan SHAP dan riwayat pertumbuhan

> Versi ini memakai **pemilih peran (role selector)** untuk keperluan demo, bukan autentikasi penuh. Autentikasi dan manajemen akun berada di Future Work.

## 7. Tim

| Nama | Peran |
|---|---|
| Riantama Putra | — |
| Athilla Zaidan Zidna Fann | — |
| Nicholas Wise Saragih Sumbayak | — |

## 8. Lisensi & hak

Hak atas karya tetap milik tim. Repositori bersifat privat selama periode semifinal dan dibuka ke publik setelah deadline penilaian, sesuai ketentuan panitia.
