# Metodologi Kerja: Dual-Review Claude + GPT

## Pola kerja yang dipakai sepanjang sesi

1. Claude menulis kode/dokumen lengkap dengan test, menjalankannya, melaporkan hasil apa adanya.
2. User menyalin hasil ke GPT sebagai reviewer kedua.
3. GPT mereproduksi klaim Claude secara independen (menjalankan test sendiri, membuat kasus uji tambahan) dan melaporkan temuan.
4. Claude menerima temuan yang valid (diverifikasi ulang, bukan diterima buta), menolak/mengoreksi yang berlebihan, lalu patch + test regresi baru.
5. Siklus 2–4 diulang sampai tidak ada lagi *methodological blocker*, biasanya 2–5 putaran per modul.

**Kenapa pola ini efektif:** GPT secara konsisten menemukan kelas bug yang sama — kebocoran data (temporal/batch/test-set), ketidakkonsistenan semantik antar dua metrik yang seharusnya identik, dan klaim yang melebihi bukti. Claude sendiri cenderung tidak menangkap ini di putaran pertama karena fokus pada "apakah kode jalan", bukan "apakah angkanya bisa dipercaya".

**Kapan berhenti me-review:** setelah 3-5 putaran tanpa *methodological blocker* baru (hanya temuan kosmetik/robustness), lanjut ke modul berikutnya. Mengaudit fondasi tanpa henti adalah bentuk lain dari prokrastinasi.

## Log lengkap bug per modul (urutan kronologis)

### `tabular/who_lms.py` + `scripts/prepare_who_tables.py`

| Putaran | Bug ditemukan | Diperbaiki jadi |
|---|---|---|
| 1 (GPT) | Tabel bulanan WHO terpotong di bulan 23 (700.06 hari), padahal `MAX_AGE_DAYS=730` — usia 701-730 hari tidak bisa diinterpolasi | Simpan 1 baris anchor di atas batas usia sebelum filter |
| 1 (GPT) | `.xlsx` butuh `openpyxl`, tidak ada di requirements | Ditambahkan + engine eksplisit |
| 1 (GPT) | Toleransi test 0.01 terlalu ketat untuk tabel z-score yang dibulatkan 1 desimal | Default naik ke 0.05, kolom `tol` opsional per baris |
| 2 (GPT) | Script menulis file CSV rusak SEBELUM validasi cakupan usia gagal — artefak setengah jadi tertinggal | Semua validasi (cakupan, kelengkapan sex, duplikasi) dipindah sebelum `to_csv` |
| 2 (GPT) | Duplikasi `sex+age_days` divalidasi SETELAH `drop_duplicates()` dijalankan — pengecekan itu tidak akan pernah bisa gagal | Validasi duplikasi dipindah sebelum filtering |
| 3 (GPT) | `sex=""` → `IndexError`, bukan `ValueError`; `haz_series()` bisa crash satu batch karena satu baris rusak | Normalisasi sex tanpa `[0]`, alias L/P/male/female, `haz_series` menangkap `IndexError`/`TypeError` |
| 3 (GPT) | Inverse LMS bisa mengembalikan panjang negatif untuk Z ekstrem | Guard `base <= 0` → raise |
| 4 (GPT) | Test rujukan WHO lulus meski file cuma berisi header (0 kasus) — test yang lulus tanpa menguji apa pun | `comment="#"`, assert minimal 8 kasus, assert kolom wajib ada |
| 4 (GPT) | `tol` NaN pada CSV rujukan membuat `error > NaN` selalu False — kasus salah lolos diam-diam | Explicit: `tol = 0.05 if pd.isna(raw) else float(raw)`, assert finite & > 0 |

**Status akhir:** DEC-009 (verifikasi terhadap rujukan resmi WHO) **belum terpenuhi** — 4 test tetap skip sampai tabel WHO asli + minimal 8 reference cases diisi manusia. Ini bukan bug, ini ketergantungan pada data eksternal yang harus diunduh manual.

### `tabular/target.py` (definisi label prospektif, DEC-010)

| Putaran | Bug | Perbaikan |
|---|---|---|
| 1 (GPT) | Alasan drop salah nama: HAZ kosong pada baseline diberi label `followup_missing_length` (padahal fungsi terima kolom `haz`, bukan `length`, dan yang kosong itu baseline bukan followup) | Dipisah: `baseline_missing_haz` / `followup_missing_haz` / `*_age_out_of_mvp_range` |
| 1 (GPT) | Usia baseline NaN tetap menghasilkan label (harusnya ditolak) | Validasi eksplisit sebelum mencari follow-up |
| 2 (GPT) | Follow-up dengan `age_days` negatif diterima | Tambah `ages[j] < 0` ke kondisi tolak |
| 2 (GPT) | Index DataFrame tidak unik → `.loc[row_idx]` assignment mengenai banyak baris sekaligus | Assert `index.is_unique` di awal |
| 2 (GPT) | `child_id = "   "` (spasi) lolos validasi `isna()` | Cek `.str.strip().eq("")` |
| 3 (GPT) | Follow-up dengan usia **lebih kecil** dari baseline (korupsi data, usia mundur) tetap diterima dan diberi label | Tambah `ages[j] <= ages[i]` → `followup_age_not_after_baseline` |
| 3 (GPT) | `tolerance_days >= horizon_days` memungkinkan baris jadi follow-up dirinya sendiri | Validasi parameter di awal fungsi |

### `tabular/splits.py`

| Putaran | Bug | Perbaikan |
|---|---|---|
| 1 (GPT) | `assert_no_future_features` cuma lint nama kolom (`next`, `future`, dst) — bukan bukti nyata bebas leakage | Rename jadi `lint_future_feature_names`, tambah `assert_features_not_future` berbasis kolom provenance |
| 2 (GPT) | Blank string `child_id="   "` lolos di `_validate_frame` (beda tempat dari bug yang sama di target.py) | Cek `.str.strip().eq("")` juga di sini |
| 3 (GPT) | `assert_features_not_future` menerima `NaT` di `prediction_date`/`max_source_date` karena perbandingan dengan NaT selalu False | `errors="coerce"` + raise kalau ada yang kosong |
| **Blocker besar (GPT)** | **Temporal split tidak melakukan label maturation purge.** Baris pra-cutoff bisa punya label yang baru "matang" (diketahui) setelah cutoff — kebocoran masa depan yang nyata pada skema evaluasi temporal | Tambah kolom `label_available_date` di `target.py`, `temporal_split()` menerima `label_available_col` dan mem-purge baris yang labelnya belum matang saat cutoff |

### `tabular/baselines.py`

| Putaran | Bug | Perbaikan |
|---|---|---|
| Awal (Claude sendiri, sebelum GPT) | B0 versi pertama adalah aturan biner `HAZ<-2` — tidak bisa mengurutkan, tidak bisa dievaluasi Precision@K | Diganti jadi skor ranking kontinu `-HAZ_t` (DEC-012) |
| **Blocker besar (GPT)** | **B1 menghitung ulang mean/std/median dari TEST SET setiap dipanggil** — peringkat dua anak bisa berubah hanya karena anak ketiga ikut masuk batch. Ini "test-distribution leakage", bukan label leakage, tapi tetap membuat baseline tidak deployable | `B1Model` dataclass menyimpan seluruh state preprocessing yang dipelajari dari TRAIN, dikunci. Urutan: preprocessing dari train → bobot dari validation → test hanya predict |
| Sama | B0 mengisi `haz_t` kosong dengan median BATCH yang sedang diberi skor | `missing_score` jadi konstanta tetap (`-1e6`), tidak bergantung batch |
| Robustness (GPT) | `fit_b1()` bisa gagal diam-diam (hasil NaN) kalau training set kosong sama sekali untuk haz/slope | Raise `ValueError` eksplisit |

### `tabular/evaluate.py` (metrik)

| Putaran | Bug | Perbaikan |
|---|---|---|
| Ditemukan Claude saat run pertama | Ambang 0.5 pada prevalensi ~16% → semua probabilitas < 0.5 → F1=0 untuk SEMUA model LightGBM, terlihat seperti model rusak | Titik operasi diganti jadi kapasitas tindak lanjut (top-K%), bukan ambang 0.5 tetap |
| **Blocker besar (GPT)** | **"Top-20%" pakai ambang kuantil (`score >= threshold`), bukan pemilihan indeks eksak** — kalau ada skor kembar (tie), jumlah yang terpilih bisa melebihi/kurang dari K%. Pada skor biner (RULE), "top-20%" bisa memilih 100% baris | `capacity_predictions()` memilih indeks eksak via `argsort`, dengan `tie_break` opsional (child_id) untuk reprodusibilitas |
| **Blocker besar (GPT)** | RULE (aturan biner) tetap dievaluasi dengan AUPRC/Recall@K/Brier — skor 0/1 tidak bisa mengurutkan dalam kelompok yang sama, sehingga metrik itu tidak bermakna baginya | `score_type` wajib: `"probability"` / `"ranking"` / `"binary_rule"`. RULE hanya dapat metrik klasifikasi, dilaporkan di tabel terpisah |
| Sama putaran | Brier score dihitung untuk skor ranking (B0/B1) yang bukan probabilitas | `raw_brier` hanya untuk `score_type="probability"`, dan namanya diubah untuk menegaskan belum dikalibrasi |
| **Blocker besar (GPT), putaran berikutnya** | **Recall@K/Precision@K/Lift@K masih dihitung pakai urutan baris stabil TANPA tie_break, sementara metrik klasifikasi (F1, dll) pakai `capacity_predictions` DENGAN tie_break** — dua metrik bisa melaporkan angka berbeda dari daftar prioritas yang berbeda pada data yang sama | Semua fungsi `*_at_k` disatukan lewat `capacity_predictions`, tie_break diteruskan dari `evaluate_all` ke `evaluate_ranking` |
| Sama | `score_type` masih punya default `"probability"` — caller yang lupa mengisi diam-diam memperlakukan ranking score sebagai probabilitas | Jadi keyword-only wajib tanpa default |
| **Blocker besar (GPT)** | **`slice_report()` menghitung top-K SECARA TERPISAH di dalam setiap irisan (mis. per jenis kelamin)** — ini bukan daftar prioritas produk yang sebenarnya, dan bisa MENYEMBUNYIKAN disparitas (kelompok yang 0% masuk top-K global tetap dilaporkan recall tinggi karena top-K dihitung ulang khusus untuk kelompok itu) | `slice_report()` menerima `selected` (daftar prioritas GLOBAL dari `capacity_predictions` atas seluruh test set), melaporkan `selection_rate` dan `recall_at_global_capacity` per irisan |
| Kosmetik | `age_bin` pakai `pd.cut` tanpa `include_lowest=True` — bayi usia tepat 0 hari jatuh di luar bin | `include_lowest=True` |

### `tabular/train.py` (orkestrasi eksperimen)

| Putaran | Bug | Perbaikan |
|---|---|---|
| **Blocker besar (GPT)** | **M3 di-hardcode sebagai "best model"** untuk error analysis/slice report, padahal hasil eksperimen sering menunjukkan M2 lebih baik. Memilih "terbaik" dari hasil test juga bentuk kebocoran lain | `primary_model` ditetapkan DI MUKA di config = `"M2_plus_trajectory"`, dicatat manifest sebagai `selection_rule` |
| **Blocker besar (GPT)** | **Evaluasi dilakukan per KUNJUNGAN, bukan per ANAK** — satu anak dengan banyak kunjungan bisa muncul berkali-kali di "top-20%", sehingga denominator sebenarnya bukan 20% anak melainkan 20% baris kunjungan. Headline produk ("20% dari anak yang dipantau") jadi tidak akurat | `select_index_visits()`: satu kunjungan indeks per anak (grouped=kunjungan terakhir, temporal=kunjungan pertama setelah cutoff), dengan `assert child_id.is_unique` |
| **Blocker besar (GPT), putaran berikutnya** | **Validation masih pakai SEMUA kunjungan** (untuk tuning bobot B1 dan early-stopping LightGBM) padahal test sudah per-anak — objektif tuning ≠ objektif evaluasi akhir; dengan attendance MNAR di generator, anak yang lebih sering datang overweight saat tuning | Validation JUGA satu kunjungan indeks per anak (selalu aturan "terakhir", karena validation temporal berasal dari pool pra-cutoff) |
| Robustness | `pd.cut` age_bin exclude usia 0 hari (sama seperti di evaluate.py) | `include_lowest=True` |

### `tabular/features.py`

Modul ini relatif bersih di review pertama — tidak ada *methodological blocker* yang ditemukan GPT. Poin desain kunci yang dipertahankan: setiap baris fitur membawa `prediction_date` + `max_source_date` sebagai bukti (bukan sekadar klaim) bahwa fitur hanya memakai data ≤ t.

### `tabular/explain.py` (SHAP)

| Putaran | Bug | Perbaikan |
|---|---|---|
| 1 (GPT) | SHAP bernilai tepat 0.0 diberi arah "menurunkan" (karena kondisi `value > 0` salah untuk nol) | `direction_for()`: nol → "netral" |
| 2 (GPT) | CSV `tab09_shap_top_children.csv` cuma punya `row_index` (indeks internal), tidak ada `child_id`/tanggal/rank/skor — tidak bisa langsung dipakai frontend | Ditambah kolom `child_id`, `prediction_date`, `priority_rank`, `priority_score` |
| 3 (GPT) | **Nilai SHAP dibulatkan 4 desimal untuk tampilan, TAPI arah dihitung dari nilai mentah** — kontribusi kecil (0.00004) bisa tampil "0.0" di CSV tapi tetap diberi arah "menaikkan", baris yang membantah dirinya sendiri | `displayed_shap()` jadi satu-satunya sumber nilai; arah dihitung dari nilai yang SUDAH dibulatkan, bukan nilai mentah |
| Robustness (GPT, non-blocking) | `train.py` belum menyimpan model ke disk — `Explainer` di dokumentasi diklaim "tinggal dipanggil API" padahal model belum persist lintas proses | Tambah `joblib.dump()` model + feature_names + metadata ke `primary_model.joblib` |

### `cv/aruco.py`, `cv/geometry.py`, `cv/evaluate.py`

Ditulis satu putaran, 24 test lulus di citra alas sintetis (bukan foto asli). **Belum melalui siklus review GPT** — ini modul paling baru di sesi. Kalau melanjutkan chat ini, modul CV inilah yang paling perlu direview ulang dengan pola yang sama seperti tabular.

## Pola bug yang berulang (pelajaran untuk kode berikutnya)

1. **Kebocoran lewat statistik yang dihitung ulang dari data yang salah** (test set, batch, atau seluruh populasi padahal seharusnya per-grup) — muncul di B1 (test-distribution leakage), di evaluate awal (accuracy pada kelas timpang), di slice_report (top-K per-irisan menyembunyikan disparitas).
2. **Dua metrik yang seharusnya identik tapi dihitung dengan jalur kode berbeda** — Recall@K vs F1 sebelum disatukan tie-break-nya; nilai SHAP mentah vs yang ditampilkan.
3. **Validasi yang secara struktural tidak bisa pernah gagal** — cek duplikasi setelah `drop_duplicates()`, test rujukan WHO yang lulus meski filenya kosong.
4. **Unit analisis yang salah** — evaluasi per kunjungan padahal klaim produk per anak; ini kelas bug yang paling halus karena kodenya "jalan" dan angkanya "masuk akal", cuma tidak menjawab pertanyaan yang benar.
5. **Overclaim kecil yang menumpuk** — "praktik eksisting" untuk baseline yang belum tervalidasi wawancara, "kebaruan terbukti" untuk selisih metrik yang sebenarnya cuma "nilai tambah prediktif". Bahasa laporan butuh audit terpisah dari audit kode.

## Cara membangun prompt/instruksi yang dipakai sepanjang sesi (pola yang berhasil)

- **Minta hasil lengkap + dijalankan sendiri**, bukan cuma kode. Setiap modul disertai run nyata dengan angka asli sebelum diserahkan.
- **Jangan percaya klaim tanpa reproduksi.** Setiap kali GPT melaporkan bug, Claude mereproduksinya sendiri dengan test baru sebelum patch — beberapa kali (lihat SHAP round 1) ekspektasi test yang salah, bukan kodenya.
- **Setiap patch disertai test regresi**, bukan cuma perbaikan diam-diam — supaya bug yang sama tidak bisa masuk lagi tanpa terdeteksi.
- **Setiap keputusan desain dicatat dengan alasannya** (`DECISIONS.md`), bukan cuma hasil akhirnya — supaya anggota tim lain atau instance Claude lain bisa melanjutkan tanpa menebak-nebak kenapa sesuatu dibuat begitu.
- **Bahasa laporan (paper/video) di-audit terpisah dari kode** — kalimat seperti "praktik eksisting", "terbukti", "kebaruan" ditandai eksplisit sebagai overclaim meski kodenya sudah benar.
