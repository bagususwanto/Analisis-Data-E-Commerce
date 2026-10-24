# Execution Status — Proyek Analisis Data E-Commerce

Terakhir diperbarui: 24 Oktober 2026, Asia/Jakarta.
Acuan: [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md), versi 2.1.

## Ringkasan untuk AI berikutnya

- Status pekerjaan: **P00–P03 selesai; P04 belum dimulai**.
- Phase berikutnya: **P04 — Integrasi dan kontrak data analisis**.
- Permintaan pengguna terakhir: eksekusi P03 — Cleaning dan penanda kualitas. Gate lulus; P04 belum dimulai.
- Artefak yang tersedia: plan/tracker, baseline dan templat P00, `src/config.py`, `src/data_pipeline.py`, requirements runtime/dev, README, `scripts/check_foundation.py`, `reports/foundation_validation.json`, modul/skrip assessment, `reports/data_quality.json`, ringkasan notebook, laporan verifikasi P02, fungsi cleaning, tes pipeline, serta audit/trace/verifikasi P03.
- Kondisi terakhir: sembilan CSV sumber tetap sesuai hash baseline; fondasi dan cleaning enam sumber berhasil diverifikasi. Hasil cleaning dikembalikan sebagai tabel dalam memori; tabel analisis/dashboard belum diekspor. Notebook analisis dan dashboard belum dibuat. Runtime terpilih: Python 3.12.13 dalam `.venv`, juga dicatat pada `.python-version`.
- P00 memverifikasi sembilan CSV, ukuran, SHA-256, jumlah baris, dan profil awal pada 22 Oktober 2026. Seluruh jumlah baris dan temuan numerik yang diperiksa sesuai plan; hash pertama tersimpan pada `reports/baseline.json`. Assessment formal selesai pada P02; profil lengkap ditambahkan ke baseline tanpa mengubah hash/riwayat P00.
- Salinan lokal templat notebook: **terverifikasi**, nbformat 4, 37 sel. URL sumber, waktu pengambilan, heading, dan SHA-256 tersedia dalam baseline; gunakan salinan ini pada P07.
- Identitas notebook diberikan langsung oleh pengguna: **Bagus Uswanto**, **DS013B6Y0318@student.devacademy.id**, ID Dicoding **DS013B6Y0318**. Tersimpan di `reports/baseline.json`; gunakan pada P07.
- Deployment: akun/repo/branch/visibilitas belum ditetapkan untuk proyek ini; tidak ada URL deployment yang telah diverifikasi.

Keputusan periode, eligibility, nilai uang, seleksi review, dan RFM mengacu ke bagian 3–5 dalam plan. Jangan menggandakan aturan tersebut di tracker dengan versi berbeda.

## Status phase

Status yang sah: `not_started`, `in_progress`, `completed`, `blocked`, dan khusus P11 `deferred_external`. Status berikut mencatat eksekusi aktual terakhir.

| Phase | Fokus | Status | Bukti terakhir | Langkah berikutnya |
| --- | --- | --- | --- | --- |
| P00 | Inventaris dan templat | `completed` | Baseline 9 CSV dan templat JSON 37 sel terverifikasi | Gunakan baseline untuk P01/P02 |
| P01 | Lingkungan dan fondasi | `completed` | Impor, pip check, loader 99.441 order, path dari /tmp, dan 9 hash sumber lulus | Fondasi dipakai pada P02/P03 |
| P02 | Gathering dan assessment | `completed` | 9 profil, 21 issue dengan kebijakan, pemeriksaan CSV independen, entry point /tmp, dan 9 hash sumber lulus | Kebijakan diterapkan pada P03 |
| P03 | Cleaning | `completed` | 31 tes lulus; cleaning deterministik, 98.673 pemenang review dan total sen cocok secara independen; 9 hash utuh | Bangun tabel order/item dan eligibility P04 |
| P04 | Join dan kontrak data | `not_started` | Belum ada tabel turunan | Bangun order/item-level setelah P03 |
| P05 | Analisis Q1–Q2 | `not_started` | Belum ada hasil bisnis | Hitung agregasi setelah P04 |
| P06 | RFM dan Q3 | `not_started` | Belum ada RFM | Hitung metrik/segmen setelah P04 |
| P07 | Notebook dan visualisasi | `not_started` | Belum ada notebook | Setelah analisis dan templat terverifikasi |
| P08 | Ekspor data dashboard | `not_started` | Belum ada CSV turunan | Setelah kontrak/analisis siap |
| P09 | Dashboard Streamlit | `not_started` | Belum ada aplikasi | Setelah P07/P08 |
| P10 | Verifikasi dan dokumentasi | `not_started` | Belum ada pemeriksaan implementasi | Setelah P09 |
| P11 | Deployment | `not_started` | Belum ada URL terverifikasi | Setelah P10 dan konteks eksternal tersedia |
| P12 | ZIP dan audit akhir | `not_started` | Belum ada paket submission | Setelah kesiapan lokal dan status P11 jelas |

## Dependency eksternal yang diketahui

Bagian ini mencatat kebutuhan; belum berarti phase terkait sudah dijalankan dan terblokir.

| Kebutuhan | Dipakai oleh | Dampak bila belum tersedia |
| --- | --- | --- |
| Salinan notebook templat terverifikasi | P00, P07 | Terpenuhi pada P00; gunakan `references/notebook_template.ipynb` |
| Identitas pemilik notebook | P07, P10, P12 | Sudah diberikan pengguna dan dicatat; masukkan saat menyusun notebook P07 |
| Konteks repositori dan akses deployment | P11 | Paket lokal tetap dapat disiapkan; saran deployment belum terpenuhi |

## Log phase yang telah dieksekusi

### P00 — Inventaris dan sumber acuan

Mulai: 22 Oktober 2026, 19:56 Asia/Jakarta.  
Verifikasi akhir: 22 Oktober 2026, 19:59 Asia/Jakarta.  
Status: `completed`.

- Prasyarat: plan v2.1 dan tracker dibaca; pencarian `AGENTS.md` pada workspace/parent tidak menemukan instruksi tambahan. Workspace belum merupakan repositori Git dan belum memiliki kode implementasi.
- Keluaran: `reports/baseline.json` memuat ukuran byte, SHA-256, jumlah baris, kolom, peran enam CSV utama/tiga pendukung, profil pembanding plan, inventaris runtime, provenance templat, dan kebutuhan identitas.
- Templat: diambil dari URL download publik untuk file ID yang sama dengan tautan Colab pada plan. Akses web awal gagal; unduhan Python melalui akses jaringan yang disetujui berhasil. JSON nbformat 4 dengan 37 sel; SHA-256 `a278bc0b6f5210e56f820c4afe3c9320da0a3db26d188ff566a3ce3bb5f29b33`.
- Verifikasi aktual: `python3 /tmp/ecommerce_p00.py` (skrip pemeriksaan sementara, bukan entry point proyek), exit 0; sembilan CSV berjumlah 1.550.922 baris dan seluruh jumlah per file sesuai plan. Pembacaan ulang SHA-256: 9/9 sama setelah pemeriksaan. Pemeriksaan independen akhir membaca kembali baseline, CSV, dan templat.
- Profil: 96.478 delivered, delapan delivered tanpa tanggal penerimaan, 610 produk tanpa kategori, 547 pesanan dengan beberapa review, dan 2.961 pesanan dengan beberapa pembayaran cocok dengan plan. Rincian tanggal dan profil lain tersimpan pada baseline. Penilaian schema/tipe, kunci, dan kualitas formal tetap P02.
- Keputusan definisi kosong: judul/pesan ulasan kosong murni masing-masing 87.656/58.247; setelah teks hanya whitespace ikut dihitung menjadi 87.658/58.274, sesuai plan. Pemeriksaan pertama dengan definisi kosong murni memicu assertion; definisi kemudian diperjelas dan pemeriksaan ulang lulus. Tidak ada CSV yang diubah.
- Runtime tersedia: Python 3.14.5 pada `/opt/homebrew/opt/python@3.14/bin/python3.14`. Belum dipilih sebagai runtime final atau diuji kompatibilitas dependensinya; ini milik P01.
- Identitas: nama lengkap, email, dan ID Dicoding berstatus `needs_user_input`; tidak menghambat pekerjaan data. File tambahan `data/New Text Document.txt` dipertahankan dan tidak dipakai sebagai sumber analisis.
- Gate: lulus; sembilan sumber teridentifikasi, baseline tersedia, templat dan asalnya terverifikasi, kebutuhan identitas dicatat tanpa mengarang.
- Berikutnya: P01, pilih runtime kompatibel dan lingkungan terisolasi, kemudian buat konfigurasi, loader, requirements awal, dan README sesuai plan. P01 belum dieksekusi.

Saat sebuah phase dikerjakan, tambahkan entri dengan format:

```text
Phase: Pxx — nama phase
Mulai: YYYY-MM-DD HH:MM Asia/Jakarta
Pembaruan terakhir: YYYY-MM-DD HH:MM Asia/Jakarta
Status: in_progress / completed / blocked / deferred_external

Prasyarat yang diperiksa:
- Artefak dependency, versi/hash bila relevan, dan hasil pemeriksaan.

Perubahan dan keluaran:
- Path file aktual serta fungsi/isi yang ditambahkan atau diubah.

Verifikasi yang benar-benar dijalankan:
- Perintah atau langkah UI: ...
- Hasil aktual/exit code/angka rekonsiliasi: ...
- Lokasi laporan/screenshot bila dibuat: ...

Gate:
- Lulus/belum lulus, dengan bukti dan syarat yang masih belum terpenuhi.

Masalah dan keputusan baru:
- Alasan, bukti sumber, serta phase/file yang terdampak.

Langkah berikutnya:
- Satu tindakan spesifik yang harus dilanjutkan AI berikutnya.
```

## Pemeriksaan yang perlu diulang akibat perubahan

Tidak ada pemeriksaan ulang tertunda setelah P03. Jika sumber/loader/assessment berubah, hasil P02 dan profil baseline harus dihasilkan serta diverifikasi ulang. Jika fungsi cleaning berubah, jalankan kembali tes P03 dan `scripts/check_cleaning.py`, lalu perbarui audit, trace, dan hasil verifikasi sebelum memakai tabel pada P04. Ketika pipeline atau metrik berubah pada phase berikutnya, catat phase terdampak sampai verifikasi ulang lulus.

## Riwayat perubahan perencanaan

- **22 Oktober 2026:** implementation plan diperinci menjadi P00–P12 dengan dependency, keluaran, gate, kontrak data, pemeriksaan integritas, dan contoh prompt. Tracker ini dibuat untuk handoff antar-AI. Tidak ada phase implementasi, pengujian proyek, deployment, atau pengemasan yang diklaim selesai.
- **22 Oktober 2026 — audit rubrik:** kelima tab instruksi Dicoding dibaca kembali. Plan versi 2.1 mempertegas bahwa target maksimum memerlukan empat kriteria wajib dan empat saran, termasuk deployment berhasil + `url.txt`. Ditambahkan checklist bintang 5 pada bagian 10.1, audit orisinalitas, pemeriksaan seluruh visualisasi, dan pemetaan SMART. Seluruh phase tetap `not_started`; yang diperiksa adalah kesesuaian rencana, bukan hasil implementasi.

## Pembaruan identitas pemilik

- 2026-10-22T20:05:22+07:00: pengguna memberikan nama **Bagus Uswanto**, email **DS013B6Y0318@student.devacademy.id**, dan ID Dicoding **DS013B6Y0318**. Identitas baseline diperbarui menjadi `provided_by_user`; catatan kebutuhan identitas pada log P00 merupakan kondisi historis sebelum pembaruan ini. P01 belum dimulai.

### P01 — Lingkungan dan fondasi kode

- Mulai: 2026-10-22T20:06:56+07:00.
- Verifikasi akhir: 2026-10-22T20:22:10+07:00. Status: `completed`.
- Prasyarat: plan v2.1 dan tracker dibaca; sembilan SHA-256 sumber P00 serta hash templat cocok. Tidak ditemukan AGENTS.md pada workspace, ancestor, atau direktori yang diedit.
- Lingkungan: `.venv` terisolasi menggunakan Python 3.12.13 yang tersedia pada instalasi uv lokal. `.python-version` mencatat versi tersebut. Python 3.14.5 sempat dipakai untuk percobaan awal; unduhan dihentikan oleh pelaksana, kemudian environment yang baru dibuat tersebut diganti dengan 3.12.13. Tidak ada klaim inkompatibilitas 3.14.
- Instalasi: percobaan pip dalam sandbox gagal DNS PyPI. Akses jaringan disetujui dan instalasi akhir melalui `uv --cache-dir /tmp/ecommerce-uv-cache pip install --python .venv/bin/python -r requirements-dev.txt` berhasil, exit 0. Cache unduhan berada di /tmp; `.venv` tidak menggunakan system-site-packages.
- Keluaran: `src/__init__.py`, `src/config.py`, `src/data_pipeline.py`, `requirements.txt`, `requirements-dev.txt`, `.python-version`, `.gitignore`, README awal, skrip pemeriksaan fondasi, dan laporan `reports/foundation_validation.json`.
- Konfigurasi bersama: root dari `__file__`, schema sembilan sumber, enam sumber utama/tiga pendukung, periode eksklusif, acuan RFM, status delivered, sampel 50, recency 30/90, label kategori, BRL/sen, dan aturan monetary quantile/interpolasi.
- Kontrak loader: semua kolom mentah StringDtype; field kosong menjadi pd.NA; whitespace, ID berawalan nol, literal NA, dan representasi uang dipertahankan. Tidak ada parsing/cleaning/filter atau penulisan sumber. Nama sumber tidak dikenal, file hilang, dan kolom wajib hilang memiliki error yang jelas. Path relatif data dihitung dari root proyek.
- Versi langsung terpasang dan dipin: pandas 3.1.0, NumPy 2.5.4, Matplotlib 3.11.2, Seaborn 0.13.2, Streamlit 1.66.1; ipykernel 7.4.0, nbconvert 7.17.2, nbformat 5.11.1, pytest 9.1.1. Requirements dev memasukkan runtime melalui `-r requirements.txt`. Inventaris seluruh paket ada dalam laporan. Pin final/clean install tetap P10.
- Verifikasi aktual, seluruhnya exit 0:
  - Impor `src.config` dan `src.data_pipeline` langsung dari root menggunakan `.venv/bin/python -c ...`.
  - `MPLCONFIGDIR=/tmp/ecommerce-mpl-cache .venv/bin/python scripts/check_foundation.py` dari root.
  - Pemanggilan path absolut `.venv/bin/python` dan `scripts/check_foundation.py` dari `/tmp` (cwd terlapor `/private/tmp`), dengan MPLCONFIGDIR yang sama.
  - Skrip mengimpor sembilan paket runtime/dev; pip check melaporkan `No broken requirements found.`; CSV orders memiliki 99.441 baris dan delapan kolom string; ID asli cocok; data_dir relatif tetap merujuk root. Kasus file/kolom hilang, sumber tidak dikenal, ID nol depan, NA literal, desimal, dan field kosong lulus.
  - Sembilan hash CSV dan hash templat tidak berubah. Laporan terakhir menyimpan invocation cwd, versi Python/paket, hasil pip check, daftar pemeriksaan, serta hash sumber.
- Gate: lulus. Lingkungan tercatat dan terisolasi, konfigurasi terpusat, loader membaca data asli, dan entry point terbukti bekerja dari direktori lain. Tidak ada hambatan P01 tersisa.
- Batas verifikasi: belum menjalankan assessment formal, cleaning, metrik, notebook, atau dashboard; pengujian tahapan tersebut dilakukan oleh phase pemiliknya. Tidak membuat placeholder artefak phase berikutnya.
- Langkah berikutnya: P02 — muat enam tabel utama melalui loader, lengkapi profil baseline dan susun issue register pada `reports/data_quality.json` sesuai plan.

### P02 — Gathering dan Assessing Data

- Mulai: 2026-10-24T09:09:57+07:00.
- Verifikasi akhir: 2026-10-24T09:13:32+07:00. Status: `completed`.
- Prasyarat: plan/tracker dan fondasi P01 dibaca; working tree awal bersih; tidak ditemukan AGENTS.md pada workspace/ancestor. Sembilan hash sumber dan hash templat cocok dengan baseline P00 sebelum/sesudah assessment.
- Keluaran: `src/data_assessment.py`, `scripts/assess_data.py`, `reports/data_quality.json`, `reports/assessment_summary.md`, dan `reports/assessment_validation.json`. Baseline ditambah `assessment_profile` pada sembilan sumber (baris, kolom, StringDtype awal, null/whitespace, duplikasi, tanggal/numerik/kunci; status orders), tanpa mengganti hash, identitas, atau riwayat P00. README memuat perintah reproduksi.
- Cakupan: enam sumber utama dimuat melalui loader; tiga pendukung diprofilkan sebagai sumber tambahan. Assessment hanya memakai salinan parsing untuk observasi. Belum ada transformasi cleaning, seleksi ulasan, tabel join, atau metrik bisnis akhir.
- Temuan aktual: 610 produk tanpa kategori (1.603 baris item), 13 produk dari 2 kode tanpa terjemahan (24 item); 547 order memiliki beberapa review (551 baris tambahan), 814 kemunculan review_id tambahan melintasi 789 ID. Tidak ada duplikasi persis pada enam sumber utama; pasangan review_id/order_id juga unik.
- Tanggal: 2.965 order tanpa tanggal penerimaan, termasuk 8 delivered (semuanya dalam periode utama); 1.382 order memiliki setidaknya satu inversi urutan lifecycle. Tidak ada penerimaan sebelum pembelian. Sebanyak 64 review mempunyai tanggal pembuatan kalender sebelum pembelian; 4 item pada 3 order mempunyai shipping_limit pada 2020. Rincian pasangan tanggal, populasi, dan jumlah menurut status ada dalam JSON.
- Cakupan tambahan: 775 order tanpa item (0 delivered), 768 order tanpa review (646 delivered); 2.961 order memiliki beberapa pembayaran. Geolocation memuat 261.831 baris identik tambahan dan kode pos berulang; tetap sumber pendukung yang tidak dipakai Q1–Q3.
- Pemeriksaan tanpa pelanggaran: kunci orders/customer/product/translation dan order-item lengkap serta unik; tidak ada kegagalan parsing tanggal/numerik, harga negatif/nol, presisi uang di luar sen, atau skor di luar integer 1–5. Semua foreign key yang diuji cocok, kecuali 2 kode kategori tanpa terjemahan yang dicatat terpisah. Freight nol sebanyak 383 tetap valid.
- Verifikasi aktual (exit 0): `.venv/bin/python scripts/assess_data.py` dari root; kemudian executable dan skrip berpath absolut dari `/tmp` (invocation cwd `/private/tmp`). Eksekusi terakhir menghasilkan 9 profil dan 21 issue dengan kebijakan. Pemeriksaan CSV independen menggunakan `csv.DictReader` mengonfirmasi baris/skema/missing/duplikasi enam sumber, status/kunci, multiplicity review, kategori, dan kronologi review. Kasus kecil memeriksa Decimal 1.230 versus 1.234, invalid/nonfinite, whitespace, kunci komposit, review ID berulang, dan parsing tanggal. Hash mismatch sengaja disimulasikan pada salinan baseline di memori dan ditolak sebelum penulisan laporan, tanpa mengubah CSV. Pemeriksaan akhir membandingkan profil baseline dengan laporan, total status/bulan 99.441, keunikan 21 issue, hash laporan, dan 9 hash sumber; `git diff --check` lulus.
- Gate: lulus. Masalah aktual dan tindakan per issue tersedia, jumlah baris/status dapat direproduksi, serta bahan sel Gathering/Assessing/Steps to Take tersedia. Tidak ada hambatan P02.
- Handoff P03: terapkan tindakan per `issue_id` dalam JSON; bedakan kategori kosong dan belum diterjemahkan; pilih review deterministik sebelum validasi skor; pertahankan null; flag anomali lifecycle/review tanpa menebak tanggal. Inversi approval/carrier atau metadata review tidak otomatis membatalkan sales/RFM maupun skor valid. Review tie-breaker dioperasionalkan dengan urutan menurun creation/answer/review_id/nomor baris sumber (null tanggal sebelum tanggal valid), konsisten dengan pemilihan nilai terbaru pada plan. Isu cakupan tanpa item/review ditangani kontrak eligibility P04; sumber pendukung hanya didokumentasikan sampai dipakai.
- Langkah berikutnya: P03 — implementasikan fungsi cleaning yang mengembalikan data dan audit dampak per issue, lalu verifikasi kasus berisiko sesuai plan. P03 belum dimulai.

### P03 — Cleaning dan penanda kualitas

- Mulai: 2026-10-24T09:14:49+07:00.
- Verifikasi akhir: 2026-10-24T09:20:24+07:00. Status: `completed`.
- Prasyarat: working tree awal bersih; plan/tracker, loader/config, issue register P02 dan instruksi workspace dibaca; tidak ditemukan AGENTS.md pada workspace/ancestor. Hash laporan P02 cocok dengan `assessment_validation.json`; sembilan hash CSV dan hash templat cocok dengan baseline sebelum/sesudah proses.
- Keluaran: `src/data_pipeline.py` kini menyediakan `clean_orders`, `clean_customers`, `clean_translation`, `clean_products`, `clean_order_items`, `clean_reviews`, dan `clean_primary_sources`. Setiap cleaner mengembalikan tabel dan audit. Tambahan: `scripts/check_cleaning.py`, `tests/test_pipeline.py`, `reports/cleaning_audit.json`, `reports/review_selection.csv`, `reports/cleaning_validation.json`, dan petunjuk README. Baseline, laporan P02, serta seluruh sumber mentah tidak diubah.
- Transformasi: timestamp bertipe datetime dengan kolom teks `*_raw` dan flag missing/parse failure/valid; skor integer 1–5 nullable; uang menjadi `price_cents`/`freight_cents` Int64 dari Decimal dan rasio integer tepat. Teks di luar presisi sen memicu `MoneyPrecisionError`, termasuk kasus >28 digit signifikan, tanpa pembulatan. Harga negatif/non-numerik/nonfinite menjadi null dengan alasan, sedangkan harga/freight nol tetap valid. ID dan kode pos tetap string.
- Kategori: 610 produk kosong diberi `category_name` Tidak diketahui dan flag; 13 produk dari dua kode tanpa terjemahan memakai kode asli sebagai nama fallback. `category_code` mempertahankan kode asli atau null. Atribut opsional tetap nullable; empat berat nol dipertahankan dan diberi flag.
- Tanggal: 1.382 inversi lifecycle diberi flag tanpa koreksi spekulatif. Semua 2.965 pasangan delivery yang tidak dapat dievaluasi memiliki `is_late`/`days_late` null, termasuk delapan delivered tanpa penerimaan. Tanggal kalender pada hari estimasi dianggap tepat waktu; selisih negatif yang valid menjadi nol hari terlambat. Label tanggal belum memakai filter status/periode. Inversi approval/carrier saja tidak membatalkan pasangan tanggal aktual/estimasi; estimasi yang mendahului tanggal pembelian diberi flag dan tidak menghasilkan label keterlambatan.
- Ulasan: 99.224 kandidat menjadi 98.673 review terpilih (satu per order); 551 alternatif tersisih pada 547 order. Sebanyak 391 pemenang ditentukan oleh creation terbaru dan 156 oleh answer terbaru; lexical review_id dan ordinal sumber menjadi tie-breaker tambahan yang diuji. Skor diperiksa sesudah seleksi dan review terbaru invalid tidak diganti review lama. Dari 64 kandidat dengan creation sebelum tanggal pembelian, 61 terpilih dan tetap diberi flag; skor valid dipertahankan. Review ID berulang pada pesanan berbeda tidak dihapus; 572 kemunculan ID tambahan tetap ada setelah seleksi per order.
- Jejak: `reports/review_selection.csv` memuat 1.098 kandidat bersaing, 547 pemenang, ordinal sumber, timestamp, skor asli, dan alasan seleksi. `source_row_number` berarti ordinal data record mulai 1 sebelum deduplikasi, bukan nomor baris fisik CSV. Jumlah kandidat dihitung sesudah exact dedup. Pada data asli tidak ada duplikasi persis pada enam sumber utama; jalur exact dedup dan penghentian konflik kunci berbeda isi telah diuji.
- Audit: seluruh 21 issue P02 memiliki jumlah sebelum/sesudah, ukuran/populasi yang dijelaskan, tindakan, serta status. Tiga belas issue P03 ditangani; tiga isu cakupan item/review dan relasi pembayaran tetap milik P04; lima isu bersifat dokumentasi. Sumber pendukung tidak di-clean atau dipakai menghitung Q1–Q3. Perbedaan missing text/metadata pada review akhir berasal dari seleksi kandidat, bukan imputasi.
- Verifikasi aktual, exit 0: `.venv/bin/python -m pytest tests/test_pipeline.py -q` (31 passed); `.venv/bin/python scripts/check_cleaning.py` dari root; kemudian executable dan skrip berpath absolut dari `/tmp` (cwd `/private/tmp`). Skrip menjalankan cleaning dua kali dan membandingkan semua tabel serta audit; pemenang 98.673 order cocok dengan seleksi independen via `csv.DictReader`/datetime; price total 1.359.164.370 sen dan freight 225.190.954 sen cocok dengan jumlah Decimal sumber. Enam kunci keluaran lengkap/unik pada satuan barisnya, seluruh status dan 99.441 order/112.650 item dipertahankan. Hash sembilan CSV dan templat tidak berubah. Pemeriksaan akhir juga memvalidasi hash audit/trace, jumlah kandidat/pemenang, dan `git diff --check`.
- Temuan saat pengujian: dua kasus tanpa kelompok multi-review awalnya gagal karena map kosong menginferensikan tipe numerik pada pandas/Arrow. Implementasi diperbaiki dengan cast string sebelum fill label; ekspektasi tes dipertahankan. Seluruh 31 tes akhir lulus.
- Gate: lulus. Cleaning deterministik dari mentah, kunci siap untuk join tervalidasi, null tidak berubah menjadi label tepat waktu palsu, dan sumber tetap utuh. Tidak ada hambatan P03 tersisa.
- Handoff P04: gunakan `tables, audits = clean_primary_sources()`; agregasikan item per order sebelum join review/customer. Gunakan `price_valid` dan `price_cents` untuk menilai kelengkapan seluruh item, bukan menghitung sebagian order. Review terpilih unik pada `order_id`; `review_id` tidak unik lintas order. Gabungkan `delivery_dates_valid` dengan status delivered/periode saat membentuk eligibility; atribut approval/carrier tidak menjadi filter universal. Gunakan flag kategori untuk memisahkan denominator kategori tidak diketahui dari top 5. Bentuk kontrak tabel order/item, cakupan FK, dan audit rekonsiliasi sesuai plan.
- Langkah berikutnya: P04 — Integrasi dan kontrak data analisis. P04 belum dimulai; belum ada CSV order-level/item-level/RFM, eligibility akhir, atau hasil bisnis Q1–Q3.
