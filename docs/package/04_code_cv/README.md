# Kanal CV — Cara Pakai dan Status

## Status jujur

Hanya **3 dari 7 modul yang direncanakan** sudah ditulis: `aruco.py`, `geometry.py`, `evaluate.py` (runner CV-00).

**Belum ditulis:** `quality.py` (blur/framing/marker readability), `segment.py` (segmentasi subjek dari alas), `posture.py` (QC postur siluet + pose opsional), `pipeline.py` (orkestrasi citra → hasil ukur).

**Belum melalui siklus review GPT** seperti modul tabular — kalau melanjutkan sesi ini, modul CV inilah yang paling butuh direview ulang dengan pola yang sama (lihat `08_process_and_review_log/REVIEW_METHODOLOGY_AND_BUG_LOG.md` untuk pola bug yang biasa ditemukan: kebocoran statistik dari data yang salah, dua fungsi yang harusnya identik tapi beda jalur, validasi yang tidak bisa gagal, unit yang salah).

## Modul yang sudah ada

### `aruco.py`
Deteksi 4 marker ArUco, hitung homografi bidang alas → koordinat cm. Fungsi kunci: `detect_markers()`, `distance_cm()`, `rectify()`, `save_marker_sheet()` (generate PNG marker untuk dicetak).

### `geometry.py`
Analisis plane-offset (parallax) — **BUKAN koreksi**, hanya pengukuran dan pembatasan (DEC-004). Fungsi kunci:
- `scale_error_factor(camera_height, object_elevation)` — rumus pinhole sederhana
- `expected_bias_cm()` — perkiraan galat teoretis, dipakai membandingkan dengan hasil empiris CV-00
- `GeometryQC.check()` — terima/tolak citra berdasarkan kemiringan kamera & reprojection error

### `evaluate.py` (runner CV-00)
CLI dengan 3 subcommand:
```bash
python -m cv.evaluate markers --out data/markers      # cetak marker
python -m cv.evaluate template --out manifest.csv      # buat template manifest foto
python -m cv.evaluate run --manifest manifest.csv \
  --mat-width-cm <hasil ukur meteran> --mat-height-cm <hasil ukur meteran> \
  --out results/cv
```
Keluaran termasuk **keputusan gerbang otomatis** (`gate_decision()`) yang membaca hasil dan menyebut mitigasi DEC-011 yang relevan kalau gagal.

## Temuan teoretis penting (dari `test_cv_geometry.py`, model pinhole, BELUM empiris)

```
galat pada panjang 70cm:
  kamera 100cm, elevasi 8cm  -> ~6.1 cm   (JAUH di atas toleransi 1cm)
  kamera 150cm, elevasi 8cm  -> ~3.9 cm
  kamera 200cm, elevasi 8cm  -> ~2.9 cm
  tinggi kamera minimum utk <1cm error pada elevasi 8cm: ~568 cm (TIDAK PRAKTIS)
```

**Implikasi:** kemungkinan besar CV-00 empiris akan gagal toleransi 1cm murni dengan menaikkan tinggi kamera. Siapkan mental untuk memilih mitigasi DEC-011 opsi 2 (reference bar pada elevasi tubuh) atau opsi 4 (estimasi visual wajib dikonfirmasi manual) — lihat `02_docs/DECISIONS.md` DEC-011 untuk keempat opsi lengkap.

## Cara pakai testnya (tidak butuh foto asli)

24 test di `05_tests/test_cv_geometry.py` berjalan pada **citra alas sintetis yang dibuat kode**, bukan foto asli — jadi bisa diverifikasi logikanya kapan saja:

```bash
pip install -r ../10_repo_scaffold/requirements.txt   # termasuk opencv-python
python -m pytest tests/test_cv_geometry.py -q
```

## Yang harus dilakukan berikutnya (urutan prioritas)

1. **Sesi foto CV-00 fisik** (lihat `07_todo_and_handover/TODO_MASTER.md` B1-B5) — ini gerbang DEC-011, HARUS dilakukan sebelum investasi besar ke pipeline visual selanjutnya.
2. Tulis `quality.py`, `segment.py`, `posture.py` — bisa ditulis PARALEL tanpa menunggu hasil foto.
3. Tulis `pipeline.py` setelah ketiganya selesai.
4. Review ulang seluruh modul CV dengan pola dual-review yang sama seperti tabular.
