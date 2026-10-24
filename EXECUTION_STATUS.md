# Execution Status — Proyek Analisis Data E-Commerce

Terakhir diperbarui: 24 Oktober 2026, Asia/Jakarta.
Acuan: [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md), versi 2.1.

## Ringkasan untuk AI berikutnya

- Status pekerjaan: **P00–P05 selesai; P06 belum dimulai**.
- Phase berikutnya: **P06 — RFM dan segmentasi Q3**.
- Permintaan pengguna terakhir: eksekusi P05 — Agregasi Q1 dan Q2. Gate lulus; P06 belum dimulai.
- Artefak yang tersedia: plan/tracker, baseline dan templat P00, `src/config.py`, `src/data_pipeline.py`, requirements runtime/dev, README, `scripts/check_foundation.py`, `reports/foundation_validation.json`, modul/skrip assessment, `reports/data_quality.json`, ringkasan notebook, laporan verifikasi P02, fungsi cleaning, tes pipeline, audit/trace/verifikasi P03, builder order/item, kontrak kolom, `reports/join_audit.json`, `reports/data_dictionary.json`, verifikasi P04, `src/analytics.py`, tes agregasi, `reports/analytical_results.json`, dan verifikasi P05.
- Kondisi terakhir: sembilan CSV sumber tetap sesuai hash baseline; fondasi, cleaning enam sumber, integrasi order/item, serta agregasi Q1/Q2 berhasil diverifikasi. Tabel analisis direproduksi dalam memori; ekspor CSV dashboard belum dikerjakan. Notebook analisis dan dashboard belum dibuat. Runtime terpilih: Python 3.12.13 dalam `.venv`, juga dicatat pada `.python-version`.
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
| P03 | Cleaning | `completed` | 31 tes awal; regresi P03 lulus dalam 51 tes P04; hasil cleaning asli tetap sama | Fondasi dipakai integrasi P04 |
| P04 | Join dan kontrak data | `completed` | 6 join, 99.441 order/112.650 item, 51 tes; kontrak dan rekonsiliasi independen lulus | Dipakai agregasi P05/P06 |
| P05 | Analisis Q1–Q2 | `completed` | 73 tes; Q1/Q2 cocok referensi CSV pada 6 skenario; nilai dan coverage cocok P04 | Lanjut RFM/Q3 P06 |
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

Tidak ada pemeriksaan ulang tertunda setelah P05. Jika sumber/loader/assessment berubah, hasil P02 dan profil baseline harus dihasilkan serta diverifikasi ulang. Jika fungsi cleaning berubah, jalankan kembali tes P03 dan `scripts/check_cleaning.py`, lalu perbarui audit, trace, dan hasil verifikasi serta ulang integrasi P04. Jika builder/kontrak berubah, jalankan `scripts/check_integration.py` dan tes pipeline, lalu perbarui audit join, data dictionary, serta verifikasi P04 dan agregasi P05 sebelum analisis lanjutan. Jika fungsi Q1/Q2 berubah, jalankan tes analytics/pipeline dan `scripts/check_analytics.py`, perbarui laporan hasil/verifikasi, lalu ulang artefak turunan yang sudah dibuat. Ketika pipeline atau metrik berubah pada phase berikutnya, catat phase terdampak sampai verifikasi ulang lulus.

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

### P04 — Integrasi dan kontrak data analisis

- Mulai: 2026-10-24T09:49:24+07:00.
- Verifikasi akhir: 2026-10-24T09:55:58+07:00. Status: `completed`.
- Prasyarat: working tree awal bersih; plan/tracker dan keluaran P03 dibaca; tidak ditemukan AGENTS.md pada workspace/ancestor. Hash audit/trace P03 cocok dengan laporan verifikasinya; sembilan hash CSV dan hash templat sesuai baseline sebelum/sesudah integrasi.
- Keluaran: `aggregate_order_items` dan `build_analysis_tables` pada `src/data_pipeline.py`; `src/data_contracts.py`; `scripts/check_integration.py`; tambahan tes pada `tests/test_pipeline.py`; `reports/join_audit.json`, `reports/data_dictionary.json`, dan `reports/integration_validation.json`; README diperbarui. Tabel order/item dikembalikan dalam memori, CSV dashboard menunggu P08.
- Agregasi: item lebih dahulu menjadi satu baris per order. `order_value_cents` hanya tersedia bila seluruh harga item valid; tanpa item nilainya null dan item_count nol. Satu harga invalid membatalkan seluruh nilai order untuk sales/RFM tanpa menghapus transaksi atau membuat nilai parsial. Freight tidak menjadi syarat penjualan barang.
- Join: enam left join tervalidasi (`many_to_one` atau `one_to_one`) meliputi order→customer, order→agregat item, order→review terpilih, item→order/customer, item→product, serta item→translation. Setiap join melaporkan baris, pesanan unik, nilai uang, kunci kosong/tidak cocok, dan baris kanan yang tidak terpakai. Tidak ada join pembayaran mentah.
- Hasil aktual: order-level tetap 99.441 baris dan item-level tetap 112.650 baris; kunci unik pada satuan masing-masing, seluruh status dipertahankan. Sebanyak 775 order tanpa item diberi item_count 0 dan order_value null; 768 order tanpa review tetap dipertahankan. Semua order→customer dan item→order/product cocok. Join kategori mempunyai 1.603 item berkode kosong dan 24 item berkode nonkosong tanpa terjemahan; label/fallback mempertahankan cakupan nilai barang.
- Eligibility (satuan pesanan): sales 96.211, delivery 96.203, comparison 95.560, RFM 96.211. Filter periode mengecualikan 349 order; sesudahnya 2.881 order bukan delivered. Dari 96.211 delivered dalam periode, delapan tidak memiliki pasangan tanggal valid; dari 96.203 eligible delivery, 643 tidak memiliki skor review valid. Tidak ada pengurangan sales→RFM karena identitas pada data asli. Nilai yang sama untuk sales/RFM tidak mengubah definisi eligibility yang terpisah.
- Rekonsiliasi: populasi eligible sales memuat 109.880 item dari 96.211 order. Jumlah price item dan order_value keduanya 1.318.102.713 sen BRL; seluruh item sebelum/sesudah join tetap 1.359.164.370 sen price dan 225.190.954 sen freight. Tidak ada penggandaan nilai atau order akibat ulasan/kategori. Kelengkapan nilai order dan cakupan metrik tidak disatukan menjadi satu filter universal.
- Kontrak: `src/data_contracts.py` memvalidasi nama, tipe, nullability, dan primary key; data dictionary mencatat satuan, arti null, asal/definisi setiap kolom, tipe aktual, serta jumlah null. Tanggal pembelian memiliki `purchase_date` kalender dan `purchase_month` YYYY-MM. Label is_late/days_late tetap nullable bila tanggal tidak dapat dievaluasi; Q2 harus memakai denominator order-level.
- Verifikasi aktual, exit 0: `.venv/bin/python -m pytest tests/test_pipeline.py -q` (51 passed: 31 P03 + 20 P04); `.venv/bin/python scripts/check_integration.py` dari root; executable dan skrip berpath absolut dari `/tmp` (cwd `/private/tmp`). Dua build pada setiap eksekusi menghasilkan tabel dan audit identik. Referensi independen berbasis csv/datetime/Decimal/dict mencocokkan 1.690.497 nilai field pada seluruh 99.441 order dan memeriksa seluruh 112.650 item, kategori, eligibility, total uang, serta distribusi status. Pemeriksaan akhir memvalidasi hash audit/dictionary, kontrak tipe/nullability, dan `git diff --check`; sembilan CSV dan templat tetap utuh.
- Kasus berisiko: beberapa item dan review tidak memperbanyak nilai order; tanpa item/review/tanggal tidak memakai satu filter bersama; harga invalid membatalkan seluruh item order; freight invalid tidak membatalkan price valid; customer/product/orphan item tidak cocok tetap dipertahankan dan diberi flag; batas tanggal inklusif/eksklusif dan status snapshot diterapkan; kunci dimensi/review duplikat memblokir join; overflow Int64 order dihentikan.
- Perbaikan dependency P03: tiga tes awal P04 gagal pada validasi kunci tabel kosong akibat pandas/Arrow menganggap hasil apply kosong tetap string. `_require_unique` diperbaiki menjadi pemeriksaan boolean per kolom tanpa mengubah ekspektasi. Seluruh 51 tes kemudian lulus. `scripts/check_cleaning.py` dijalankan ulang dari root, exit 0; audit sumber, issue impacts, schema, gate, serta hash sumber P03 dibandingkan dengan versi Git sebelumnya dan identik. Audit/verifikasi P03 diperbarui dengan timestamp dan bukti regresi; tidak ada pemeriksaan ulang tertunda.
- Gate: lulus. Seluruh kontrak, kardinalitas, pelestarian baris/nilai, eligibility independen, dan rekonsiliasi eligible item–order memiliki bukti aktual. DQ13/DQ14 ditangani pada kontrak; DQ15 didokumentasikan sebagai sumber pendukung tidak dipakai. Tidak ada hambatan P04.
- Handoff P05: gunakan `tables, audit = build_analysis_tables()` atau berikan hasil `clean_primary_sources()` yang sudah ada. Q1 memakai item_level eligible_sales, termasuk kategori Tidak diketahui dalam denominator; top 5 hanya kategori diketahui. Q2 memakai order_level eligible_delivery/eligible_review_comparison dan menampilkan denominator yang sesuai. Periode/status/metrik berasal dari config dan flag P04. Jangan menjumlahkan order kategori untuk menggantikan order global; jangan menghitung Q2 dari baris item.
- Langkah berikutnya: P05 — Agregasi Q1 dan Q2. P05 belum dimulai; belum ada hasil analisis bisnis, RFM pelanggan, notebook, atau dashboard.

### P05 — Agregasi Q1 dan Q2

- Mulai: 2026-10-24T09:59:22+07:00.
- Verifikasi akhir: 2026-10-24T10:04:58+07:00. Status: `completed`.
- Prasyarat: perubahan kerja P04 yang belum di-commit dipertahankan; plan/tracker dan kontrak P04 dibaca; tidak ditemukan AGENTS.md pada workspace/ancestor/subdirektori yang diedit. Hash audit join, dictionary, serta dependency cleaning cocok dengan bukti P04. Builder dijalankan ulang dan audit agregasi/join/eligibility/rekonsiliasi/coverage/kontrak sama dengan P04; tidak ada perubahan pipeline atau sumber pada P05.
- Keluaran: `src/analytics.py` (`filter_sales`, `analyze_q1`, `analyze_q2`), `tests/test_analytics.py`, `scripts/check_analytics.py`, `reports/analytical_results.json`, `reports/analytics_validation.json`, dan README. Laporan menyimpan hasil default lengkap, metadata filter, denominator/cakupan, tabel kategori/seri bulanan, perbandingan ulasan, seluruh wilayah/peringkat, serta ringkasan enam skenario filter.
- Kontrak filter: batas kalender half-open start/end_exclusive diiris dengan periode config; batas di luar periode tidak menciptakan bulan tambahan. `states=None` mencakup seluruh wilayah, `[]` menghasilkan filter kosong. Rentang terbalik/timestamp berwaktu/timezone dan kode kosong ditolak. Persentase tanpa denominator menjadi unavailable (None/Float64 nullable/JSON null), bukan nol.
- Q1: 96.211 order eligible sales, 109.880 item, dan nilai barang 1.318.102.713 sen BRL sesuai P04. Seluruh 74 kategori termasuk Tidak diketahui masuk denominator dan kontribusi berjumlah 100%. Lima kategori diketahui dipilih sekali per filter dengan tie-break kode kategori: health_beauty 122.955.750 sen (9,328237%); watches_gifts 116.346.591 (8,826823%); bed_bath_table 102.295.577 (7,760820%); sports_leisure 95.284.040 (7,228878%); computers_accessories 88.805.559 (6,737378%). Total top lima 525.687.517 sen, kontribusi 39,882136%. Angka persentase pada log dibulatkan; presisi perhitungan tersimpan dalam JSON.
- Kategori tidak diketahui: 17.066.074 sen, kontribusi 1,294745%; tetap masuk total dan tidak dipilih menjadi rekomendasi top lima. Pesanan lintas kategori dihitung unik pada tiap kategori, sehingga jumlah order kategori tidak dipakai menggantikan order global.
- Seri Q1: 20 bulan kalender (Januari 2017–Agustus 2018), 100 titik kategori/bulan untuk lima kategori tetap. Filter parsial mencatat window_start/end_exclusive dan is_partial_month. Bulan tanpa transaksi di dalam irisan diberi nol teramati, dengan catatan bahwa ini bukan bukti kelengkapan pencatatan sumber. Bulan di luar periode tidak diisi nol.
- Q2 coverage: 99.092 order dalam filter utama, 96.211 delivered; 96.203 dapat dievaluasi pengirimannya (8 tidak tersedia). Sebanyak 6.531 terlambat, 89.672 tepat waktu; tingkat keterlambatan 6,788770%. Comparison memakai 95.560 order dengan tanggal/skor valid; 643 order eligible delivery tidak memiliki review valid.
- Q2 perbandingan: kelompok terlambat memakai n=6.378 (3.980 skor 1–2), proporsi 62,402007%, mean score 2,270931. Tepat waktu memakai n=89.182 (8.248 skor 1–2), proporsi 9,248503%, mean score 4,291045. Selisih = 53,153504 persentase poin. Denominator delivery dan comparison berbeda dan dilaporkan eksplisit; hubungan ini tidak membuktikan bahwa keterlambatan menyebabkan skor rendah.
- Q2 wilayah: seluruh 27 state ditampilkan. Sebanyak 26 memenuhi minimal 50 eligible review comparison; RR dengan n=40 tetap terlihat tetapi tidak diperingkat. Prioritas menurut lateness desc, bad-review proportion desc, comparison n desc, lalu kode state asc: lima teratas AL, MA, SE, PI, CE. Lateness masing-masing 21,464646%; 17,531557%; 15,361446%; 13,894737%; 13,825609%. Ini aturan prioritas investigasi operasional. Skor ulasan buruk dan ukuran sampel state lengkap tersedia dalam JSON.
- Verifikasi aktual, exit 0: `.venv/bin/python -m pytest tests/test_analytics.py tests/test_pipeline.py -q` (73 passed: 22 P05 + 51 pipeline/regresi). Fixture tie-break peringkat kemudian disederhanakan dengan data yang sama dan tes terarah kembali lulus. Kasus mencakup order lintas kategori, kategori tidak diketahui, top lima tetap, tie kode, kalender/parsial/batas periode, filter kosong, total nilai nol, tidak ada review, salah denominator, selisih persentase poin, kelompok pembanding kosong, threshold 49/50, delivery n besar tetapi comparison <50, missing state, dan input dengan grain salah.
- Verifikasi dataset: `.venv/bin/python scripts/check_analytics.py` dari root dan executable/skrip absolut dari `/tmp` (cwd `/private/tmp`), keduanya exit 0. Enam skenario default, SP, RR Januari 2017, rentang parsial SP/RJ, states kosong, dan tanggal di luar periode dicocokkan ke oracle independen csv/datetime/Decimal/dict (termasuk kategori, top lima, bulanan, coverage/perbandingan, mean review, dan urutan wilayah). RR Januari menghasilkan filter kosong; kasus sampel kecil positif pada data asli terlihat pada RR default n=40, serta diuji secara eksplisit pada fixture 49/50. Agregasi diulang dan seluruh hasil identik. Total Q1/coverage Q2 cocok P04; sembilan hash CSV dan templat tidak berubah. Hash hasil, jumlah kategori/bulan/state, null pada denominator kosong, dan `git diff --check` diperiksa pada penutupan phase.
- Gate: lulus. Hasil dapat ditelusuri ke baris dan referensi mentah, filter/denominator/cakupan eksplisit, serta unavailable tidak dipaksa menjadi nol. Tidak ada hambatan P05 tersisa.
- Handoff P06: gunakan order_level eligible_rfm dari `build_analysis_tables()`; bangun RFM per customer_unique_id dengan snapshot/aturan config. Tambahkan Q3 ke `reports/analytical_results.json` sambil mempertahankan hasil Q1/Q2. Monetary/frequency RFM harus direkonsiliasi ke order eligible RFM, dan ambang nilai tinggi dihitung dari populasi acuan penuh sekali. Jika upstream berubah, perbarui P05/P06 yang terdampak sebelum notebook/ekspor.
- Langkah berikutnya: P06 — RFM dan segmentasi Q3. P06 belum dimulai; belum ada segmentasi pelanggan, visualisasi/notebook P07, dashboard, atau deployment.
