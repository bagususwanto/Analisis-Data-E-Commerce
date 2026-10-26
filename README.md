# Analisis Data E-Commerce

Analisis dataset E-Commerce Olist untuk menjawab tiga kebutuhan: memilih kategori prioritas, menyelidiki hubungan keterlambatan dengan ulasan buruk, dan menentukan kandidat pilot retensi melalui RFM tanpa machine learning.

**Pemilik:** Bagus Uswanto · **Email:** DS013B6Y0318@student.devacademy.id · **ID Dicoding:** DS013B6Y0318.

Periode pembelian utama **1 Januari 2017–31 Agustus 2018**, status **delivered** pada snapshot dataset, mata uang **BRL**. Notebook berisi proses Gathering–Assessing–Cleaning–EDA, visualisasi, kesimpulan, dan rekomendasi. Dashboard menyediakan tiga tab dengan filter interaktif. Riwayat pekerjaan dan status deployment/pengemasan terdapat pada [EXECUTION_STATUS.md](EXECUTION_STATUS.md).

## Mulai menjalankan dashboard

Gunakan **Python 3.12.13**. Dari root proyek:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip check
python -m streamlit run dashboard/dashboard.py
```

Windows PowerShell: gunakan `py -3.12 -m venv .venv`, lalu `.venv\Scripts\Activate.ps1` untuk aktivasi. Sesudah aktivasi, perintah `python` sama. P10 menguji macOS ARM64; Windows/Linux belum diuji langsung. Runtime cloud harus diuji lagi saat deployment.

Jika hanya menjalankan aplikasi, cukup instal `requirements.txt`. `requirements-dev.txt` menyertakan runtime, kernel/eksekusi notebook, pembaca render, dan pytest. Semua dependensi langsung dipin; daftar lengkap paket dari lingkungan bersih dicatat pada `reports/reproducibility_validation.json`.

Alternatif instalasi dengan **uv** pada environment yang sudah dibuat:

```bash
uv pip install --python .venv/bin/python -r requirements-dev.txt
```

P10 menguji instalasi ke virtual environment baru menggunakan uv dengan opsi `--offline` dan cache paket lokal. Paket tetap dipilih dari requirements yang sama. Instalasi lewat jaringan baru, platform lain, dan ketersediaan indeks paket merupakan kondisi lingkungan yang berbeda. Folder `.venv`, cache, dan keluaran `dist/` tidak disertakan dalam submission.

Dashboard membaca tiga CSV yang sudah disiapkan beserta metadata. Aplikasi tidak memerlukan sumber mentah/notebook/reports pada runtime. Jika input hilang, checksum berubah, atau schema tidak sesuai, aplikasi menampilkan instruksi regenerasi dari root proyek:

```bash
python scripts/prepare_dashboard_data.py
```

## Struktur dan berkas yang dibutuhkan

```text
.
├── data/                         # 9 CSV sumber lokal; tidak diubah
├── notebook.ipynb                # Analisis dengan output eksekusi tersimpan
├── src/                          # Konfigurasi, pipeline, analytics, grafik, reader
├── dashboard/
│   ├── dashboard.py              # Entry point Streamlit
│   ├── order_level.csv           # 99.441 pesanan, seluruh status
│   ├── item_level.csv            # 112.650 pasangan order/item
│   ├── rfm_customers.csv         # 93.104 pelanggan unik
│   └── data_metadata.json        # Schema, provenance, parameter, baseline
├── scripts/                      # Regenerasi dan pemeriksaan
├── tests/                        # Kasus berisiko, widget, dan gate validasi
├── reports/                      # Audit, hasil, HTML, figure, bukti verifikasi
├── references/notebook_template.ipynb
├── requirements.txt
├── requirements-dev.txt
├── IMPLEMENTATION_PLAN.md
└── EXECUTION_STATUS.md
```

Untuk notebook/validasi lengkap, pertahankan sumber `data/`, `src/`, `scripts/`, `tests/`, `references/`, dan laporan pendukung dalam `reports/`. Jangan memindahkan notebook sendirian: kode dan audit lokal merupakan dependensinya. Semua skrip menemukan root melalui lokasi file dan dapat dipanggil dari direktori lain dengan path absolut. Kernel notebook dijalankan dari root proyek atau subdirektorinya.

Sumber utama adalah orders, customers, order items, products, order reviews, dan terjemahan kategori. Payments, sellers, serta geolocation hanya dinilai sebagai sumber pendukung dan tidak dimasukkan ke metrik Q1–Q3. Inventaris sembilan CSV, jumlah baris, dan SHA-256 ada di [baseline](reports/baseline.json). Dataset tidak diunduh ulang saat menjalankan analisis.

## Reproduksi dan verifikasi lengkap

Jalankan dengan environment aktif, dari root proyek:

```bash
python scripts/prepare_dashboard_data.py
python scripts/validate_outputs.py
python -m pytest -q
python scripts/check_notebook.py
```

`check_notebook.py` membersihkan output lama dan menjalankan **21 code cell** pada kernel Python baru dari executable yang sama dengan runner. Runner memerlukan koneksi lokal Jupyter. Output disimpan pada notebook, HTML dengan gambar tertanam pada `reports/notebook.html`, dan enam PNG V01–V06 pada `reports/figures/`. Generator `scripts/build_notebook.py` hanya diperlukan ketika ingin membentuk ulang isi notebook dari templat, bukan setiap kali menjalankan analisis.

Setiap eksekusi menandai review visual sebagai **pending**. Buka keenam PNG atau HTML dan periksa label panjang, angka, satuan, skala, warna, legenda, margin, denominator dan konteks. Setelah pemeriksaan tersebut benar-benar dilakukan, catat nama pemeriksa serta catatan temuan, misalnya:

```bash
python scripts/record_notebook_review.py --reviewer 'Pemeriksa lokal' --notes 'V01–V06 dibuka; label, unit, skala, n/denominator, legenda, dan margin sudah diperiksa.'
python scripts/prepare_dashboard_data.py
python scripts/validate_outputs.py
python -m streamlit run dashboard/dashboard.py
```

Perintah pencatatan hanya menyimpan review dan mengikatnya ke hash notebook/HTML/PNG; perintah tersebut tidak memeriksa gambar secara otomatis. Sesuaikan nama dan catatan dengan pemeriksaan yang dilakukan. Ekspor diulang setelah notebook selesai ditinjau agar hash provenance merujuk versi terbaru. Jika ekspor belum mengikuti notebook/review baru, validator sengaja gagal dengan pesan **Provenance usang**. Ekspor membaca sumber, melakukan round-trip tipe/sel, dan membandingkan dua ekspor dengan urutan input diacak.

`validate_outputs.py` berhenti dengan **exit code 1** bila ada ketidaksesuaian, lalu menyimpan rincian pada [validation_results.json](reports/validation_results.json). Pemeriksa mencakup:

- Hash sembilan sumber/templat; schema, tipe, null, kunci dan metadata bundle.
- Pembangunan ulang pipeline dari sumber dan pencocokan setiap sel/tipe CSV.
- Referensi independen berbasis CSV, Decimal, datetime, dan dictionary untuk order/item, Q1–Q2, serta seluruh pelanggan RFM.
- Rekonsiliasi nilai barang item–order, cakupan eligibility, frequency/monetary RFM, 12 skenario filter, dan ambang global.
- Payload Q1–Q3 yang benar-benar dikeluarkan kernel notebook, laporan analitis, metadata, serta KPI/tabel kategori, kelompok ulasan dan segmen pada dashboard default melalui AppTest.
- Kelengkapan identitas, placeholder templat, hash notebook/HTML/enam figure, dan status review visual.

Jangan menjalankan pemeriksa dengan `python -O`, karena referensi independen memakai assertion. `scripts/check_dashboard.py` menyediakan tes regresi/UI tambahan dan laporan `reports/dashboard_validation.json`; pemeriksaan browser nyata tetap diperlukan untuk layout/interaksi. Alur P10 serta versi dan hasil perintah lingkungan bersih dicatat pada `reports/reproducibility_validation.json`. Pemeriksaan P02–P06 yang lebih terperinci tetap tersedia pada skrip `assess_data.py`, `check_cleaning.py`, `check_integration.py`, `check_analytics.py`, dan `check_rfm.py`; jika laporan analitis diregenerasi, lanjutkan urutan dependensi P05 → P06 → notebook/review → ekspor → validasi agar provenance tetap konsisten.

## Cara membaca dashboard

**Penjualan** dan **Pengiriman & Ulasan** menggunakan filter tanggal pembelian dan negara bagian pelanggan yang sama. Tanggal akhir inklusif diterapkan melalui batas eksklusif hari berikutnya; satu tanggal berarti satu hari penuh. Opsi **Semua wilayah** mencakup wilayah tidak diketahui. Hapus opsi ini sebelum memilih kode wilayah tertentu; pilihan kosong berarti tidak ada wilayah. Top kategori serta ringkasan mengikuti filter aktif. Grafik dapat diperbesar dengan Fullscreen dan tabel rincian digeser mendatar.

**Pelanggan RFM** mempunyai filter **Segmen pelanggan** dan **Wilayah pesanan terakhir**. Kontrol transaksi tidak mengubah jendela observasi RFM atau tanggal acuan **1 September 2018**. Negara bagian mengikuti pesanan eligible terakhir, dengan tie-break timestamp lalu order ID leksikografis terbesar; riwayat pembelian pelanggan di wilayah lain tetap masuk R/F/M. Ambang nilai tinggi dihitung sekali dari populasi global, tidak dihitung ulang oleh filter. Persentase segmen memakai total pelanggan/monetary pada filter aktif.

## Definisi metrik dan kebijakan kualitas

| Metrik | Definisi dan denominator |
| --- | --- |
| Nilai penjualan barang | Jumlah `price` item pada pesanan delivered eligible; tanpa freight. Disimpan dalam integer sen BRL, ditampilkan sebagai BRL. Bukan laba, pendapatan bersih, atau total pembayaran. |
| Pesanan / item | Order ID unik / baris item valid. Pesanan lintas kategori dapat muncul sekali di tiap kategori; jumlah order kategori tidak dijumlahkan menjadi total global. |
| Kontribusi kategori | Nilai kategori / total barang dalam filter yang sama, termasuk kategori Tidak diketahui. Top lima dipilih dari kategori yang diketahui sekali untuk seluruh rentang filter. |
| Keterlambatan | Tanggal kalender penerimaan melewati estimasi, dengan pasangan tanggal valid pada delivered; hari estimasi yang sama berarti tepat waktu. |
| Ulasan buruk | Skor terpilih 1–2 / ulasan integer valid 1–5 pada pengiriman yang dapat dievaluasi. n kelompok terlambat dan tepat waktu ditampilkan terpisah. Selisih dalam persentase poin. |
| Prioritas wilayah | Minimal 50 pesanan eligible review comparison. Urutan: tingkat keterlambatan, ulasan buruk, ukuran sampel menurun, kemudian kode wilayah menaik. Kelompok kecil tetap ditampilkan tanpa peringkat. |
| Recency / frequency / monetary | Hari kalender dari pembelian terakhir ke tanggal acuan / order unik / nilai barang eligible per `customer_unique_id` selama periode utama. |

Item diagregasi per order dan satu ulasan dipilih sebelum join untuk mencegah nilai barang berlipat. Ulasan dipilih menurut creation terbaru, answer terbaru, review ID leksikografis terbesar, lalu ordinal sumber terbesar; tanggal kosong mendahului tanggal valid. Skor diperiksa sesudah seleksi, tanpa kembali ke ulasan lama. Nilai harga invalid mengecualikan seluruh nilai order dari penjualan; order tanpa item tetap null, bukan nilai nol.

Kelayakan metrik dipisahkan: penjualan memerlukan item/harga valid; pengiriman memerlukan pasangan tanggal; perbandingan ulasan menambah syarat skor; RFM menambah identitas pelanggan valid pada penjualan. Missing date/ulasan tidak diubah menjadi tepat waktu atau skor baik. Persentase tanpa denominator menjadi **Tidak tersedia**. Kategori kosong diberi label eksplisit, sementara kode tanpa terjemahan memakai kode aslinya. Masalah, tindakan dan cakupan terukur ada pada [kualitas data](reports/data_quality.json), [audit cleaning](reports/cleaning_audit.json), [audit join](reports/join_audit.json), dan [dictionary](reports/data_dictionary.json).

CSV dashboard memakai UTF-8, ID string, uang/skor `Int64` nullable, datetime dan boolean nullable dengan parser eksplisit. Null disimpan sebagai token `\N`; string `False` tidak diparse memakai `astype(bool)`. Schema, grain, sort, hash, profil null/uang, parameter dan asal berkas ada pada [metadata](dashboard/data_metadata.json). Reader menolak file campuran/rusak, parameter usang, serta tipe yang tidak sesuai. Cache Streamlit mengikuti ukuran/waktu perubahan berkas; filter memakai salinan tabel.

## Segmentasi dan batas interpretasi

Lima segmen manual saling eksklusif: pembeli sekali dengan recency ≤30, 31–90, atau >90 hari; pelanggan berulang dengan recency ≤90 atau >90 hari. Atribut nilai tinggi memakai monetary ≥ P75 global dengan interpolasi linear dan rasio integer tepat. Cutoff statistik bisa berupa pecahan sen; ties bisa membuat jumlah bernilai tinggi melebihi 25%.

Periode utama menghindari ekor data 2016/September–Oktober 2018 yang jarang, tetapi tidak membuktikan kelengkapan pencatatan bulan lain. Status delivered berasal dari snapshot, bukan rekonstruksi status pada akhir setiap bulan. Nol tren adalah nol teramati dalam filter. Q2 menunjukkan hubungan, tanpa mengisolasi penyebab ulasan buruk. Ambang 30/90 hari adalah heuristik operasional, bukan prediksi churn; pembeli sekali tidak otomatis churn. Frekuensi pembelian sangat didominasi satu order sehingga tidak dipaksa menjadi kuantil. Monetary tidak mengukur keuntungan.

Rekomendasi notebook berupa pilot katalog/pemasaran pada kategori prioritas, investigasi logistik wilayah, dan pilot retensi pada segmen bernilai tinggi. Pengukuran efektivitas memerlukan periode tindak lanjut/kelompok pembanding dan data biaya tambahan; dataset ini tidak membuktikan hasil pilot. Angka, kategori dan sasaran dalam kesimpulan dihitung dari hasil analisis, tanpa jaminan kenaikan penjualan atau nilai penilaian submission.

## Sumber dan atribusi

- Referensi dataset: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Berkas yang digunakan adalah sembilan CSV lokal yang dicatat dalam baseline; aplikasi tidak mengunduh data saat dijalankan.
- Struktur notebook diadaptasi dari [templat resmi Dicoding](https://colab.research.google.com/drive/144WFnMMqvTAnGG-Qj5pUuVAYtCHGJbcp?usp=sharing). Salinan 37 sel beserta hash dipertahankan di `references/` dan baseline.
- Acuan tugas: [Instruksi Submission Dicoding](https://www.dicoding.com/academies/555/tutorials/31230/submission-guidance). Audit persyaratan yang sudah dicatat tersedia di implementation plan; halaman dapat memerlukan akses kelas.
- [Contoh struktur proyek Dicoding](https://github.com/dicodingacademy/a555-Project-Structure/blob/main/README.md) menjadi referensi susunan berkas. Analisis, narasi, fungsi dan grafik proyek mengikuti dataset serta keputusan kualitas lokal; tidak mengimpor hasil analisis atau identitas dari notebook contoh.

Deployment Community Cloud adalah P11; URL aktif dan `url.txt` baru dibuat setelah deployment berhasil diperiksa. Pengemasan ZIP serta pengujian hasil ekstraksi adalah P12. Kesiapan teknis lokal P10 tidak menyatakan kedua tahap tersebut selesai.
