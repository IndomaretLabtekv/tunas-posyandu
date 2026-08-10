# Aturan Kompetisi — Ringkasan Kerja

> Sumber lengkap: file asli `DATATHON_2026_SEMIFINAL_CONTEXT.md` yang diupload user di awal sesi (tidak disertakan di paket ini — minta user upload ulang jika dibutuhkan verbatim). Ini adalah ringkasan poin-poin yang dipakai sebagai dasar keputusan sepanjang sesi.

## Fakta dasar

| Item | Nilai |
|---|---|
| Kompetisi | Datathon 2026, RISTEK Fasilkom UI, dipresentasikan oleh OpenAI + mitra |
| Babak | Semifinal (lanjutan Preliminary) |
| Tim | IndomaretLabtekV (3 mahasiswa ITB) |
| Periode | 30 Juli – 10 Agustus 2026 |
| **Deadline** | **10 Agustus 2026** (jam belum dikonfirmasi panitia — asumsi kerja 23:59 WIB) |
| Semifinalis | 35 tim |
| Lolos ke final | 7 tim |
| Final | 30 Agustus 2026 |

## Tiga deliverable (semua dikumpulkan 10 Agustus)

### 1. Paper (AI Product Proposal)
- Format NeurIPS 2015, **maksimal 12 halaman konten** (references + lampiran tidak dihitung)
- Struktur: Introduction, Literature Review, Methodology, **Results and Discussion (baru di semifinal)**
- Perubahan dari concept paper preliminary **hanya boleh refinement** — problem/tema harus tetap sama. Ganti ide total = risiko diskualifikasi.

### 2. Implementation
- Link GitHub repo, README dengan setup instructions
- Model weights & dataset di **Hugging Face**, link terpisah
- Repo boleh private selama semifinal, **wajib public setelah deadline**
- **Semua fitur yang diklaim di paper wajib benar-benar ada dan jalan di produk**

### 3. Video Demo
- **3–5 menit, strict, tanpa toleransi.** <3 atau >5 menit = ditolak, bukan pengurangan poin
- Wajib: sisi bisnis + demo produk berjalan (bukan slide/mock-up)

## Rubrik penilaian (100%)

| Komponen | Bobot |
|---|---:|
| Value Creation and Demonstrated Impact | **20%** |
| Adoption, Feasibility and Scalability | 10% |
| Innovation and Meaningful Differentiation | 15% |
| Functional Product and User Experience | 10% |
| AI Implementation and Technical Excellence | **20%** |
| Evaluation, Reliability and Responsible AI | 10% |
| System Design, Engineering and Reproducibility | 5% |
| Product Demonstration and Presentability | 10% |

**Dua komponen terbesar: Value Creation (20%) dan AI Implementation (20%).** Prioritaskan keduanya saat trade-off waktu.

## Poin Q&A penting yang membentuk keputusan produk

- **Q3/Q4:** Perubahan fitur aman; ganti ide/AI produk total tidak boleh.
- **Q8:** Boleh pakai API eksternal (OpenAI dll) — aturan Kaggle preliminary (dilarang API, wajib open weights) **tidak berlaku** di semifinal.
- **Q10/Q11:** User validation **tidak wajib**, tapi disebut "poin plus besar". Bentuk bebas, kantor cabang/lokal boleh (tidak harus pusat).
- **Q12:** Hasil user validation sebaiknya masuk **lampiran paper** (tidak dihitung batas halaman), bukan cuma di video.
- **Q15:** Data sintetis diperbolehkan selama impact-nya bisa dijustifikasi dan produk benar-benar jalan.

## Item yang belum dikonfirmasi panitia (per akhir sesi)

1. Konvensi penamaan file proposal semifinal
2. Jam pasti deadline 10 Agustus
3. Apakah skor preliminary dibawa ke semifinal
4. Contoh video demo finalis tahun lalu (kemungkinan besar tidak ada — user melaporkan tahun lalu tidak ada sesi video)

## Konteks produk dari babak preliminary (concept paper lama)

Judul: **"Sistem Skrining Dini Stunting Berbasis Estimasi Antropometri Computer Vision dan Data Posyandu untuk Prioritisasi Intervensi Gizi"**

Ide awal: kanal visual (YOLOv11-pose + ArUco) untuk estimasi antropometri + kanal tabular (LightGBM + SHAP) untuk prioritisasi intervensi. Konsep ini **dipertahankan** di semifinal sebagai refinement, bukan diganti — lihat `01_project_context/PRODUCT_BRIEF.md` untuk versi yang sudah disempurnakan.
