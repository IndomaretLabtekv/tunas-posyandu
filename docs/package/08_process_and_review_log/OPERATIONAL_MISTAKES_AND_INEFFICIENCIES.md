# Kesalahan Operasional & Sumber Ketidakefisienan

> Ini bukan bug kode — ini kesalahan proses/komunikasi yang membuang waktu selama sesi. Dicatat supaya tidak terulang.

## 1. File hilang saat transfer Claude → Windows lokal (paling sering terjadi)

**Masalah berulang:** Setiap kali Claude mengirim banyak file sekaligus, minimal satu file gagal tersalin ke repo lokal user karena:

- Browser Windows menambahkan suffix `(1)`, `(2)`, dst pada file dengan nama duplikat
- Beberapa file viewer menampilkan nama dengan **spasi** menggantikan underscore (`test generate synth.py` alih-alih `test_generate_synth.py`)
- User kadang menjalankan perintah `Copy-Item` tapi lupa menjalankan `python -m pytest` setelahnya, atau sebaliknya menjalankan test tanpa menyalin file baru dulu

**Dampak nyata:** Minimal 4 putaran percakapan penuh dihabiskan hanya untuk debug "kenapa jumlah test tidak match" (91 vs 120 vs 183, dst) yang ternyata karena `test_generate_synth.py` atau `test_train.py` tidak ikut ter-copy.

**Pelajaran untuk sesi berikutnya:**
- **Selalu cek jumlah test collected per FILE** (`pytest tests/test_X.py -q --collect-only`) bukan cuma total, begitu ada ketidakcocokan angka.
- Sebelum menyalin banyak file, jalankan dulu skrip pemetaan otomatis berbasis nama file yang sudah dibersihkan dari suffix/spasi (contoh skrip PowerShell ada di riwayat chat, bisa diminta ulang ke Claude).
- **Setelah SETIAP sesi kode**, langsung `git commit` — jangan menumpuk beberapa modul sebelum commit, supaya kalau ada file yang hilang, dampaknya kecil dan mudah dilacak.

## 2. Nama file `evaluate.py` bentrok antar folder

`tabular/evaluate.py` (metrik model) dan `cv/evaluate.py` (runner CV-00) punya nama sama. Ini nyaris menyebabkan salah timpa saat instruksi disalin tanpa memperhatikan folder tujuan. **Selalu sebutkan path lengkap** (`tabular\evaluate.py` vs `cv\evaluate.py`) saat memberi instruksi salin-tempel.

## 3. Scaffold awal (`scaffold.sh`) punya bug yang baru ketahuan setelah direview GPT

- `.gitignore` awal mengecualikan `results/**/*.csv` — padahal keputusan desainnya adalah hasil eksperimen kecil justru HARUS di-commit sebagai jejak angka paper. Kontradiksi ini lolos dari Claude sendiri, baru ketahuan saat GPT benar-benar menjalankan scaffold-nya.
- `Makefile` awal punya target `make demo` yang memanggil `docker compose up`, padahal `docker-compose.yml` belum pernah dibuat — README sempat mengklaim command itu tersedia padahal pasti gagal.
- `configs/` awal cuma diisi `.gitkeep` (folder kosong tidak ter-track git), bukan config nyata.

**Pelajaran:** Scaffold/infrastruktur perlu benar-benar DIJALANKAN dan diverifikasi (bukan cuma dibaca) sebelum diklaim siap pakai. Klaim "sudah saya uji" dari Claude sebelumnya kurang lengkap — pengujian pertama cuma mengecek script tidak error, bukan mengecek isinya konsisten dengan dokumen keputusan lain.

## 4. Nama produk dibahas berulang kali sebelum benar-benar dikunci

Diskusi nama (Tunas vs TumbuhTepat vs Ukurin) berlangsung 2 putaran penuh sebelum GPT memberi argumen penutup yang membuat keputusan bertahan ("Tunas + descriptor konsisten, karena paper juara tidak pernah menyebut nama brand di isi paper"). Ini bukan waktu yang sia-sia (hasilnya dipakai konsisten sepanjang sisa sesi), tapi bisa dipercepat kalau riset ke paper juara dilakukan LEBIH DULU sebelum brainstorming nama, bukan sesudahnya.

**Pelajaran:** Untuk keputusan yang butuh referensi eksternal (pola nama pemenang tahun lalu), cek referensi dulu baru brainstorming — bukan brainstorm dulu baru divalidasi.

## 5. Asumsi tanggal yang perlu diverifikasi ulang

Rencana awal (`docs/PLAN.md`) mengasumsikan ketua tim berangkat "7 Agustus pagi" dan wawancara harus terjadi sebelum itu. Tapi percakapan menunjukkan wawancara benar-benar dilakukan pada **8 Agustus**. Ada inkonsistensi tanggal yang tidak pernah diklarifikasi ulang secara eksplisit dalam sesi ini.

**Tindakan wajib saat melanjutkan:** konfirmasi ulang tanggal keberangkatan sebenarnya, durasi ketidaktersediaan, dan apakah rencana timeline di `02_docs/PLAN.md` masih valid atau perlu di-rebaseline lagi (`PLAN.md` sudah pernah di-rebaseline sekali dari 4→5 Agustus).

## 6. Analisis "headline" sempat dibangun dari angka yang salah unit

Kalimat dampak (`headline()` di `train.py`) sempat dirancang berdasarkan evaluasi PER KUNJUNGAN, bukan PER ANAK — sehingga klaim "20% dari anak yang dipantau" secara teknis salah sebelum bug unit-evaluasi diperbaiki. Untungnya ini ketahuan sebelum masuk paper (karena disiplin "jangan salin angka ke paper sebelum data final"), tapi ini pengingat bahwa **angka headline/demo harus dibangun ULANG setiap kali unit dasar evaluasi berubah**, jangan disalin dari draft lama.

## 7. Efek gabungan: total waktu terpakai untuk debug-transfer vs menulis kode baru

Dari observasi pola percakapan, rasio "waktu klarifikasi file/copy-paste" berbanding "waktu menulis modul baru" cukup tinggi di paruh kedua sesi (setelah kode mulai banyak). Ini wajar untuk kolaborasi lintas-platform (Claude sandbox Linux → Windows lokal user) tapi bisa ditekan dengan:

- Commit lebih sering (per modul, bukan per beberapa modul)
- Selalu cross-check jumlah test per file sebelum lanjut ke modul berikutnya
- Kalau ragu file sudah benar, jalankan `git status --short` dan `git diff --stat` sebelum commit untuk melihat apa yang benar-benar berubah
