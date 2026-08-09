# DECISIONS — Catatan Keputusan Teknis

Format: satu keputusan per entri, berisi konteks, keputusan, alasan, dan konsekuensinya terhadap paper.
Dokumen ini juga berfungsi sebagai bahan mentah untuk pembahasan *trade-off* di section Methodology dan Discussion — kriteria "Technical depth and justification" secara eksplisit meminta pembahasan trade-off, bukan sekadar pilihan akhir.

---

## DEC-001 — Target model bersifat prospektif, bukan turunan HAZ saat ini

**Konteks.** Rancangan awal mengklasifikasikan risiko rendah/sedang/tinggi. Jika label itu diturunkan dari aturan ambang HAZ sementara HAZ juga menjadi fitur input, model hanya menghafal aturan yang sudah diketahui. Akurasi akan mendekati sempurna dan tidak bermakna.

**Keputusan.** Target adalah kejadian **deteriorasi pertumbuhan pada horizon ke depan** (misal 3–6 bulan), dihitung dari kunjungan setelah waktu prediksi `t`. Seluruh fitur hanya boleh berasal dari data ≤ `t`.

**Alasan.** Menjadikan tugas model non-trivial, membenarkan penggunaan ML, membenarkan fitur lintasan, dan membuat SHAP punya makna. Ini juga tugas yang benar-benar dihadapi petugas gizi: menentukan siapa yang *akan* memburuk, bukan mengulang klasifikasi yang sudah terbaca dari tabel WHO.

**Konsekuensi.** Definisi horizon dan ambang deteriorasi harus dinyatakan sebagai **ambang operasional prototipe**, bukan standar klinis, sampai dikalibrasi bersama ahli gizi.

---

## DEC-002 — Baseline harus memprediksi endpoint yang sama
> ⚠️ **Bentuk B0 dan B1 di-*supersede* oleh DEC-012** (skor ranking kontinu). Tabel di bawah sudah diperbarui; prinsipnya tidak berubah.

**Konteks.** Membandingkan model prospektif dengan aturan `HAZ < −2` tidak adil: aturan itu mendeteksi kondisi sekarang, model memprediksi masa depan.

**Keputusan.** Semua pembanding dievaluasi pada target dan split yang identik:

| ID | Model | Input | Target |
|---|---|---|---|
| B0 | Ranking `−HAZ_t` (DEC-012) | snapshot | deteriorasi horizon |
| B1 | Ranking `w₁·(−HAZ_t) + w₂·(−slope_HAZ)` (DEC-012) | snapshot + slope | deteriorasi horizon |
| B2 | Logistic regression | snapshot | deteriorasi horizon |
| M1 | LightGBM snapshot | snapshot | deteriorasi horizon |
| M2 | LightGBM + lintasan | snapshot + trajectory | deteriorasi horizon |
| M3 | LightGBM + lintasan + kontekstual | seluruh fitur | deteriorasi horizon |

**Alasan.** B0 merepresentasikan praktik eksisting (prioritas berdasarkan HAZ terkini) — inilah "before" dalam narasi *before → after*. Selisih M2/M3 terhadap B0 adalah nilai tambah produk yang bisa dikuantifikasi. Selisih M2 terhadap M1 adalah bukti langsung untuk klaim kebaruan "lintasan pertumbuhan multi-waktu".

---

## DEC-003 — Split berbasis `child_id` dan waktu

**Konteks.** Satu anak menyumbang banyak baris kunjungan. Random split per baris akan menempatkan kunjungan anak yang sama di train dan test, sehingga model mengenali individu dan metrik menjadi terlalu optimistis.

**Keputusan.**
- Seluruh baris satu `child_id` berada pada split yang sama (grouped split).
- Fitur pada waktu `t` hanya memakai data ≤ `t`; label dari kunjungan setelah `t`.
- Test set tambahan berupa **temporal holdout**: periode terakhir kohort.
- Yang dicatat per eksperimen: random seed, daftar `child_id` per split, versi dataset, commit hash, hyperparameter, tanggal.

**Alasan.** Tanpa ini, seluruh angka di section Results tidak bisa dipertahankan saat ditanya juri.

---

## DEC-004 — "Rektifikasi perspektif + geometry QC", bukan "koreksi parallax"

**Konteks.** Homografi memetakan satu bidang planar ke bidang planar lain. Marker ArUco berada pada bidang alas; bagian tubuh yang tidak tepat pada bidang tersebut tidak otomatis terkoreksi. Estimasi pose kamera yang sebenarnya membutuhkan parameter intrinsik dan koefisien distorsi, bukan hanya empat sudut marker.

**Keputusan.** MVP **mengontrol** parallax, tidak mengklaim menyelesaikannya:

1. Deteksi seluruh marker; tolak jika tidak lengkap.
2. Hitung homografi bidang alas.
3. Estimasi kemiringan kamera / reprojection error; **tolak citra yang terlalu miring**.
4. Panduan pengambilan citra pada UI agar kamera mendekati tegak lurus bidang alas dan jarak sesuai protokol.
5. Ukur galat pada kondisi tangkap ideal **dan** tidak ideal; laporkan keduanya.

Penamaan di paper: *ArUco-based perspective rectification and geometry-aware image quality control*.

**Alasan.** Bisa diselesaikan dalam waktu tersedia, dapat diuji, dan tidak overclaim. Melaporkan galat sisa akibat offset bidang tubuh justru menjadi nilai pada kriteria "Reliability and error analysis".

**Ditolak untuk MVP.** Koreksi analitik berbasis tinggi kamera dan tebal tubuh, marker sekunder pada bidang setinggi tubuh, dan depth estimation — semuanya masuk Future Work dengan penjelasan singkat.

---

## DEC-005 — Satu protokol pengukuran: panjang badan telentang (recumbent), alas ber-marker, kamera dari atas

**Konteks.** Mendukung sekaligus panjang telentang (<24 bulan) dan tinggi berdiri (≥24 bulan) praktis berarti membangun dua sistem CV: pose, penempatan marker, sudut kamera, QC, dan failure case berbeda.

**Keputusan.** MVP hanya mendukung **panjang badan telentang** di atas alas ber-marker dengan kamera dari atas. Mode berdiri masuk Future Work.

**Status: BERSYARAT.** Keputusan ini berlaku hanya jika CV-00 (plane-offset stress test, lihat DEC-011) menunjukkan galat skala yang dapat dikendalikan lewat protokol. Jika tidak, jalankan salah satu opsi mitigasi di DEC-011 sebelum melanjutkan pembangunan pipeline.

**Koreksi atas alasan sebelumnya.** Pernyataan bahwa sisa galat "hanya setebal tubuh" menyesatkan. Untuk kamera pada ketinggian H dan titik yang diukur berada z di atas bidang alas, perbedaan skalanya kira-kira H/(H−z): kamera 100 cm dengan z = 10 cm sudah menghasilkan selisih ~11%, yang pada panjang 70 cm berarti beberapa sentimeter. Mode telentang **tidak menyelesaikan parallax**; keunggulannya adalah z-nya kecil, konsisten, dan dapat dikontrol lewat protokol — bukan nol.

Satu penajaman yang perlu diperhatikan saat merancang CV-00: yang menentukan galat bukan ketebalan tubuh secara keseluruhan, melainkan **elevasi titik yang benar-benar diukur**. Tumit menyentuh alas (z ≈ 0), sedangkan tepi siluet kepala berada pada sekitar setengah tinggi kepala. Karena itu objek uji harus menyertakan bentuk membulat pada elevasi diketahui, bukan hanya pelat datar. Posisi objek dalam bingkai juga berpengaruh — parallax paling kecil di pusat bingkai dan membesar ke tepi.

**Alasan memilih telentang — berbeda dari saran umum "pilih mode berdiri karena pretrained pose lebih siap":**

1. **Geometri lebih terkendali.** Pada mode telentang, offset bidang (z) kecil dan relatif konstan antar pengambilan. Pada mode berdiri, marker harus berada di latar vertikal sementara subjek berdiri di depannya — z lebih besar, lebih bervariasi antar anak, dan tinggi kamera menjadi variabel bebas tambahan. Keduanya menghadapi parallax; yang telentang lebih mudah dibatasi lewat protokol.
2. **Latar terkontrol.** Alas ukur berwarna seragam membuat segmentasi subjek dapat diandalkan tanpa model yang dilatih khusus. Ini yang memungkinkan V4 (ekstraksi endpoint) berjalan tanpa keypoint puncak kepala/tumit yang memang tidak tersedia di model pose pretrained.
3. **Selaras dengan narasi dampak.** Urgensi paper bertumpu pada 1.000 hari pertama kehidupan, dan periode itu justru berada pada rentang usia yang diukur telentang. Memilih mode berdiri akan mempersempit cakupan MVP ke 24–59 bulan dan melemahkan hubungan antara produk dan urgensi yang dibangun di Pendahuluan.
4. **Sesuai standar.** WHO memang membedakan recumbent length untuk anak di bawah 24 bulan dan standing height untuk usia di atasnya; membatasi satu mode adalah pembatasan yang eksplisit dan dapat dipertahankan, bukan kelalaian.

**Risiko yang diterima.** Model pose pretrained kurang andal pada subjek berbaring dilihat dari atas. Karena itu pose **tidak** dipakai sebagai sumber ukuran, hanya sebagai QC postur, dan kegagalan pose menurunkan skor kepercayaan alih-alih menggagalkan pengukuran.

**Konsekuensi untuk paper.** Section Methodology harus menyatakan cakupan versi semifinal (usia 0–23 bulan, protokol telentang) secara eksplisit, dan Limitations menyebut mode berdiri sebagai pekerjaan lanjutan.

---

## DEC-006 — Endpoint tubuh dari segmentasi, pose hanya untuk QC postur

**Konteks.** Model pose pretrained (keluarga COCO 17-keypoint) menyediakan hidung, mata, telinga, bahu, siku, pergelangan tangan, panggul, lutut, dan pergelangan kaki — **tidak** ada puncak kepala (vertex) maupun ujung tumit. "Ekstrapolasi vertex dan tumit" adalah heuristik, bukan keluaran model.

**Keputusan.**
- Panjang badan dihitung dari titik ekstrem siluet subjek sepanjang sumbu tubuh pada citra yang sudah diregistrasi, bukan dari keypoint.
- **Pose bersifat opsional dan hanya masuk produk jika lolos CV-06.** Model pose pretrained dilatih pada subjek tegak; pada subjek telentang dilihat dari atas, pada boneka, pada tungkai berdekatan, dan pada tubuh tertutup pakaian, keandalannya belum tentu memadai. Jika CV-06 buruk, pose dipindahkan ke Future Work tanpa merusak pipeline utama.
- **QC postur yang tidak bergantung pose (wajib, jalur utama):** rasio panjang–lebar siluet, kelengkungan sumbu siluet, deviasi sumbu tubuh, deteksi geometris tungkai tertekuk atau terpisah, dan confidence segmentasi.
- Confidence rendah → estimasi ditandai, bukan disembunyikan.

Menambahkan model hanya agar pipeline terlihat kompleks adalah kesalahan yang dinilai negatif: rubrik meminta *correctness of AI approach*, yaitu metode yang tepat dan dapat dijustifikasi, bukan jumlah model terbanyak.

**Evaluasi terpisah yang harus dilaporkan.** Galat endpoint kepala, galat endpoint kaki, galat panjang total, dan failure rate saat postur tidak lurus atau ada oklusi.

---

## DEC-007 — Data sintetis dilaporkan sebagai bukti kelayakan teknis, bukan validitas klinis

**Konteks.** Penggunaan data sintetis diperbolehkan. Risikonya: jika generator menanamkan aturan risiko dan model diberi fitur yang sama, model hanya merekonstruksi aturan generator. F1 tinggi tidak membuktikan apa pun tentang balita nyata.

**Keputusan.**
- Proses pembangkitan didokumentasikan penuh di `DATA_CARD.md`, termasuk mekanisme yang menghasilkan deteriorasi.
- Generator memasukkan noise pengukuran, missing values, kunjungan tidak teratur, dan ketidakseimbangan kelas agar tugas tidak deterministik.
- Bahasa pelaporan dikunci: *"Pada kohort longitudinal sintetis, model merekonstruksi pola risiko yang ditanamkan dalam simulasi. Eksperimen ini memvalidasi kelayakan teknis pipeline, bukan validitas klinis pada populasi balita nyata."*
- Dilarang menulis kalimat berbentuk *"Model mencapai F1 X% dalam memprediksi deteriorasi pertumbuhan balita."*

**Yang sah dibuktikan dengan data sintetis.** Pipeline end-to-end berjalan, penanganan missing values, ketahanan terhadap noise, perbandingan antar model, ablasi lintasan, tampilan SHAP dan dashboard.

---

## DEC-008 — Thin vertical slice sebelum modul apa pun matang

**Konteks.** Menunda integrasi sampai modul selesai adalah cara paling umum kehilangan deliverable di hari terakhir.

**Keputusan.** Sebelum eksperimen berat dimulai, jalur `unggah citra → backend → HAZ placeholder → skor risiko placeholder → dashboard` harus sudah hidup. Placeholder diganti satu per satu: geometri dummy → pipeline ArUco; HAZ dummy → perhitungan LMS WHO; risiko dummy → LightGBM; penjelasan dummy → SHAP.

**Alasan.** Setiap penggantian adalah perubahan kecil yang bisa langsung diuji, dan produk berada dalam kondisi dapat didemokan sejak hari pertama.

---

## DEC-009 — Verifikasi implementasi HAZ terhadap keluaran referensi WHO

**Keputusan.** Perhitungan Z-score diuji terhadap sejumlah kasus rujukan resmi WHO (termasuk kasus batas dan kasus dengan Z-score ekstrem), bukan hanya diperiksa "rumusnya terlihat benar". Hasil verifikasi disimpan sebagai unit test.

**Alasan.** Seluruh keluaran produk bergantung pada langkah ini. Galat di sini akan diam-diam merusak setiap angka di paper.

---

## DEC-010 — Definisi target dikunci (satu horizon, satu ambang, satu aturan missing)

**Konteks.** Menyisakan "3–6 bulan" dan "ambang contoh" berarti tiga anggota tim dapat menghasilkan label yang berbeda dari data yang sama.

**Keputusan (kunci malam ini, jangan diubah setelah TAB-01 jalan).**

> **Deteriorasi** terjadi bila pada kunjungan tindak lanjut dalam jendela **3 bulan (± 6 minggu)** setelah `t`, anak mengalami **penurunan HAZ ≥ 0,5 SD** dibanding `t`, **atau** melintasi ambang HAZ −2 ke arah lebih buruk.

Aturan kasus tepi — wajib diikuti seragam:

| Kasus | Perlakuan |
|---|---|
| Tidak ada kunjungan dalam jendela | Baris dibuang dari train/test (dicatat jumlahnya, dilaporkan di paper) |
| Lebih dari satu kunjungan dalam jendela | Pakai yang terdekat ke titik 3 bulan |
| Hanya ada kunjungan di luar jendela | Dibuang; jangan ekstrapolasi |
| Anak melewati batas usia MVP di dalam jendela | Baris dibuang |
| Anak sudah severely stunted (HAZ < −3) pada `t` | Tetap disertakan; kriteria penurunan ≥ 0,5 SD tetap berlaku, dan kasus ini dilaporkan terpisah di error analysis |
| Follow-up ada tapi kolom panjang badan kosong | Dibuang |

Penamaan di paper: **operational deterioration threshold** untuk prototipe, bukan ambang klinis. Kalibrasi bersama ahli gizi masuk Future Work.

---

## DEC-011 — CV-00 plane-offset stress test sebagai gerbang kanal visual

**Konteks.** Seluruh arsitektur kanal visual bergantung pada asumsi bahwa galat akibat offset bidang dapat dikendalikan. Asumsi itu belum diuji, dan mengetahuinya di CV-07 sudah terlambat.

**Keputusan.** CV-00 dijalankan **sebelum** pipeline CV dibangun lebih jauh. Matriks uji: ketebalan/elevasi objek 0, 5, 10, 15 cm × tinggi kamera 100, 150, 200 cm × posisi objek di pusat dan tepi bingkai, dengan kamera mendekati tegak lurus.

**Aturan keputusan setelah hasil keluar** — pilih satu dan catat di sini:

1. Tetapkan tinggi kamera minimum yang aman dan jadikan bagian protokol serta QC.
2. Tambahkan reference bar pada elevasi mendekati titik ukur.
3. Terapkan koreksi empiris dan nyatakan batasannya secara eksplisit.
4. Turunkan status keluaran visual menjadi estimasi awal yang wajib dikonfirmasi manual.

Opsi 4 tetap merupakan produk yang sah dan jujur; ia mengurangi klaim, bukan menghapus nilai.

---

## DEC-012 — Baseline B0 dan B1 berbentuk skor ranking, bukan aturan biner

**Konteks.** Produk menghasilkan **urutan prioritas** dan dievaluasi dengan Precision@K/Recall@K. Aturan biner `HAZ < −2` tidak dapat mengurutkan, sehingga tidak dapat dibandingkan pada metrik @K.

**Keputusan.**

| ID | Bentuk | Keterangan |
|---|---|---|
| B0 | `priority_score = −HAZ_t` | Representasi praktik eksisting: makin rendah HAZ terkini, makin tinggi prioritas |
| B1 | `priority_score = w₁·(−HAZ_t) + w₂·(−slope_HAZ)` | Bobot ditentukan pada **validation split**, bukan test |
| B2 | Probabilitas dari logistic regression | |

Aturan biner `HAZ_t < −2` tetap dipakai sebagai pembanding pada metrik klasifikasi (precision/recall/F1), tetapi bukan satu-satunya baseline ranking.

---

## DEC-013 — Dataset kedua untuk klaim segmentasi & QC postur

**Konteks.** `proxy_objects_v1` (objek kaku) hanya dapat membuktikan geometri dan konversi ukuran. Ia tidak dapat membuktikan segmentasi bentuk tubuh, endpoint kepala/kaki, postur telentang, tungkai tertekuk, atau oklusi — padahal klaim itu ada di `CLAIMS_MATRIX.md`.

**Keputusan.** Tambahkan `proxy_subjects_v1` (boneka seukuran bayi, manekin, dan anggota tim berbaring untuk uji postur & segmentasi; variasi pakaian, posisi kaki, oklusi, pencahayaan). Klaim dipisah tegas:

| Dataset | Membuktikan |
|---|---|
| `proxy_objects_v1` | Akurasi geometri & konversi ukuran |
| `proxy_subjects_v1` | Segmentasi, endpoint, QC postur, failure case |

Keduanya tetap bukan pengganti validasi pada balita nyata. Jika `proxy_subjects_v1` tidak sempat dikumpulkan, **klaim segmentasi dan QC postur dihapus dari paper**, bukan dibiarkan tanpa bukti.

---

## DEC-014 — Segmentasi subjek: model (BiRefNet_dynamic) sebagai jalur utama, baseline warna tetap ada

**Konteks.** DEC-006 menetapkan endpoint dari segmentasi (bukan keypoint pose) tanpa memutuskan metode segmentasinya; asumsi awalnya threshold warna pada alas seragam. Evaluasi lapangan yang lebih luas (pakaian, cahaya, posisi) membuat segmentasi berbasis model lebih andal.

**Keputusan.**
- **Jalur utama:** BiRefNet_dynamic (`ZhengPeng7/BiRefNet_dynamic`, resolusi dinamis 256–2304) via transformers, lazy-load, backend default di `cv/segment.py`.
- **Baseline non-AI (wajib tetap ada):** ColorSegmenter — subjek = komponen terbesar "bukan alas" di dalam region alas. Dipakai sebagai fallback saat model tidak tersedia dan sebagai pembanding eksperimen CV-05/CV-07/CV-08.
- **Posture QC:** ViTPose (`nielsr/vitpose_base`) sebagai model pose opsional gated CV-06, menggantikan "pose pretrained generik" pada DEC-006. Tetap hanya menurunkan confidence, tidak pernah menjadi sumber angka ukur.
- Registry backend dibuat extensible (YOLO26n-seg / SAM 3 bisa ditambah; SAM 3 butuh Python 3.12 + GPU + akses checkpoint gated — Future Work).

**Alasan.** Segmentasi adalah satu-satunya titik yang benar-benar butuh "pengertian visual"; bagian skala/geometri tetap deterministik. Mempertahankan baseline non-AI menjaga produk tetap jalan tanpa model dan memberi bahan perbandingan yang jujur.

**Konsekuensi.** CLAIMS C-A5 (endpoint berbasis segmentasi) kini didukung jalur model + baseline. Video boleh menyebut "AI" pada segmentasi bila BiRefNet yang dipakai (VIDEO_SCRIPT.md catatan segmen C). Data evaluasi `proxy_subjects_v1` tetap syarat klaim segmentasi (DEC-013).

---

## DEC-015 — Referensi skala tanpa marker: alas polos berukuran diketahui

**Konteks.** Marker ArUco di sudut alas adalah friction bagi kader (harus dicetak/ditempel dengan presisi) dan "penanda" yang ingin dihindari pengguna. Keputusan tim: MVP memakai alas polos warna seragam berukuran fisik diketahui (mis. 60×100 cm) sebagai referensi skala — pengguna cukup membaringkan anak dan menjepret.

**Keputusan.**
1. Deteksi referensi skala baru (`cv/mat_corners.py`): clustering warna (k-means) → kandidat segiempat cembung terbesar yang **tidak menyentuh tepi bingkai** → refinement sudut subpiksel → pengurutan konsisten (TL, TR, BR, BL) → homografi identik dengan mode marker. Kontrak keluaran sama (`DetectionResult`), sehingga seluruh modul hilir tidak berubah.
2. `cv/pipeline.py` default ke `detect_mat_corners`; mode marker ArUco tetap tersedia via argumen `detector` sebagai comparator/fallback.
3. Warna alas = spesifikasi produk (dicetak seragam), diteruskan ke ColorSegmenter via `mat_color`.
4. Runner `cv/evaluate.py` (CV-00) tetap mode marker untuk sesi fisik yang sudah dirancang; runner mode alas polos menyusul.

**Alasan.** Tanpa referensi skala di foto, pengukuran absolut tidak mungkin secara matematis (scale ambiguity: `S/d = s/f`); multi-frame VIO (ARCore/ARKit) bisa menghilangkan referensi fisik tetapi butuh gerakan kamera, perangkat terkalibrasi, dan SDK native — tidak cocok dengan alur "jepret sekali" dan scope web app (Future Work, lihat bawah). Alas polos adalah kompromi: friction minimal (cetak sekali, tanpa presisi penempatan marker) dengan matematika identik.

**Trade-off yang diterima (dilaporkan jujur di paper).** Deteksi sudut polos kurang robust daripada fidusial ber-ID: rawan cahaya, alas kusut, warna lantai mirip, dan tidak ada ID untuk verifikasi korespondensi sudut. Dikompensasi: syarat cembung + margin bingkai, subpixel refinement, QC framing/tilt di hilir, dan penolakan (bukan angka salah) saat gagal. Detection rate ekspektasi lebih rendah dari ArUco — diukur di CV-01/CV-02.

**Konsekuensi.** CLAIMS C-A1, SCOPE V1/V3, MODEL_CARD disinkronkan. Paper §3.3 menyebut "deteksi 4 sudut alas polos berukuran diketahui". Future Work: (a) multi-frame VIO tanpa referensi fisik — butuh gerakan kamera, daftar device terkalibrasi, dan app native/WebXR (iOS Safari tidak mendukung WebXR); (b) deteksi sudut berbasis deep learning jika robustness alas polos tidak mencukupi.

---

## DEC-0xx — (template)

**Konteks.**
**Keputusan.**
**Alasan.**
**Konsekuensi.**
