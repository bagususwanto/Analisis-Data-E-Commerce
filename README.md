# Analisis Data E-Commerce

Proyek analisis dataset E-Commerce untuk submission Dicoding. Pemilik: **Bagus Uswanto**, ID Dicoding **DS013B6Y0318**.

Saat ini tersedia inventaris sumber (P00), fondasi (P01), assessment (P02), cleaning (P03), integrasi/kontrak data (P04), serta agregasi penjualan dan pengiriman/ulasan Q1–Q2 (P05). RFM/Q3, notebook, dan dashboard mengikuti phase berikutnya pada [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). Status aktual dicatat di [EXECUTION_STATUS.md](EXECUTION_STATUS.md).

## Setup lingkungan

Lingkungan P01 menggunakan **Python 3.12.13** dan `.venv` lokal. Dari folder proyek, jalankan:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip check
python scripts/check_foundation.py
```

Pada mesin ini, executable Python 3.12 tersedia di `/Users/bagus/.local/share/uv/python/cpython-3.12.13-macos-aarch64-none/bin/python3.12`. Jika `python3.12` belum ada di PATH, gunakan path tersebut untuk perintah pembuatan environment. Instalasi dependensi P01 menggunakan `uv --cache-dir /tmp/ecommerce-uv-cache pip install --python .venv/bin/python -r requirements-dev.txt`; perintah pip di atas merupakan alternatif setup dengan berkas dependensi yang sama.

`requirements-dev.txt` menyertakan `requirements.txt`, kernel notebook, nbconvert, nbformat, dan pytest. Versi langsung dipin berdasarkan instalasi P01; validasi clean install dan pin final dilakukan P10. Gunakan `.venv/bin/python` secara langsung bila tidak mengaktifkan environment. Jangan sertakan `.venv` dalam paket submission.

## Memuat sumber mentah

Jalankan dari root proyek dengan Python environment:

```python
from src.config import ANALYSIS_START, ANALYSIS_END_EXCLUSIVE
from src.data_pipeline import load_source

orders = load_source("orders_dataset")
print(orders.shape)
```

Nama sumber memakai nama file tanpa `.csv`. Daftar kolom wajib dan sumber utama/pendukung tersedia di `src/config.py`. Loader membaca semua kolom sebagai pandas `StringDtype`: ID dan kode pos tetap berupa teks, sementara uang dan tanggal belum dikonversi. Field kosong menjadi `pd.NA`; teks hanya whitespace dan literal seperti `NA` dipertahankan agar penanganannya dapat diaudit pada assessment/cleaning. Loader tidak mengubah sumber atau menghapus baris.

Path data berasal dari lokasi modul (`__file__`), sehingga tidak mengikuti current working directory. Argumen opsional `data_dir` menerima direktori absolut; direktori relatif dihitung dari root proyek. File atau kolom wajib yang hilang menghasilkan pesan error yang menyebut sumber terkait.

Skrip pemeriksaan dapat dipanggil dari direktori lain dengan path absolut ke `.venv/bin/python` dan `scripts/check_foundation.py`. Skrip menemukan root melalui `__file__`, memeriksa loader beserta kasus file/kolom hilang dan pelestarian nilai mentah, lalu membandingkan checksum sembilan CSV dengan baseline. Bukti terakhir ditulis ke `reports/foundation_validation.json`; skrip berhenti dengan error jika sumber berubah.

## Menjalankan assessment P02

```bash
.venv/bin/python scripts/assess_data.py
```

Skrip memuat enam sumber utama melalui loader dan membuat profil ringkas tiga sumber pendukung. Hasilnya mencakup nilai kosong menurut kolom/status, keunikan kunci, duplikasi persis dan ulasan berulang, parsing tanggal/numerik, presisi uang, kronologi, serta foreign key. Uang diperiksa melalui `Decimal` dari teks sumber agar presisi sen tidak bergantung pada floating point.

Laporan lengkap dan rencana tindakan per `issue_id` tersimpan pada [reports/data_quality.json](reports/data_quality.json). Tabel Gathering, Assessing, dan Steps to Take untuk bahan notebook tersedia pada [reports/assessment_summary.md](reports/assessment_summary.md). Profil ditambahkan ke baseline dengan tetap mempertahankan hash dan riwayat P00. Hash sembilan CSV dan templat diperiksa sebelum/sesudah proses; sumber yang berubah menyebabkan skrip berhenti. Entry point juga dapat dipanggil melalui path absolut dari direktori lain.

P02 hanya menilai sumber dan mendokumentasikan tindakan. Seleksi ulasan dan transformasi cleaning dikerjakan di P03; tabel analisis dan flag eligibility dibentuk di P04. Jumlah masalah dapat tumpang tindih, sehingga tidak boleh dijumlahkan sebagai total transaksi bermasalah.

## Menjalankan cleaning P03

```bash
.venv/bin/python -m pytest tests/test_pipeline.py -q
.venv/bin/python scripts/check_cleaning.py
```

Fungsi cleaning tersedia pada `src/data_pipeline.py`; setiap fungsi mengembalikan `(tabel, audit)`. Untuk memakainya dari notebook atau phase berikutnya:

```python
from src.data_pipeline import clean_primary_sources

tables, audits = clean_primary_sources()
orders = tables["orders_dataset"]
selected_reviews = tables["order_reviews_dataset"]
```

Cleaning dimulai dari enam sumber mentah dan memakai salinan data. Hasil tidak memfilter status atau periode. Kolom tanggal dikonversi dengan salinan `*_raw`, serta flag missing, gagal parsing, dan valid. `is_late` menggunakan tanggal kalender; `days_late` berupa integer nullable. Pasangan tanggal yang tidak dapat dievaluasi tetap menghasilkan nilai kosong. Inversi waktu approval/kurir dicatat tanpa menebak tanggal pengganti. Estimasi sebelum tanggal pembelian diberi flag dan tidak menghasilkan label keterlambatan.

Uang disimpan dalam `price_cents` dan `freight_cents` (`Int64`) melalui representasi Decimal dan rasio integer yang tepat. Nilai nol dipertahankan; nilai negatif/non-numerik menjadi tidak tersedia dengan alasan kualitas. Presisi di luar sen menghentikan proses melalui `MoneyPrecisionError`; tidak ada pembulatan diam-diam. ID dan kode pos tetap string.

Produk memiliki `category_code`, `category_name`, `category_missing`, dan `category_translation_missing`. Label kategori kosong dibedakan dari fallback kode kategori yang belum diterjemahkan. Atribut produk opsional tetap nullable. Duplikasi persis dibuang dengan jejak ordinal sumber, sedangkan konflik kunci berbeda isi menghentikan proses untuk diinspeksi.

Ulasan dipilih satu per pesanan dengan urutan creation terbaru, answer terbaru, review ID leksikografis terbesar, lalu ordinal sumber terbesar; tanggal kosong ditempatkan sebelum tanggal valid. Validasi skor dilakukan sesudah pemilihan. Kolom `source_row_number` adalah urutan data record mulai 1 sebelum deduplikasi, bukan nomor baris fisik CSV. `review_candidate_count` menghitung kandidat setelah duplikasi persis dihapus. Review ID yang sama pada pesanan berbeda dipertahankan.

Skrip pemeriksaan menjalankan cleaning dua kali untuk membuktikan hasil deterministik, memeriksa kunci dan label nullable, serta merekonsiliasi pemenang review dengan pembacaan CSV independen dan total uang dengan Decimal. Sembilan hash CSV dan hash templat diperiksa sebelum/sesudah. Keluaran berupa [audit cleaning](reports/cleaning_audit.json), [jejak kandidat review](reports/review_selection.csv), dan [laporan verifikasi](reports/cleaning_validation.json). Audit mencakup sebelum/sesudah seluruh issue P02, termasuk kondisi yang sengaja dipertahankan dan pekerjaan eligibility yang menjadi milik P04. CSV tabel analisis/dashboard belum diekspor pada tahap ini.

## Menjalankan integrasi P04

```bash
.venv/bin/python -m pytest tests/test_pipeline.py -q
.venv/bin/python scripts/check_integration.py
```

Gunakan API yang sama untuk notebook, analisis, dan ekspor berikutnya:

```python
from src.data_pipeline import build_analysis_tables

tables, join_audit = build_analysis_tables()
order_level = tables["order_level"]
item_level = tables["item_level"]
```

Jika hasil cleaning sudah ada, `build_analysis_tables(cleaned_tables)` memakainya tanpa membaca ulang sumber. Fungsi mengembalikan tabel dalam memori; ekspor CSV dashboard dilakukan pada P08.

`order_level` mempunyai satu baris per pesanan, sedangkan `item_level` mempunyai satu baris per pasangan `order_id`/`order_item_id`. Item diagregasi per order sebelum digabung dengan pelanggan dan satu review terpilih. Enam left join memakai validasi kardinalitas pandas, melaporkan referensi yang tidak cocok pada kedua sisi, dan memeriksa jumlah baris, pesanan unik, serta nilai uang. Pembayaran tidak digunakan.

`order_value_cents` kosong jika pesanan tidak memiliki item atau sedikitnya satu harganya invalid. `item_count` tetap nol untuk pesanan tanpa item. Satu harga invalid mengecualikan seluruh item pesanan dari penjualan; nilai barang tidak dihitung sebagian. Produk/kategori yang tidak cocok dipertahankan sebagai kategori Tidak diketahui dengan flag, sehingga nilai barang tetap tercakup dalam denominator penjualan.

Eligibility order dibentuk sesuai konfigurasi periode dan status delivered: `eligible_sales` memerlukan seluruh harga item valid; `eligible_delivery` memerlukan tanggal delivery valid; `eligible_review_comparison` menambahkan skor review terpilih valid; `eligible_rfm` menambahkan identitas pelanggan lintas pesanan yang valid pada eligible sales. Harga, review, dan tanggal memiliki cakupan tersendiri. Pelanggan yang tidak cocok dapat tetap tercakup dalam nilai penjualan global, sedangkan RFM memerlukan identitas valid. Item mewarisi `eligible_sales` seluruh order; gunakan `order_level` untuk denominator Q2.

Kontrak nama/tipe/satuan/arti null/asal kolom tersedia pada `src/data_contracts.py` dan [data dictionary](reports/data_dictionary.json). [Audit join](reports/join_audit.json) memuat agregasi, cakupan join, jumlah eligible, alasan pengecualian yang tumpang tindih maupun saling eksklusif, serta rekonsiliasi item–order. [Laporan verifikasi](reports/integration_validation.json) mencatat pencocokan dengan pembacaan CSV independen dan determinisme hasil. Entry point dapat dijalankan dari direktori lain dengan path absolut. Seluruh status dan transaksi sumber tetap dipertahankan dalam keluaran integrasi.

## Menjalankan agregasi Q1–Q2 (P05)

```bash
.venv/bin/python -m pytest tests/test_analytics.py tests/test_pipeline.py -q
.venv/bin/python scripts/check_analytics.py
```

```python
from src.analytics import analyze_q1, analyze_q2
from src.data_pipeline import build_analysis_tables

tables, audit = build_analysis_tables()
q1 = analyze_q1(tables["item_level"])
q2 = analyze_q2(tables["order_level"])

# Tanggal akhir eksklusif; contoh mencakup Februari 2018 di SP/RJ.
q1_filtered = analyze_q1(
    tables["item_level"], start="2018-02-01", end_exclusive="2018-03-01", states=["SP", "RJ"]
)
```

Fungsi pada `src/analytics.py` mengembalikan summary, metadata filter, dan DataFrame agregat untuk notebook/dashboard. Rentang filter diiris dengan periode utama di config; batas berupa tanggal kalender tanpa waktu/timezone. `states=None` berarti seluruh wilayah termasuk yang belum diketahui, sedangkan `states=[]` menghasilkan filter kosong. Rentang terbalik ditolak. Persentase/selisih yang tidak memiliki denominator tersedia sebagai `None` atau nullable Float64, dan menjadi JSON null pada laporan.

Q1 menghasilkan kategori, top lima, kalender bulan, serta seri bulanan kategori yang sama sepanjang filter aktif. Nilai barang memakai integer sen; kategori Tidak diketahui tetap masuk denominator tetapi tidak masuk top lima. Tie-break memakai kode kategori. Bulan tanpa transaksi dalam irisan filter diisi nol; bulan di luar periode tidak ditambahkan. Bulan parsial diberi penanda dan rentang tanggalnya. Nol teramati tidak membuktikan kelengkapan pencatatan.

Q2 menghasilkan coverage delivered/delivery/review, perbandingan terlambat–tepat waktu (dengan n masing-masing), dan tabel seluruh wilayah. Tingkat keterlambatan memakai eligible delivery; proporsi ulasan buruk memakai eligible review comparison. Selisih dinyatakan dalam persentase poin. Wilayah dengan minimal 50 order comparison diperingkat menurut keterlambatan, ulasan buruk, ukuran sampel (semuanya menurun), lalu kode state menaik. Kelompok kecil tetap ditampilkan; wilayah tidak diketahui tidak diperingkat. Ini aturan prioritas investigasi dan tidak membuktikan sebab-akibat.

[Hasil numerik Q1–Q2](reports/analytical_results.json) mencakup seluruh kategori, 20 bulan periode utama, perbandingan ulasan, peringkat wilayah, dan summary enam skenario filter. [Laporan verifikasi](reports/analytics_validation.json) memuat referensi independen berbasis CSV/datetime/Decimal, pencocokan dengan P04, determinisme, serta hash sumber. Visualisasi dan narasi akhir dikerjakan P07; hasil RFM/Q3 menjadi milik P06.

## Konfigurasi dan sumber

`src/config.py` mendefinisikan periode utama 1 Januari 2017 hingga sebelum 1 September 2018, tanggal acuan RFM 1 September 2018, status delivered, ambang recency 30/90 hari, minimum sampel wilayah 50, serta aturan kategori dan persentil monetary. Konfigurasi ini baru mendefinisikan parameter; loader belum menerapkan filter atau menghitung metrik.

Enam sumber utama di `data/` adalah orders, customers, order items, products, order reviews, dan terjemahan kategori. Payments, sellers, dan geolocation merupakan sumber pendukung. CSV lokal dipertahankan; ukuran, jumlah baris, dan SHA-256 tersimpan di `reports/baseline.json`.

Templat notebook resmi tersimpan di `references/notebook_template.ipynb`; sumbernya adalah [templat Dicoding di Colab](https://colab.research.google.com/drive/144WFnMMqvTAnGG-Qj5pUuVAYtCHGJbcp?usp=sharing). Provenance dan hash tercatat di baseline. Analisis mengikuti [instruksi submission Dicoding](https://www.dicoding.com/academies/555/tutorials/31230/submission-guidance).
