# Cara Merakit Ulang Struktur Repo dari Paket Ini

Paket ini adalah **arsip kerja**, bukan struktur repo final. Kalau mau melanjutkan sebagai repo Git yang bisa langsung `git push`, ikuti langkah berikut.

## Langkah 1 — jalankan scaffold

```bash
cd /path/ke/tunas-posyandu   # repo git yang sudah di-clone
bash scaffold.sh
```

Ini membuat seluruh struktur folder (`cv/`, `tabular/`, `api/`, `web/`, `data/`, `configs/`, `results/`, `tests/`, dll) berisi **file stub** (docstring placeholder) untuk modul yang belum ditulis, plus `.gitignore`, `Makefile`, `requirements.txt`, `.env.example`.

## Langkah 2 — timpa stub dengan kode nyata dari paket ini

```bash
cp <paket>/03_code_tabular/*.py tabular/
cp <paket>/04_code_cv/*.py cv/
cp <paket>/05_tests/*.py tests/
cp <paket>/05_tests/who_reference_cases.csv.template tests/
cp <paket>/06_data_and_scripts/generate_synth.py data/
cp <paket>/06_data_and_scripts/prepare_who_tables.py scripts/
cp <paket>/02_docs/*.md docs/
cp <paket>/02_docs/PROJECT_README.md README.md
cp <paket>/10_repo_scaffold/requirements.txt .
```

**Perhatikan:** jangan sampai `04_code_cv/evaluate.py` menimpa `tabular/evaluate.py` atau sebaliknya — keduanya file berbeda dengan nama sama, tujuan foldernya berbeda.

## Langkah 3 — verifikasi

```bash
pip install -r requirements.txt
python -m pytest tests/ -q
```

Target: **228 passed, 4 skipped** (4 skip = menunggu tabel WHO resmi, lihat `07_todo_and_handover/TODO_MASTER.md` item A1-A4).

## Langkah 4 — commit

```bash
git add -A
git commit -m "feat: restore tabular and cv kernel from working package"
git push
```

## File yang TIDAK ada di paket ini (harus ditulis dari nol atau oleh anggota lain)

- `cv/quality.py`, `cv/segment.py`, `cv/posture.py`, `cv/pipeline.py`
- Semua isi `api/` (FastAPI backend)
- Semua isi `web/` (frontend)
- `data/who/lhfa_lms.csv` (tabel WHO — harus diunduh manual, tidak boleh di-hardcode di kode)
- `tests/who_reference_cases.csv` (harus diisi manual dari sumber WHO resmi, template ada tapi kosong)

## Struktur folder final yang diharapkan (setelah scaffold + isi lengkap)

```
tunas-posyandu/
├── README.md
├── Makefile / requirements.txt / .env.example / .gitignore
├── docs/                  <- dari 02_docs/
├── cv/                    <- dari 04_code_cv/ + modul yang belum ditulis
├── tabular/               <- dari 03_code_tabular/ (LENGKAP)
├── api/                   <- BELUM ADA, tanggung jawab fullstack
├── web/                   <- BELUM ADA, tanggung jawab fullstack
├── data/                  <- generate_synth.py + who/ + synth/ + samples/
├── configs/               <- exp_cv_00.yaml (dari scaffold.sh)
├── results/                <- output eksperimen, di-commit (bukan di-gitignore)
├── scripts/               <- prepare_who_tables.py
└── tests/                 <- dari 05_tests/ (LENGKAP untuk tabular+cv yang ada)
```
