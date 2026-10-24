# Analisis Data E-Commerce

Proyek analisis dataset E-Commerce untuk submission Dicoding. Pemilik: **Bagus Uswanto**, ID Dicoding **DS013B6Y0318**.

Saat ini tersedia inventaris sumber (P00), konfigurasi bersama, loader mentah, pemeriksaan fondasi (P01), serta assessment formal dan rencana tindakan kualitas data (P02). Cleaning, notebook analisis, dan dashboard mengikuti phase berikutnya pada [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). Status aktual dicatat di [EXECUTION_STATUS.md](EXECUTION_STATUS.md).

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

## Konfigurasi dan sumber

`src/config.py` mendefinisikan periode utama 1 Januari 2017 hingga sebelum 1 September 2018, tanggal acuan RFM 1 September 2018, status delivered, ambang recency 30/90 hari, minimum sampel wilayah 50, serta aturan kategori dan persentil monetary. Konfigurasi ini baru mendefinisikan parameter; loader belum menerapkan filter atau menghitung metrik.

Enam sumber utama di `data/` adalah orders, customers, order items, products, order reviews, dan terjemahan kategori. Payments, sellers, dan geolocation merupakan sumber pendukung. CSV lokal dipertahankan; ukuran, jumlah baris, dan SHA-256 tersimpan di `reports/baseline.json`.

Templat notebook resmi tersimpan di `references/notebook_template.ipynb`; sumbernya adalah [templat Dicoding di Colab](https://colab.research.google.com/drive/144WFnMMqvTAnGG-Qj5pUuVAYtCHGJbcp?usp=sharing). Provenance dan hash tercatat di baseline. Analisis mengikuti [instruksi submission Dicoding](https://www.dicoding.com/academies/555/tutorials/31230/submission-guidance).
