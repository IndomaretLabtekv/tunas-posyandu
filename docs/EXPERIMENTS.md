# EXPERIMENTS — Log Eksperimen

> **Aturan:** diisi **saat eksperimen dijalankan**, bukan direkonstruksi dari ingatan menjelang deadline. Setiap angka yang masuk ke paper harus punya baris di sini.
>
> Setiap entri wajib memuat: tanggal, penanggung jawab, commit hash, config, seed, definisi split, dan hasil apa adanya — termasuk eksperimen yang gagal. Eksperimen yang gagal adalah bahan section Discussion, bukan aib.

**Template entri**

```
### <ID> — <judul>
- Tanggal / PIC:
- Commit / config / seed:
- Dataset & versi:
- Split:
- Pertanyaan yang dijawab:
- Setup:
- Hasil:
- Interpretasi & batasannya:
- Masuk paper di:
```

---

## Daftar eksperimen yang direncanakan (pre-registered)

Direncanakan lebih dulu agar tidak terjadi pemilihan hasil setelah melihat angka.

### Kanal visual

| ID | Pertanyaan | Keluaran yang diharapkan |
|---|---|---|
| **CV-00** | **Berapa galat skala akibat offset bidang, dan pada kondisi apa ia dapat dikendalikan?** | **Tabel galat: elevasi (0/5/10/15 cm) × tinggi kamera (100/150/200 cm) × posisi di bingkai (pusat/tepi). Gerbang untuk DEC-005 — jalankan sebelum pipeline dibangun lebih jauh** |
| CV-01 | Seberapa andal deteksi 4 marker pada variasi pencahayaan dan sudut? | Detection rate per kondisi |
| CV-02 | Seberapa akurat rektifikasi bidang alas? | Reprojection error; galat pengukuran objek planar berukuran diketahui |
| CV-03 | Ambang QC mana yang memisahkan citra layak dan tidak? | Kurva ambang blur/marker/framing vs galat hilir |
| CV-04 | Berapa batas kemiringan kamera sebelum galat melewati toleransi? | Galat terhadap sudut; ambang penolakan yang dipilih |
| CV-05 | Seberapa stabil endpoint berbasis segmentasi? | Variasi antar pengambilan pada objek sama |
| CV-06 | Apakah pose pretrained cukup andal sebagai QC postur pada subjek berbaring? | Rate keypoint valid; false accept/reject postur |
| CV-07 | Berapa MAE estimasi panjang pada objek proksi berukuran diketahui, kondisi ideal? | MAE, MAPE, distribusi galat, n objek |
| CV-08 | Berapa MAE pada kondisi tidak ideal (sudut & jarak bervariasi)? | Tabel MAE per kondisi; **ini bahan utama error analysis** |
| CV-09 | Apakah implementasi HAZ cocok dengan rujukan WHO? | Selisih terhadap kasus rujukan; unit test lulus |
| CV-10 | Berapa latency pipeline visual per citra? | ms per tahap, CPU |
| CV-11 | Bagaimana ambang QC memengaruhi coverage dan galat? | Kurva coverage vs MAE; laporkan **coverage + MAE pada citra yang diterima**, bukan MAE saja |

### Kanal tabular

| ID | Pertanyaan | Keluaran yang diharapkan |
|---|---|---|
| TAB-01 | Apakah kohort sintetis punya karakteristik yang masuk akal? | Distribusi HAZ per usia, prevalensi deteriorasi, pola missing |
| TAB-02 | Fitur lintasan apa yang terbentuk dan seberapa terisi? | Statistik deskriptif per fitur |
| TAB-03 | Apakah split bebas kebocoran? | Verifikasi tidak ada `child_id` lintas split; tidak ada fitur > `t` |
| TAB-04 | Apakah LightGBM mengungguli B0/B1/B2 pada target identik? | Tabel utama paper: metrik × model |
| TAB-05 | Berapa kontribusi blok fitur lintasan dan kontekstual? | Ablasi M1 → M2 → M3 |
| TAB-06 | Bagaimana performa pada anggaran tindak lanjut terbatas? | Precision@K / Recall@K untuk K = 5%, 10%, 20% |
| TAB-07 | Kasus apa yang paling sering salah? | Confusion matrix + karakteristik false negative |
| TAB-08 | Seberapa tahan model terhadap noise pengukuran & missing? | Metrik vs level noise/missing; coverage saat pengukuran terkini tidak tersedia |
| TAB-09 | Apakah atribusi SHAP konsisten dengan mekanisme yang ditanamkan generator? | Ranking fitur; contoh kasus |
| TAB-10 | Berapa latency inferensi per prediksi? | ms, ukuran model |
| TAB-11 | Apakah performa merata antar irisan populasi sintetis? | Metrik per jenis kelamin, kelompok usia, panjang riwayat, tingkat missing, kelompok SES. Dilaporkan sebagai *sensitivity analysis pada simulasi*, bukan bukti fairness |

### Sistem & pengguna

| ID | Pertanyaan | Keluaran |
|---|---|---|
| SYS-01 | Apakah repo bersih bisa di-setup < 10 menit oleh anggota lain? | Waktu setup, hambatan yang ditemukan |
| SYS-02 | Apakah alur end-to-end lolos smoke test? | Log hasil |
| UV-01..04 | Lihat `USER_VALIDATION.md` | |

---

## Log

### CV-09 — Validasi resmi WHO length-for-age
- Tanggal / PIC: 9 Agustus 2026 / Codex, untuk diverifikasi tim
- Commit / config / seed: parent HEAD `30fa13b`; working tree memuat perubahan task ini; tidak memakai seed
- Dataset & versi: WHO `lenanthro.sas7bdat`, 1.462 baris recumbent usia 0–730 hari
- Split: tidak berlaku
- Pertanyaan yang dijawab: apakah implementasi HAZ cocok dengan rujukan resmi independen?
- Setup: LMS dari paket SAS resmi WHO; 18 kasus dari simplified field tables WHO yang terpisah
- Hasil: 18/18 kasus lulus; selisih absolut maksimum 0,0256 HAZ pada toleransi 0,05
- Interpretasi & batasannya: toleransi mencakup pembulatan panjang 0,1 cm pada tabel lapangan; provenance dan checksum ada di `data/who/provenance.json`
- Masuk paper di: §3.3 / bukti CV-09

### TAB-FINAL-01 — Final multi-seed tabular evaluation
- Tanggal / PIC: 9 Agustus 2026 / Codex, untuk diverifikasi tim
- Commit / config / seed: parent HEAD `30fa13b`; working tree memuat perubahan task ini; `configs/exp_tabular_final.json`; seed 42, 314, 1618, 2026, 2718
- Dataset & versi: `posyandu_synth_v1`; 1.200 anak per seed; 22.779–22.983 kunjungan per seed
- Split: grouped child holdout + temporal holdout dengan label-maturity purge; satu index visit per anak
- Pertanyaan yang dijawab: TAB-01–07, TAB-09, TAB-11; kontribusi trajectory M2 terhadap M1
- Setup: B0/B1/B2/M1/M2/M3, exact-K 5/10/20%, M2 dipra-spesifikasikan sebagai primary
- Hasil grouped: M2 AUPRC 0,2735 ± 0,0947; Recall@20% 0,4821 ± 0,0994; M2−M1 +0,0444 ± 0,0716 AUPRC dan +0,0697 ± 0,0774 Recall@20%
- Hasil temporal: M2 AUPRC 0,2976 ± 0,0311; Recall@20% 0,4358 ± 0,0345; M2−M1 +0,0739 ± 0,0281 AUPRC dan +0,0821 ± 0,0680 Recall@20%
- Interpretasi & batasannya: trajectory memberi sinyal tambahan rata-rata pada kedua protokol dalam simulasi terkontrol, dengan variasi antarseed; bukan validasi klinis atau bukti dampak kesehatan nyata
- Artefak: `results/tabular/final/`; ringkasan `docs/FINAL_TABULAR_RESULTS.md`
- Masuk paper di: §4.2–§4.4 / TAB-01–07, TAB-09, TAB-11

### TAB-08 — Robustness terhadap noise dan missing pengukuran
- Tanggal / PIC: 10 Agustus 2026 / Codex, untuk diverifikasi tim
- Commit / config / seed: parent HEAD `e0f5902`; working tree memuat perubahan closure; `configs/exp_tabular_final.json`; seluruh lima seed final
- Dataset & versi: `posyandu_synth_v1`; model M2 per seed/protokol dibekukan dari training tanpa perturbasi
- Split: grouped + temporal yang sama dengan `TAB-FINAL-01`; satu index visit per anak
- Pertanyaan yang dijawab: bagaimana metrik M2 berubah saat informasi longitudinal yang sudah tersedia diberi tambahan noise panjang 0,5/1/2 cm, tambahan missing 10/20/30%, atau pengukuran terkini dibuat tidak tersedia?
- Setup: perturbasi hanya pada kunjungan `<= prediction_date`; future target dan label tidak disentuh; HAZ WHO dan seluruh fitur dependen dihitung ulang; seed perturbasi deterministik
- Hasil grouped: baseline AUPRC 0,2735 ± 0,0947; sigma 2 cm 0,1536 ± 0,0432; missing +30% 0,2447 ± 0,0696; current missing 0,1465 ± 0,0363
- Hasil temporal: baseline AUPRC 0,2976 ± 0,0311; sigma 2 cm 0,1860 ± 0,0139; missing +30% 0,2477 ± 0,0366; current missing 0,2017 ± 0,0293
- Coverage: 1,0000 pada seluruh skenario karena LightGBM tetap dapat memberi skor ketika fitur antropometri kosong; ini bukan berarti kualitas ranking tidak turun
- Interpretasi & batasannya: noise besar dan hilangnya pengukuran terkini menurunkan ranking paling konsisten; hasil grouped dapat non-monotonik karena test hanya 240 anak/seed dan satu perturbasi deterministik per seed. Ini sensitivitas simulasi, bukan robustness klinis. Pengukuran manual valid bukan `current_measurement_missing`. Berlawanan dengan konteks task, schema frozen memang memuat `measured_by_cv_t`; karena itu tidak dibuat klaim bahwa skor invariant terhadap flag sumber.
- Artefak: `results/tabular/final/tab08_robustness_per_seed.csv`, `tab08_robustness_aggregate.csv`

### TAB-10 — Latency dan ukuran model M2
- Tanggal / PIC: 10 Agustus 2026 / Codex, untuk diverifikasi tim
- Commit / config / seed: parent HEAD `e0f5902`; working tree dirty tercatat; artefak primary grouped seed 42
- Environment: WSL2 Linux x86_64, Intel Core Ultra 7 155H, 22 logical CPU, Python 3.12.3, LightGBM 4.7.0
- Setup: `time.perf_counter_ns`; warm prediction tanpa CSV I/O/interpreter startup; 100 load repetitions dan 200 prediction repetitions
- Hasil: model 14.150 byte (0,01349 MiB); load median/p95 7,637/12,572 ms; single-row 1,143/1,562 ms; batch-10 1,122/1,601 ms; batch-100 1,159/1,824 ms; batch-240 0,918/1,398 ms; score + exact Top-20% batch-240 0,959/1,484 ms
- Interpretasi & batasannya: angka hanya berlaku untuk environment yang direkam; bukan klaim Raspberry Pi, ponsel, atau deployment produksi
- Artefak: `results/tabular/final/tab10_latency.csv`, `tab10_latency_environment.json`

### TAB-12 — Audit sensitivitas tie pada batas Top-K
- Tanggal / PIC: 10 Agustus 2026 / Codex, untuk diverifikasi tim
- Commit / config / seed: parent HEAD `e0f5902`; seluruh lima seed final; grouped + temporal; K 5/10/20%
- Setup: skor frozen M2 dan anak evaluasi identik dengan `TAB-FINAL-01`; batas min/max dihitung eksak hanya dengan memvariasikan anggota dari grup skor cutoff
- Hasil: 30/30 kombinasi tersedia. Mean/max ukuran grup cutoff adalah 5,2/20, 5,0/12, 6,4/28 untuk grouped K 5/10/20%, dan 11,0/47, 16,4/54, 23,6/65 untuk temporal.
- Worst case: grouped seed 42 K=5% memiliki observed Recall 0,1154 dengan batas eksak 0,0000–0,1538; grouped seed 42 K=20% 0,3462 dengan batas 0,3077–0,4231; temporal seed 2026 K=10% 0,2357 dengan batas 0,2000–0,3286.
- Interpretasi & batasannya: jumlah anak terpilih tetap exact K dan production tie-break `child_id` tidak berubah, tetapi membership dan Recall@K dapat material sensitif saat grup cutoff besar
- Artefak: `results/tabular/final/tab12_tie_sensitivity.csv`, `tab12_tie_sensitivity_summary.csv`

### TAB-REPRO-01 — Regenerasi final dari source worktree bersih
- Tanggal / PIC: 10 Agustus 2026 / Codex
- Commit: detached worktree `e0f5902ec68b0b90f3f5ddbb227259705c892556`, `git_dirty=false`
- Setup: canonical `TAB-FINAL-01` dijalankan ke direktori `/tmp`, tidak menimpa artefak committed
- Hasil: dataset summary, per-seed/aggregate metrics, ablation deltas, representative cases/error counts, global SHAP, persistence predictions, dan WHO output semuanya byte-identical terhadap artefak committed (11/11 CSV + WHO JSON)
- Interpretasi & batasannya: ini memverifikasi reproduksibilitas tabular pada environment dependency yang sama, bukan setup seluruh aplikasi atau platform lain
- Artefak: `results/tabular/final/tab13_reproducibility.json`
