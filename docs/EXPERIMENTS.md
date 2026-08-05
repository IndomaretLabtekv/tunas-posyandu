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
| TAB-08 | Seberapa tahan model terhadap noise pengukuran & missing? | Metrik vs level noise; metrik saat kanal visual tidak tersedia |
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

> Kosong. Entri pertama diisi saat CV-00 benar-benar dijalankan.
>
> Jangan menyalin contoh berisi angka. Angka placeholder di dokumen ini adalah cara paling mudah membuat paper berisi hasil yang tidak pernah terjadi.
