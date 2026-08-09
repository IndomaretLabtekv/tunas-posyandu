# Eksperimen Kanal Visual — Foto Asli

Struktur:

```
experiments/
├── src/
│   ├── mats/     # foto alas asli (yoga mat dll, public domain Wikimedia)
│   └── babies/   # foto bayi asli (public domain Wikimedia) -- DI-GITIGNORE
├── results/      # output runner: overlay/ + report.csv
└── README.md
```

## Cara pakai

```bash
conda activate datsci
python scripts/run_cv_experiments.py
```

Runner membaca semua foto di `experiments/src/**`, menjalankan pipeline
kanal visual, lalu menulis:

- `results/overlay/<nama>.png` — citra + overlay deteksi/pengukuran/penolakan
- `results/report.csv` — tabel: deteksi (dengan & tanpa signature warna alas),
  hasil ukur, confidence, alasan penolakan, latency

## Catatan privasi (penting)

`experiments/src/babies/` **di-gitignore**: repo wajib public setelah deadline,
sedangkan `RESPONSIBLE_AI.md` dan `DATA_CARD.md` mengikat klaim *"tidak ada
citra balita nyata yang dikumpulkan, disimpan, atau didistribusikan"*. Foto
bayi hanya untuk pengujian lokal (lisensi public domain/CC dari Wikimedia
Commons); jangan commit, jangan pakai di paper/video.

## Sumber foto

- `mats/` — Wikimedia Commons: yoga mat & matras (ukuran standar ~61x183 cm,
  berguna sebagai ground truth aspek rasio). Beberapa foto bukan kondisi
  protokol (mat tekstur/miring/terpotong) — kegagalan deteksi di situ adalah
  perilaku yang benar (fail-closed).
- `babies/` — Wikimedia Commons: foto bayi telentang tanpa alas ukur — wajib
  ditolak oleh pipeline (false positive rate = 0).
