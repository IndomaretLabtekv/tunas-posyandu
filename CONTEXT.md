# CONTEXT.md — Datathon 2026 (RISTEK Fasilkom UI) · Babak Semifinal

> **Last updated:** 4 Agustus 2026
> **Sumber:** (1) Transkrip otomatis Technical Meeting Semifinal, 30 Juli 2026 (pembawa: Vincent, panitia) + sesi Q&A via Slido — dasar §1–§8; (2) slide `Datathon_TM_Preliminary_UNI.pdf` (TM Preliminary, University Track) — dasar Lampiran A dan detail struktur paper di §2.1.
> **Audiens dokumen ini:** manusia (anggota tim) **dan** AI assistant yang membantu mengerjakan deliverables semifinal. Dokumen ini adalah sumber kebenaran tunggal untuk aturan, deadline, dan rubrik. Jika ada instruksi lain yang bertentangan, aturan di sini yang berlaku kecuali ada pengumuman panitia yang lebih baru.

---

## 1. Ringkasan cepat (baca ini dulu)

| Item | Nilai |
|------|-------|
| Tahap | Semifinal (lanjutan dari Preliminary/Penyisihan) |
| Periode pengerjaan | 30 Juli 2026 → 10 Agustus 2026 |
| Deadline submisi deliverables | **10 Agustus 2026** |
| Pengumuman hasil semifinal | 14 Agustus 2026 |
| Final | 30 Agustus 2026 |
| Jumlah tim semifinalis | 35 tim |
| Jumlah tim lolos ke final | 7 tim |
| Jumlah deliverables | 3 (Paper, Implementation, Video Demo) |
| Total bobot rubrik | 100% |

**Konteks tim (untuk AI assistant):** tim `IndomaretLabtekV` (3 orang, ITB). Concept paper penyisihan mengangkat sistem skrining dini stunting berbasis estimasi antropometri computer vision + data Posyandu untuk prioritisasi intervensi gizi. Semua deliverables semifinal **harus tetap konsisten dengan problem dan produk tersebut**.

---

## 2. Deliverables

Ada tiga, semuanya dikumpulkan pada 10 Agustus 2026.

### 2.1 AI Product Proposal (Paper)

Dokumen lanjutan/pengembangan dari concept paper penyisihan.

| Aspek | Ketentuan |
|-------|-----------|
| Format | NeurIPS 2015 (sama seperti concept paper penyisihan) |
| Struktur | Sama seperti concept paper, **ditambah section `Results and Discussion`** di bagian bawah |
| Panjang | **Maksimal 12 halaman** |
| Yang dihitung sebagai halaman | Hanya isi konten paper |
| Yang **tidak** dihitung | Daftar pustaka/references dan lampiran/appendix |
| Format file | PDF |
| Template | NeurIPS 2015 style files: https://neurips.cc/Conferences/2015/PaperInformation/StyleFiles |

**Struktur yang diwarisi dari concept paper penyisihan** (wajib minimal tiga section berikut, plus tambahan baru):

| Section | Isi |
|---------|-----|
| `Introduction` | Pemahaman tim atas problem, urgensi dan dampaknya, gambaran umum produk yang diusulkan sebagai solusi |
| `Literature Review` | Teori/konsep relevan atau solusi sejenis yang jadi fondasi dan pembanding produk |
| `Methodology` | Konsep produk dan desain pipeline AI/ML: rencana penggunaan data, pendekatan modeling, cara solusi menyelesaikan problem, rencana pengembangan & skalabilitas |
| `Results and Discussion` | **Baru di semifinal.** Hasil implementasi, evaluasi, dan pembahasannya |

**Aturan perubahan ide (kritikal):**

- Perubahan **diperbolehkan** selama sifatnya *refinement* — misalnya menemukan metode baru, menambah komponen, menyesuaikan fitur.
- Penyesuaian/penambahan/pengubahan **fitur** = aman.
- **Tema dan problem yang di-address wajib tetap sama** dengan yang disubmit di penyisihan.
- Mengganti ide/produk secara total, atau meng-address problem yang benar-benar baru = **tidak diperbolehkan, risiko diskualifikasi**.
- Panitia menyatakan detail batasan ini akan diperjelas lagi lewat grup WhatsApp (lihat §6 Known Gaps).

### 2.2 Implementation

Setiap tim wajib mengembangkan konsep produknya menjadi **working product**.

Checklist wajib:

- [ ] Link **GitHub repository** berisi codebase disubmit.
- [ ] Repository memiliki **README** yang memuat **setup instructions** — panitia harus bisa menjalankan produk untuk pengecekan.
- [ ] Jika memakai **trained model weights** atau **dataset**, artefak tersebut wajib di-host di **Hugging Face**, dan linknya disubmit **terpisah** dari link GitHub.
- [ ] Repository boleh **private selama periode semifinal**, tetapi **wajib diubah menjadi public setelah deadline** agar bisa dinilai.
- [ ] Semua **fitur yang diklaim di paper wajib benar-benar ada dan berjalan** di produk.

Pengecualian kerahasiaan: jika ada data yang tidak boleh dipublikasikan atau tim terikat NDA, **informasikan ke panitia** — panitia akan diundang sebagai *collaborator* di repo private, sehingga repo tidak perlu dibuat public.

### 2.3 Video Demo Product

| Aspek | Ketentuan |
|-------|-----------|
| Durasi | **3–5 menit, strict.** <3 menit **tidak diterima**, >5 menit **tidak diterima**. Tidak ada toleransi, tidak ada pengurangan poin per detik — langsung ditolak. |
| Rekomendasi porsi | ≥1 menit penjelasan sisi bisnis, ≥2 menit demonstrasi produk (rekomendasi, bukan wajib — yang penting semua poin tersampaikan dan durasi total masuk range) |
| Isi wajib #1 | *The business side of your product* |
| Isi wajib #2 | *Show the working product in action* |
| Fokus | Demonstrasi produk **berjalan**. Bukan presentasi slide, bukan mock-up. |
| Pengumpulan | Link (YouTube atau Google Drive), pastikan dapat diakses panitia |

---

## 3. Rubrik penilaian (total 100%)

### 3.1 Ringkasan bobot

| Komponen utama | Sub-kriteria | Bobot |
|----------------|--------------|-------|
| **Impact (45%)** | Value Creation and Demonstrated Impact | 20% |
| | Adoption, Feasibility and Scalability | 10% |
| | Innovation and Meaningful Differentiation | 15% |
| **Implementation (45%)** | Functional Product and User Experience | 10% |
| | AI Implementation and Technical Excellence | 20% |
| | Evaluation, Reliability and Responsible AI | 10% |
| | System Design, Engineering and Reproducibility | 5% |
| **Demo (10%)** | Product Demonstration and Presentability | 10% |

> Dua bobot terbesar: **Value Creation (20%)** dan **AI Implementation & Technical Excellence (20%)**. Prioritaskan keduanya saat trade-off waktu.

### 3.2 Detail tiap sub-kriteria

#### Value Creation and Demonstrated Impact — 20%
1. **Problem significance and user relevance** — seberapa relevan problem yang diangkat; tim harus paham siapa user yang terdampak, pain point-nya, dan tantangannya di dunia nyata.
2. **Value creation** — kondisi *before → after*: bagian mana dari kondisi eksisting yang diperbaiki produk. Contoh dimensi: efficiency, accessibility, safety, accuracy, reliability.
3. **Impact evidence** — panitia mengharapkan **user validation**. Klaim harus didukung bukti nyata: user feedback, expert validation, usability testing, pilot results, dsb. *Any user validation will be appreciated.*

#### Adoption, Feasibility and Scalability — 10%
1. **Adoption pathway** — siapa yang akan memakai, dan bagaimana produk masuk ke *existing workflow*.
2. **Implementation feasibility** — seberapa layak diimplementasikan; sebutkan external dependencies dan tantangan legal, privacy, data availability, serta sisi cost.
3. **Scalability potential** — bagaimana produk akan di-expand agar jangkauannya lebih luas.

#### Innovation and Meaningful Differentiation — 15%
1. **Originality** — konsep produk yang berbeda; seberapa orisinal idenya.
2. **Meaningful differentiation** — jelaskan bedanya dengan solusi yang sudah ada.
3. **Practical innovation** — jangan berinovasi hanya demi inovasi; inovasi harus punya manfaat nyata (accessibility, effectiveness, efficiency, usability, dll).

> Framing panitia: tujuannya *creating impact yang tidak redundant* — produk yang tidak menabrak solusi yang sudah ada.

#### Functional Product and User Experience — 10%
1. **End-to-end functionality** — apa yang diklaim di paper harus benar-benar jalan; harus ada *user journey* yang jelas.
2. **Product usability** — produk enak dipakai oleh *intended user*; tim harus tahu siapa target user-nya (termasuk pertimbangan seperti age group terhadap desain UI).
3. **System integration and reliability** — bagaimana front-end, back-end, dan AI layer terintegrasi di dalam repository.

#### AI Implementation and Technical Excellence — 20%
1. **Correctness of AI approach** — pemilihan model, metode, dan arsitektur AI yang cocok untuk problem yang dikerjakan.
2. **Technical depth and justification** — jelaskan data pipeline, training, dan inference dengan jelas. Panitia secara eksplisit mengharapkan pembahasan **trade-off**: bereksperimen dengan beberapa opsi dan menjelaskan mana yang cocok di kondisi apa.
3. **AI product integration** — AI harus menjadi **inti produk**, bukan sekadar fitur tambahan yang kalau dihapus produknya tetap jalan. Ini poin penilaian penting.
4. **Robustness and efficiency** — seberapa robust model di situasi produksi, dan efisiensinya (termasuk estimasi cost penerapan).

#### Evaluation, Reliability and Responsible AI — 10%
1. **Experimental evaluation** — gunakan metrics dan baseline, atau cara evaluasi lain yang valid untuk model AI-nya.
2. **Reliability and error analysis** — identifikasi failure case dan edge case yang mungkin muncul di produksi, serta bagaimana produk menanganinya.
3. **Responsible AI consideration** — limitasi AI: privacy, bias, hallucination, security/safety — dan bagaimana tim memitigasinya.

#### System Design, Engineering and Reproducibility — 5%
1. **System architecture and code quality** — codebase harus *maintainable*; orang lain yang melanjutkan tidak kerepotan.
2. **Documentation and setup** — README lengkap: dependency requirements, setup instructions. Orang yang membuka repo harus langsung paham gambaran aplikasi dan cara setup-nya.
3. **Reproducibility and access** — dataset, model weights, dan artefak lain diupload ke Hugging Face agar panitia bisa mereproduksi.

#### Product Demonstration and Presentability — 10% (dinilai dari video demo)
1. **Business and product clarity** — komunikasikan dengan jelas: masalahnya, siapa target user-nya, product value, dan kenapa solusi ini penting.
2. **Working product demonstration** — perlihatkan fitur-fitur utama dan **di mana letak AI-nya**.
3. **Demo credibility and completeness** — demo harus realistis dan apa adanya; output harus benar; tunjukkan alur end-to-end; **jangan menampilkan mock-up atau fitur yang belum dibuat**.
4. **Public-facing presentability** — presentasikan seolah untuk publik umum, bukan hanya untuk mahasiswa ilmu komputer atau orang yang paham AI. Harus bisa dipahami audiens dengan latar belakang berbeda.

---

## 4. Q&A Session (Slido + tanya langsung)

Disusun sebagai pasangan pertanyaan → jawaban panitia. Beberapa jawaban ditandai *belum final*.

**Q1. Bisa dielaborasi soal "teams are permitted to make changes to the original concept product"? Apakah boleh full change asal temanya sama?**
A: Perubahan diharapkan berupa **refinement** — misalnya menemukan metode atau hal baru yang bisa ditambahkan sehingga idenya berubah. Yang penting **masih meng-address masalah yang sama**. Bukan "ide kemarin jelek, pakai ide baru saja", melainkan menyempurnakan ide yang sudah disubmit. Detail lebih jelas akan diberikan menyusul.

**Q2. Ada contoh video demo finalis tahun lalu?**
A: *Belum final.* Setahu panitia tahun lalu tidak ada demo video. Akan dicek ulang; kalau ada, dibagikan lewat WhatsApp.

**Q3. Kalau ada perubahan/penyesuaian fitur dari concept paper, masih aman?**
A: **Masih sangat aman.** Yang tidak boleh adalah benar-benar mengubah tema / meng-address problem yang benar-benar baru.

**Q4. Ganti AI product-nya boleh? Ganti ide boleh?**
A: **Tidak boleh.**

**Q5. Kalau perubahan total pada paper, ditolak atau hanya pengurangan nilai?**
A: Saat ini tidak diperbolehkan; **risikonya diskualifikasi**.

**Q6. Untuk video demo, kalau durasi lebih dari 5 menit apakah ada toleransi (misal 1–1,5 menit lebih)?**
A: **Tidak.** Demi keadilan, aturannya strict: maksimal 5 menit, minimal 3 menit. Lewat 5 menit tidak diterima, kurang dari 3 menit tidak diterima.

**Q7. Maksimal 12 halaman sudah termasuk appendix?**
A: **Tidak.** 12 halaman hanya isi konten paper. Daftar pustaka dan lampiran tidak dihitung.

**Q8. Kalau AI-nya langsung memakai API OpenAI, boleh?**
A: **Boleh.** Alasannya reproducibility tetap terjaga — panitia bisa menembak API yang sama untuk mereplikasi.

**Q9. Boleh minta slide TM-nya?**
A: Ya, akan di-share.

**Q10. Kalau target user-nya anggota instansi pusat yang susah ditemui, bagaimana cara mendapat user feedback? Apakah kantor cabang boleh? Bentuk feedback-nya apa?**
A: Panitia mengakui ini di luar ranah mereka dan harus dipikirkan tim sendiri. Poinnya: **kantor cabang tidak masalah** (tidak harus pusat) selama cabang tersebut bisa menjawab pertanyaan dan **memvalidasi permasalahan** yang diangkat. **Bentuk user feedback bebas** — diserahkan ke kreativitas tim, tidak dibatasi. Mendapatkan user feedback akan jadi **poin plus besar**.

**Q11. User feedback sifatnya wajib?**
A: **Tidak wajib.** Sifatnya *nice to have* dan menjadi **plus point**; tim yang melakukannya akan lebih dihargai usahanya. Tidak melakukannya tidak menyebabkan diskualifikasi.

**Q12. User feedback ditaruh di mana — saat demo, atau wajib dicantumkan di paper?**
A: **Lebih baik dicantumkan di paper**, karena dalam 5 menit video sulit menampilkan user feedback lengkap. Taruh di **lampiran** — lampiran tidak dihitung ke batas halaman, jadi batas 12 halaman tidak menjadi kendala.

**Q13. Apakah ada pernyataan tertulis dari panitia terkait hak proyek hasil semifinalis (karena panitia mendapat repo proyek)?**
A: **Hak tetap milik peserta.** Namun sebagai bagian dari kompetisi, pihak Datathon meminta izin untuk **mempublikasikan hasil kerja** peserta.

**Q14. Lanjutan Q13: bagaimana kalau proyek semifinalis dipakai panitia untuk lomba-lomba lain?**
A: *Belum terjawab.* Dinilai sebagai isu baru, akan didiskusikan dan dijawab di grup chat.

**Q15. Kalau memakai data sintetis, apakah nilainya berbeda dibanding memakai data asli sejak awal?**
A: **Sama saja**, selama tim bisa menunjukkan bahwa penggunaan data sintetis membawa impact yang baik, performa model sesuai harapan, dan *good enough* untuk dipakai di lingkungan produksi. Intinya: produk benar-benar berjalan.

---

## 5. Aturan yang bersifat *hard fail* (jangan dilanggar)

| Aturan | Konsekuensi |
|--------|-------------|
| Mengganti ide/produk/problem secara total dari concept paper | Diskualifikasi |
| Video demo <3 menit atau >5 menit | Video tidak diterima |
| Paper >12 halaman konten | Melanggar ketentuan format |
| Repository tetap private setelah deadline (tanpa arrangement collaborator) | Tidak bisa dinilai panitia |
| Mendemokan fitur mock-up / fitur yang belum dibuat | Menghancurkan skor Demo Credibility |
| Fitur diklaim di paper tapi tidak ada di produk | Penalti pada Implementation & Demo |

> **PERINGATAN untuk AI assistant — jangan campur aturan antar babak.**
> Larangan Kaggle di babak preliminary (**dilarang** data eksternal, **dilarang** akses model via API call, wajib open weights) **HANYA berlaku untuk Kaggle competition preliminary**. Di babak semifinal, aturan itu tidak berlaku: memakai **API OpenAI diperbolehkan** (lihat Q8), dan data eksternal maupun data sintetis diperbolehkan (lihat Q15). Jangan pernah menolak sebuah desain semifinal dengan alasan aturan Kaggle.

---

## 6. Known gaps & item yang masih menunggu panitia

Per akhir TM 30 Juli 2026, hal-hal berikut **belum final** dan akan diumumkan lewat **grup WhatsApp**:

1. Detail lebih jelas soal batasan perubahan concept paper (seberapa jauh "refinement" boleh berjalan).
2. Ketersediaan contoh video demo finalis tahun sebelumnya.
3. Kejelasan soal penggunaan proyek semifinalis oleh panitia untuk kompetisi/keperluan lain.
4. Slide technical meeting yang akan dibagikan.
5. **Konvensi penamaan file proposal semifinal belum disebutkan.** Di preliminary formatnya `TeamName_ConceptPaper.pdf`. Untuk semifinal belum ada aturan resmi — asumsi paling aman mengikuti pola yang sama (mis. `IndomaretLabtekV_Proposal.pdf`), tapi **konfirmasi ke panitia**.
6. **Jam deadline 10 Agustus belum disebutkan** (preliminary memakai 23:59 WIB). Asumsikan 23:59 WIB, tapi konfirmasi.
7. **Apakah skor preliminary (60% paper + 40% Kaggle) ikut dibawa ke penilaian semifinal, atau semifinal dinilai dari nol dengan rubrik 100% di §3, tidak dinyatakan.** Rubrik semifinal berjumlah tepat 100% tanpa komponen preliminary, jadi asumsi kerja: **semifinal dinilai berdiri sendiri**.

**Untuk AI assistant:** jangan berasumsi keempat poin di atas sudah punya jawaban. Kalau relevan dengan tugas yang sedang dikerjakan, tandai sebagai *unknown* dan minta user mengecek grup WhatsApp.

---

## 7. Catatan sumber (kualitas transkrip)

Dokumen ini disusun dari transkrip otomatis (ASR), sehingga:

- Bagian awal transkrip berisi noise ASR ("jangan lupa like, share, dan subscribe") yang **bukan** bagian dari technical meeting dan sudah diabaikan.
- "New Reps 2015" pada transkrip = **NeurIPS 2015** (format paper).
- "Pak Nitya"/"manitia" = **panitia**.
- Angka dan tanggal sudah diverifikasi silang antar bagian transkrip; bila ada konflik dengan pengumuman resmi panitia, **pengumuman resmi yang menang**.
- Technical meeting ini tidak memakai formal attendance; sesi ditutup setelah dokumentasi (screenshot) bersama.

---

## 8. Checklist eksekusi tim

**Paper**
- [ ] Migrasi concept paper ke struktur proposal + tambahkan `Results and Discussion`
- [ ] Pastikan problem & produk konsisten dengan submisi penyisihan
- [ ] Tambahkan bukti user validation di lampiran
- [ ] Cek konten ≤12 halaman (di luar references & appendix), export PDF

**Implementation**
- [ ] Working product end-to-end (bukan prototipe parsial)
- [ ] README: overview, dependency requirements, setup instructions, cara run
- [ ] Upload dataset & model weights ke Hugging Face, siapkan link terpisah
- [ ] Set repository ke public setelah deadline
- [ ] Verifikasi setiap fitur yang diklaim di paper benar-benar berjalan

**Video Demo**
- [ ] Skrip: ±1 menit sisi bisnis + ±2–4 menit demo produk
- [ ] Durasi total terkunci di 3–5 menit
- [ ] Hanya menampilkan fitur yang sudah jadi, output asli
- [ ] Bahasa dapat dipahami audiens non-teknis
- [ ] Upload ke YouTube/Google Drive, cek akses publik

---

## Lampiran A — Konteks babak Preliminary (sudah selesai, untuk latar belakang saja)

Sumber: slide `Datathon_TM_Preliminary_UNI.pdf` (University Track). Bagian ini **tidak mengatur** pekerjaan semifinal; gunakan hanya untuk memahami dari mana proposal semifinal berasal.

**Penyelenggara:** RISTEK Fasilkom UI · Datathon 2026 · presented by OpenAI, in collaboration with BDO, glair.ai, hAIppy.

**Timeline preliminary**

| Milestone | Tanggal |
|-----------|---------|
| Preliminary round dimulai | 13 Juli 2026 |
| Kaggle access check day | 13–15 Juli 2026 |
| Kaggle Competition Task 1 | 18 Juli 2026, 12:00–17:00 WIB |
| Kaggle Competition Task 2 | 19 Juli 2026, 12:00–17:00 WIB |
| Technical writeup deadline | 20 Juli 2026, 23:59 WIB |
| Concept paper deadline | 23 Juli 2026, 23:59 WIB |
| Pengumuman semifinalis | 29 Juli 2026 |

**Rubrik preliminary (total 103%)**

| Komponen | Kriteria | Bobot |
|----------|----------|-------|
| AI Product Concept Paper (60%) | Impact | 25% |
| | Solution Technical Quality | 15% |
| | Originality & Creativity | 10% |
| | Scalability & Production Readiness | 7.5% |
| | Report Structure | 2.5% |
| Kaggle Competition (40%) | Task 1 – Private Leaderboard | 12.5% |
| | Task 1 – Technical Writeup | 7.5% |
| | Task 2 – Private Leaderboard | 12.5% |
| | Task 2 – Technical Writeup | 7.5% |
| Bonus | Workshop attendance (+1% per workshop, maks 3) | 3% |

Skor leaderboard dinormalisasi ke skala 0–100, dengan batas bawah = skor baseline panitia dan batas atas = skor tim peringkat 1.

**Aturan Kaggle preliminary (tidak berlaku di semifinal — lihat peringatan di §5):** pretrained model boleh hanya jika open weights dan bukan lewat API call; data eksternal dilarang; kolaborasi antar tim dilarang; prediksi manual dilarang; maks 5 submission per task; skor 30% public + 70% private; final submission wajib reproducible dan "run all" di Kaggle Environment; toleransi reproducibility = rata-rata selisih skor antar tim di Top 35 private leaderboard.

**Benchmark pemenang Datathon 2025** (dipakai panitia sebagai contoh standar, "we expect something even better from you this year"):

| Peringkat | Tim | Judul / Produk |
|-----------|-----|----------------|
| 1st | Timnya Olip (UGM) | Analisis Perilaku Pengunjung Toko Retail dengan Computer Vision dan Multimodal Transformer Terintegrasi untuk Optimalisasi Strategi Bisnis — produk **TracKO** (`ristek.link/dt25-1stplace`) |
| 2nd | Blekping (BINUS) | Sistem AI Multimodal untuk Deteksi Dini Penyakit dan Analisis Perilaku Ayam — produk **ChickSense** (`ristek.link/dt25-2ndplace`) |
| 3rd | Yujiem Rookies (UGM) | Sistem Rekomendasi Influencer Multiobjektif dan Analisis Konten serta Perilaku Audiens Berbasis NLP — produk **Influensure** (`ristek.link/dt25-3rdplace`) |
| Honorable Mention | Sayonarasrama (UI) | Otomatisasi Verifikasi Dini Klaim Return–Refund Multilingual pada Marketplace menggunakan Early Fusion Multimodal Transformer — produk **BantuBalik.in** (`ristek.link/dt25-honorm`) |

Pola yang konsisten di keempatnya: judul paper akademik formal (Bahasa Indonesia), tetapi **produk punya nama brand dan tampilan dashboard sendiri** yang dipakai di materi presentasi. Ini relevan untuk deliverable video demo semifinal (kriteria *public-facing presentability*).
