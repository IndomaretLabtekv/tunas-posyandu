#!/usr/bin/env bash
# Scaffold repo tunas-posyandu.
# Jalankan dari dalam folder repo yang sudah di-clone/init:
#   bash scaffold.sh
# Aman dijalankan berulang; tidak menimpa file yang sudah ada.

set -euo pipefail

mk() { mkdir -p "$@"; }
keep() { [ -f "$1/.gitkeep" ] || touch "$1/.gitkeep"; }
stub() { [ -f "$1" ] || printf '%s\n' "$2" > "$1"; }

# --- dokumen (isi .md yang sudah ada ditaruh di sini) ---
mk docs

# --- kanal visual ---
mk cv
stub cv/__init__.py ""
stub cv/aruco.py         '"""Deteksi marker + homografi bidang alas (V1, V2)."""'
stub cv/quality.py       '"""QC citra: blur, marker, framing, geometry (V3)."""'
stub cv/segment.py       '"""Segmentasi subjek terhadap alas + ekstraksi endpoint (V4)."""'
stub cv/posture.py       '"""QC postur berbasis geometri siluet (V5a) + pose opsional (V5b, gated CV-06)."""'
stub cv/geometry.py      '"""Konversi piksel -> cm; analisis & pembatasan plane-offset (DEC-004, DEC-011). Bukan koreksi parallax penuh."""'
stub cv/pipeline.py      '"""Orkestrasi kanal visual: citra -> hasil ukur + confidence."""'
stub cv/evaluate.py      '"""Evaluasi kanal visual secara config-driven (CV-00..CV-11)."""'

# --- kanal tabular ---
mk tabular
stub tabular/__init__.py ""
stub tabular/who_lms.py  '"""Tabel LMS WHO + konversi HAZ. Diverifikasi lewat tests/test_who_lms.py (DEC-009)."""'
stub tabular/features.py '"""Blok fitur: snapshot | trajectory | contextual (T2)."""'
stub tabular/target.py   '"""Definisi target prospektif + aturan kasus tepi (DEC-010)."""'
stub tabular/splits.py   '"""Grouped split by child_id + temporal holdout (DEC-003)."""'
stub tabular/baselines.py '"""B0/B1 ranking kontinu, B2 logistic regression (DEC-012)."""'
stub tabular/train.py    '"""Training LightGBM M1/M2/M3, config-driven."""'
stub tabular/evaluate.py '"""Metrik klasifikasi + ranking @K + slice analysis (TAB-06, TAB-11)."""'
stub tabular/explain.py  '"""SHAP per prediksi (T8)."""'

# --- backend ---
mk api
stub api/__init__.py ""
stub api/main.py         '"""FastAPI entrypoint."""'
stub api/routes.py       '"""Endpoint: /measure, /manual-entry, /children, /priority."""'
stub api/schemas.py      '"""Pydantic models."""'
stub api/store.py        '"""Persistensi kunjungan (SQLite untuk MVP)."""'

# --- frontend ---
mk web/src/pages web/src/components web/src/lib
keep web/src/pages; keep web/src/components; keep web/src/lib

# --- data ---
mk data/samples data/synth
stub data/schema.md      '# Skema data — lihat docs/DATA_CARD.md'
stub data/generate_synth.py '"""Generator kohort longitudinal sintetis (TAB-01)."""'
keep data/samples; keep data/synth

# --- eksperimen & konfigurasi ---
mk notebooks configs results/cv results/tabular scripts tests
keep notebooks
keep results/cv; keep results/tabular
# configs/ diisi config nyata, bukan .gitkeep — eksperimen paling mendesak duluan
stub configs/exp_cv_00.yaml $'# CV-00 plane-offset stress test (DEC-011) — gerbang arsitektur kanal visual\nexperiment_id: CV-00\ncamera_heights_cm: [100, 150, 200]\nobject_elevations_cm: [0, 5, 10, 15]\nframe_positions: [center, edge]\nmarker_mat_size_cm: [60, 100]\nrepeats_per_cell: 3\noutput: results/cv/cv00_plane_offset.csv'
stub scripts/download_artifacts.py '"""Unduh dataset & weights dari Hugging Face ke ./artifacts."""'
stub tests/test_who_lms.py '"""Verifikasi HAZ terhadap kasus rujukan WHO (DEC-009)."""'
stub tests/test_splits.py  '"""Verifikasi tidak ada kebocoran child_id / fitur masa depan (TAB-03)."""'
stub tests/test_smoke.py   '"""Smoke test end-to-end (SYS-02)."""'

# --- berkas akar ---
stub .gitignore $'.venv/\n__pycache__/\nnode_modules/\nartifacts/\n*.pyc\n.env\n*.tmp\n*.log\n\n# Output eksperimen kecil di results/ SENGAJA di-commit — itu jejak angka di paper.\n# Kalau ada file besar, abaikan per-nama, jangan pola *.csv.'
stub .env.example $'API_PORT=8000\nDB_PATH=./data/tunas.db\nHF_TOKEN='
stub requirements.txt '# pin versi eksak sebelum submit'
stub Makefile $'test:\n\tpytest -q\n\n# Target `demo` ditambahkan HANYA setelah docker-compose.yml ada dan diuji.\n# Jangan mencantumkan perintah yang diketahui gagal.'

echo "Scaffold selesai. Salin file .md ke docs/ dan README.md ke akar."
