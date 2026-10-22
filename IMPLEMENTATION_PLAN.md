# Implementation Plan — Proyek Analisis Data E-Commerce

Tanggal penyusunan: 21 Oktober 2026  
Pembaruan: 22 Oktober 2026 — versi 2.1, panduan per phase dan audit rubrik bintang 5.  
Status: perencanaan; phase implementasi belum dimulai.  
Pelacakan pekerjaan: [EXECUTION_STATUS.md](EXECUTION_STATUS.md).

Dokumen ini adalah sumber keputusan teknis dan urutan pekerjaan. AI pelaksana harus membaca dokumen ini, `EXECUTION_STATUS.md`, dan instruksi workspace yang berlaku sebelum melakukan perubahan. Eksekusi dimulai dari phase pertama yang belum selesai dan prasyaratnya sudah terpenuhi. Membaca plan atau membuat folder belum cukup untuk menyatakan satu phase selesai.

## 1. Tujuan dan acuan

Membangun proyek analisis E-Commerce dari dataset lokal `data/`, dengan notebook sesuai templat Dicoding dan dashboard Streamlit yang dapat dijalankan ulang. Hasil analisis harus menjawab pertanyaan bisnis, menyertakan bukti visual, dan menghasilkan rekomendasi tindakan yang didukung data.

Acuan utama:

- [Instruksi Submission Dicoding](https://www.dicoding.com/academies/555/tutorials/31230/submission-guidance).
- [Templat notebook wajib](https://colab.research.google.com/drive/144WFnMMqvTAnGG-Qj5pUuVAYtCHGJbcp?usp=sharing).
- [Prinsip-Prinsip dalam Visualisasi Data](https://www.dicoding.com/academies/555/tutorials/31135) dan [Explanatory Analysis](https://www.dicoding.com/academies/555/tutorials/31150).
- [Contoh README](https://github.com/dicodingacademy/a555-Project-Structure/blob/main/README.md) dan [panduan deployment Streamlit](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).

Rencana mencakup empat saran penilaian: dokumentasi setiap tahap, visualisasi yang efektif, analisis lanjutan tanpa machine learning, dan deployment Streamlit Community Cloud. Deployment merupakan tahap akhir setelah aplikasi lolos pemeriksaan lokal. Nilai akhir tetap ditentukan reviewer.

Audit pada 22 Oktober 2026 dilakukan dengan membaca kembali kelima tab halaman instruksi yang dirujuk pengguna. Target bintang 5 memerlukan seluruh kriteria wajib dan seluruh empat saran penilaian diterapkan pada hasil akhir. Paket lokal dapat disiapkan ketika deployment tertunda, tetapi belum memenuhi seluruh saran untuk target maksimum. Checklist khusus target maksimum terdapat pada bagian 10.1.

## 2. Kondisi awal yang sudah diperiksa

Workspace saat ini berisi folder `data/`; belum ada notebook, dashboard, atau kode proyek. Folder ini belum menjadi repositori Git. Pemeriksaan awal dilakukan secara read-only terhadap header, jumlah baris, nilai kosong, kunci, status, dan rentang tanggal CSV.

| Berkas lokal | Baris | Peran dalam proyek |
| --- | ---: | --- |
| `orders_dataset.csv` | 99.441 | Status dan waktu pesanan/pengiriman |
| `customers_dataset.csv` | 99.441 | Identitas pelanggan dan negara bagian |
| `order_items_dataset.csv` | 112.650 | Nilai barang, produk, dan ongkos kirim per item |
| `products_dataset.csv` | 32.951 | Kategori dan atribut produk |
| `order_reviews_dataset.csv` | 99.224 | Skor ulasan per pesanan |
| `product_category_name_translation.csv` | 71 | Terjemahan nama kategori |
| `order_payments_dataset.csv` | 103.886 | Sumber pendukung jika dibutuhkan rekonsiliasi pembayaran |
| `sellers_dataset.csv` | 3.095 | Sumber pendukung jika analisis penjual dikembangkan |
| `geolocation_dataset.csv` | 1.000.163 | Sumber pendukung jika analisis peta dikembangkan |

Enam berkas pertama diperlukan untuk pertanyaan bisnis yang direncanakan. Tiga berkas terakhir tetap tersedia sebagai sumber tambahan; analisis peta dan pembayaran bukan bagian utama rencana ini.

Temuan awal yang harus ditangani atau dijelaskan:

- Rentang pembelian: 4 September 2016–17 Oktober 2018. September dan Oktober 2018 hanya memiliki 16 dan 4 pesanan; periode awal 2016 juga sangat jarang. Periode utama dipilih 1 Januari 2017–31 Agustus 2018 agar tidak menampilkan ekor data yang sangat jarang sebagai tren bisnis normal. Kelengkapan pencatatan bulan tersebut tetap perlu diperiksa; pemilihan periode tidak membuktikan data lengkap.
- Terdapat 96.478 pesanan berstatus `delivered` di seluruh dataset. Analisis penjualan dan RFM menggunakan status ini sebagai definisi populasi utama.
- Tanggal penerimaan pelanggan kosong pada 2.965 pesanan; 8 di antaranya berstatus `delivered`. Pesanan tersebut tetap bisa masuk analisis nilai barang bila datanya valid, tetapi tidak masuk perhitungan keterlambatan.
- `order_approved_at` kosong pada 160 baris dan tanggal pengiriman ke kurir kosong pada 1.783 baris. Penanganannya mempertimbangkan status pesanan; nilai kosong tidak otomatis merupakan kesalahan.
- Sebanyak 610 produk tidak memiliki kategori. Atribut ukuran/berat juga memiliki nilai kosong. Nama kategori yang tidak tersedia diberi label eksplisit `Tidak diketahui`; ukuran produk tidak perlu diimputasi untuk pertanyaan yang tidak memakainya.
- Judul dan pesan ulasan kosong pada 87.658 dan 58.274 baris. Keduanya bersifat opsional dalam rencana ini; ulasan dengan skor valid tetap digunakan.
- Ada 547 pesanan dengan lebih dari satu baris ulasan, serta 814 kemunculan tambahan `review_id` yang berulang. Ini memerlukan pemeriksaan kombinasi kunci dan isi, bukan penghapusan berdasarkan `review_id` saja.
- Ada 2.961 pesanan dengan beberapa baris pembayaran. Penggabungan item, pembayaran, dan ulasan secara langsung berisiko menggandakan nilai penjualan.
- Dari seluruh pelanggan unik dengan pesanan `delivered`, 2.801 dari 93.358 pelanggan memiliki lebih dari satu pesanan, sekitar 3,00%. Persentase ini perlu dihitung ulang untuk periode utama. Distribusi frequency yang didominasi satu pesanan membuat pembagian kuantil frequency kurang cocok.
- `shipping_limit_date` mencapai tahun 2020, sementara rentang pembelian berakhir pada 2018. Ini akan dicatat sebagai anomali yang perlu diperiksa, bukan dianggap perpanjangan periode transaksi.

Dataset mentah dipertahankan. Angka di atas merupakan hasil pemeriksaan awal, belum merupakan insight bisnis akhir.

## 3. Pertanyaan bisnis SMART

Pertanyaan berikut memakai metrik, populasi, dan batas waktu yang jelas. Tujuan tindakannya ditetapkan sejak awal; kesimpulan dan rekomendasi akhir menunggu hasil analisis.

| ID | Pertanyaan | Metrik dan visual utama | Tindakan yang dapat didukung |
| --- | --- | --- | --- |
| Q1 | Selama 1 Januari 2017–31 Agustus 2018, lima kategori produk mana yang menyumbang nilai penjualan barang terbesar pada pesanan delivered, berapa kontribusinya terhadap total, dan bagaimana tren bulanan kelima kategori tersebut? | Jumlah `price`, kontribusi %, item terjual, pesanan unik; bar chart kategori dan line chart bulanan | Menentukan kategori prioritas katalog dan pemasaran berdasarkan kontribusi serta tren |
| Q2 | Untuk pesanan delivered yang dibeli dalam periode tersebut, seberapa berbeda proporsi ulasan buruk pada pengiriman terlambat dan tepat waktu, serta negara bagian pelanggan mana yang perlu diprioritaskan berdasarkan keterlambatan dan ulasan buruk? | Tingkat keterlambatan, proporsi skor 1–2, selisih persentase poin, ukuran sampel; grouped bar chart dan ringkasan negara bagian | Menentukan wilayah untuk pemeriksaan operasional/logistik lebih lanjut |
| Q3 | Dengan tanggal acuan 1 September 2018, bagaimana pelanggan delivered selama periode analisis tersebar menurut recency, frequency, dan monetary, serta segmen mana yang menjadi prioritas retensi atau pembelian ulang? | Hari sejak pembelian terakhir, pesanan unik, nilai barang per pelanggan, jumlah dan kontribusi segmen; distribusi RFM dan bar chart segmen | Merancang pendekatan berbeda untuk pembeli sekali, pelanggan berulang aktif, dan pelanggan berulang yang lama tidak membeli |

Q2 menganalisis hubungan yang teramati. Hasilnya tidak membuktikan bahwa keterlambatan menyebabkan skor ulasan rendah. Identitas pelanggan pada Q3 menggunakan `customer_unique_id` agar pembelian ulang dapat dikenali.

## 4. Definisi metrik dan kebijakan data

### Periode dan populasi

- Filter pembelian utama: `2017-01-01 <= order_purchase_timestamp < 2018-09-01`.
- Nilai penjualan barang dihitung dari pesanan `delivered`. Jumlah semua status tetap diperiksa dalam EDA agar cakupan filter terlihat.
- Status `delivered` adalah status pada snapshot dataset. Dashboard dan notebook menjelaskan bahwa ini bukan rekonstruksi status historis pada setiap akhir bulan.
- Negara bagian merujuk `customer_state`; penentuan wilayah tidak memerlukan tabel geolocation.

### Penjualan

- **Nilai penjualan barang:** jumlah `order_items.price`, dalam BRL. Angka ini bukan laba, pendapatan bersih, atau total pembayaran termasuk ongkos kirim. Simpan nilai turunan dalam integer sen BRL (`*_cents`) supaya rekonsiliasi tidak bergantung pada pembulatan floating point. Konversi dari representasi desimal sumber; bila presisinya melebihi dua desimal, catat dan selesaikan dahulu, jangan membulatkan secara diam-diam.
- **Item terjual:** jumlah baris item yang valid. Tidak ada kolom kuantitas terpisah; `order_item_id` merupakan urutan item dalam pesanan.
- **Pesanan:** `nunique(order_id)`. Pesanan yang memiliki beberapa kategori dapat terhitung sekali pada masing-masing kategori, sehingga jumlah pesanan antar-kategori tidak dijumlahkan untuk memperoleh total global.
- **Kontribusi kategori:** nilai barang kategori dibagi total nilai barang dalam populasi/filter yang sama, termasuk kategori `Tidak diketahui` pada denominator.
- Lima kategori prioritas dipilih dari kategori yang diketahui. Kategori `Tidak diketahui` ditampilkan terpisah untuk memperlihatkan cakupan data, tetap masuk total penjualan dan denominator kontribusi, serta tidak diperlakukan sebagai rekomendasi kategori produk.
- Pertahankan kode kategori asli sebagai kunci. Nama Inggris digunakan bila terjemahan tersedia; kategori yang memiliki kode tetapi belum mempunyai terjemahan memakai nama asli. Ketiadaan terjemahan berbeda dari kategori produk yang kosong.
- Nilai negatif, nilai non-numerik, dan nilai nol diperiksa. Nilai nol tidak otomatis dibuang; nilai besar tidak otomatis dipangkas.

### Pengiriman dan ulasan

- **Keterlambatan:** tanggal kalender penerimaan pelanggan lebih besar daripada tanggal estimasi. Kedua timestamp dinormalisasi ke tanggal terlebih dahulu agar kedatangan pada hari estimasi tidak dianggap terlambat hanya karena estimasi tersimpan pada pukul 00.00.
- **Hari terlambat:** maksimum antara selisih tanggal aktual–estimasi dan nol.
- Denominator tingkat keterlambatan hanya memuat pesanan delivered dengan pasangan tanggal valid. Data tanpa tanggal yang dibutuhkan dilaporkan terpisah.
- **Ulasan buruk:** skor 1 atau 2; rata-rata skor menjadi metrik pendukung. Proporsinya memakai pesanan dengan skor ulasan valid 1–5.
- Bila satu pesanan memiliki beberapa ulasan, pilih satu ulasan terbaru berdasarkan `review_creation_date`, lalu `review_answer_timestamp`, dengan tie-breaker deterministik. Simpan dan laporkan jumlah pesanan yang terdampak serta alasan pemilihan. Periksa duplikasi persis secara terpisah.
- Urutan pemilihan ulasan: waktu pembuatan terbaru, waktu jawaban terbaru, `review_id` secara leksikografis, lalu nomor baris sumber untuk sisa tie. Tanggal kosong ditempatkan sebelum tanggal valid. Pemilihan dilakukan sebelum memeriksa kelayakan skor; skor terbaru yang tidak valid menjadi tidak tersedia, tanpa diam-diam kembali ke ulasan lama yang lebih menguntungkan.
- Denominator perbandingan terlambat versus tepat waktu hanya memuat pesanan yang mempunyai label keterlambatan dan ulasan valid.
- Tampilkan `n` setiap kelompok. Peringkat negara bagian untuk Q2 mensyaratkan minimal 50 pesanan yang memenuhi syarat pada filter aktif; kelompok kecil tetap bisa dilihat dengan keterangan ukuran sampel.

### RFM dan pengelompokan manual

- Acuan tetap: `2018-09-01`; transaksi yang digunakan dibatasi periode utama.
- Recency = hari dari tanggal pembelian terakhir pelanggan ke tanggal acuan; semakin kecil berarti semakin baru membeli.
- Frequency = jumlah `order_id` unik pelanggan, bukan jumlah item atau baris hasil join.
- Monetary = jumlah nilai barang dari pesanan delivered pelanggan, tidak termasuk freight.
- Gunakan aturan manual tanpa algoritma machine learning. Aturan awal yang saling eksklusif dan mencakup seluruh pelanggan:

| Segmen | Aturan |
| --- | --- |
| Pembeli sekali yang baru | Frequency = 1 dan recency ≤ 30 hari |
| Pembeli sekali yang masih baru | Frequency = 1 dan 30 < recency ≤ 90 hari |
| Pembeli sekali yang lama tidak membeli | Frequency = 1 dan recency > 90 hari |
| Pelanggan berulang aktif | Frequency ≥ 2 dan recency ≤ 90 hari |
| Pelanggan berulang yang lama tidak membeli | Frequency ≥ 2 dan recency > 90 hari |

- Ambang 30/90 hari merupakan heuristik operasional, bukan prediksi churn. Tinjau distribusi recency dan jelaskan keterbatasannya dalam notebook.
- Monetary tetap dianalisis sebagai dimensi RFM dan ditampilkan per segmen. Tambahkan atribut nilai tinggi berdasarkan persentil ke-75 monetary pada populasi acuan; ambang dihitung sekali untuk menjaga perbandingan antarwilayah konsisten.
- Ambang nilai tinggi adalah quantile 0,75 monetary global, dengan metode interpolasi yang dicatat; label menggunakan `monetary_cents >= threshold`. Nilai yang sama pada ambang bisa membuat jumlah pelanggan bernilai tinggi lebih dari 25%, sehingga labelnya bukan klaim tepat 25% pelanggan.
- Negara bagian RFM diambil dari pesanan eligible terakhir pelanggan, dengan tie-breaker timestamp pembelian lalu `order_id`. Filter wilayah RFM memakai atribut ini; metrik R/F/M tetap mencakup seluruh pesanan pelanggan dalam periode acuan. Beri label UI `Wilayah pesanan terakhir` agar arti filter jelas.
- Tidak memaksakan `qcut` pada frequency karena banyak nilai yang sama, dan tidak memakai bobot skor RFM tanpa dasar yang dijelaskan.

## 5. Desain penggabungan dan keluaran data

Hindari satu tabel besar yang menggabungkan seluruh sumber mentah sekaligus. Setiap tabel keluaran memiliki satuan baris yang jelas.

| Keluaran | Satuan baris | Pembentukan dan penggunaan |
| --- | --- | --- |
| `order_level.csv` | Satu baris per pesanan | Orders + customer; item diagregasi ke order terlebih dahulu; ulasan dipilih menjadi satu per order. Seluruh status dipertahankan dan kelayakan metrik ditandai. Untuk Q2 dan KPI pesanan |
| `item_level.csv` | Satu baris per pasangan order/item | Item + produk + terjemahan kategori + atribut pesanan/pelanggan yang diperlukan. Untuk Q1 |
| `rfm_customers.csv` | Satu baris per pelanggan unik | Agregasi pesanan valid berdasarkan `customer_unique_id`, kemudian metrik RFM dan aturan segmen. Untuk Q3 |

Pada setiap join:

1. Periksa keunikan kunci sumber dan gunakan validasi relasi `one_to_one` atau `many_to_one` sesuai kebutuhan.
2. Laporkan kunci yang tidak menemukan pasangan; gunakan left join bila perlu mempertahankan catatan transaksi.
3. Bandingkan jumlah baris, pesanan unik, dan total nilai barang sebelum/sesudah join.
4. Pastikan ulasan dan pembayaran tidak memperbanyak baris item. Jika pembayaran digunakan kemudian, agregasikan ke `order_id` terlebih dahulu dan jelaskan perbedaan definisinya dengan nilai barang.

Definisi kelayakan dipusatkan di kode dan dijelaskan dalam data dictionary:

- `in_analysis_period`: timestamp pembelian valid dan berada di periode utama.
- `eligible_sales`: dalam periode, berstatus delivered, memiliki item, dan nilai barang seluruh item pesanan valid. Pesanan tanpa item tidak diberi nilai nol; pesanan dengan harga item invalid tidak dihitung sebagian tanpa penjelasan.
- `eligible_delivery`: dalam periode, delivered, tanggal aktual/estimasi valid, dan penerimaan tidak mendahului pembelian. Kelayakan ini tidak memerlukan review atau nilai barang yang lengkap.
- `eligible_review_comparison`: eligible delivery dan ulasan terpilih memiliki skor integer 1–5.
- `eligible_rfm`: eligible sales dan mempunyai `customer_unique_id` valid.
- Kunci pelanggan yang tidak cocok diberi penanda. Nilai penjualan global dapat tetap dihitung jika transaksi valid; RFM mengecualikan identitas yang tidak dapat dipetakan dan melaporkan selisih cakupannya.
- Status terlambat dan hari terlambat menggunakan nilai nullable pada pesanan yang tidak bisa dievaluasi. Nilai kosong tidak diubah menjadi `False`, tepat waktu, atau nol hari.

Periode, tanggal acuan, ambang segmen, dan minimum sampel didefinisikan sekali dalam `src/config.py`. Fungsi analisis notebook dan dashboard menggunakan definisi yang sama.

## 6. Struktur proyek yang akan dibuat

```text
Analisis Data E-Commerce/
├── data/                         # CSV sumber lokal, dipertahankan
├── notebook.ipynb                # Mengikuti templat Dicoding, semua output sudah dijalankan
├── src/
│   ├── __init__.py
│   ├── config.py                 # Periode, schema, dan aturan bersama
│   ├── data_pipeline.py          # Load, assessment, cleaning, dan join
│   ├── analytics.py              # Metrik, agregasi, dan segmentasi RFM
│   └── charts.py                 # Grafik yang dipakai notebook/dashboard
├── scripts/
│   ├── prepare_dashboard_data.py # Membentuk ulang CSV dashboard dari sumber lokal
│   ├── validate_outputs.py       # Pemeriksaan integritas hasil analisis
│   └── package_submission.py     # Pengemasan berkas yang dibutuhkan
├── dashboard/
│   ├── dashboard.py
│   ├── order_level.csv
│   ├── item_level.csv
│   ├── rfm_customers.csv
│   └── data_metadata.json        # Schema, provenance, dan parameter analisis
├── reports/
│   ├── baseline.json             # Ukuran dan SHA-256 sumber CSV
│   ├── data_quality.json         # Masalah dan tindakan terukur
│   ├── join_audit.json            # Pemeriksaan join dan cakupan metrik
│   ├── analytical_results.json   # Angka hasil, bukan insight yang dikarang
│   ├── validation_results.json
│   └── figures/
├── references/
│   └── notebook_template.ipynb   # Salinan templat sumber yang diverifikasi
├── tests/
│   ├── test_pipeline.py          # Kasus join, review, dan tanggal berisiko
│   └── test_analytics.py         # Metrik, segmen, dan filter berisiko
├── README.md
├── requirements.txt
├── requirements-dev.txt          # Kernel, eksekusi notebook, dan pemeriksaan
├── url.txt                       # Dibuat setelah deployment berhasil
├── IMPLEMENTATION_PLAN.md
└── EXECUTION_STATUS.md
```

Pemrosesan yang sama digunakan notebook dan skrip persiapan dashboard agar hasilnya konsisten. Notebook tetap menampilkan langkah, pemeriksaan, output, dan penjelasan yang dapat dinilai reviewer. Dashboard memuat keluaran yang sudah disiapkan agar tidak membaca satu juta baris geolocation saat aplikasi dibuka.

Dependensi utama: pandas, NumPy, Matplotlib, Seaborn, dan Streamlit. Versi dipin setelah kombinasi tersebut berhasil diuji di lingkungan lokal. `requirements-dev.txt` menambahkan fasilitas kernel/eksekusi notebook dan pytest. Catat versi Python dan cara membuat lingkungan dari awal. Tidak perlu menambah framework web, database, machine learning, atau layanan berbayar.

Struktur di atas merupakan target bertahap, bukan instruksi untuk membuat seluruh berkas sebagai placeholder. Buat setiap berkas pada phase yang memilikinya. Data dashboard, laporan, dan ZIP harus dihasilkan dari kode; hindari angka hasil yang diketik manual. ZIP diletakkan di `dist/` setelah phase pengemasan dan tidak memasukkan dirinya sendiri.

## 7. Protokol eksekusi untuk AI

### 7.1 Memulai dan melanjutkan pekerjaan

1. Baca instruksi workspace yang berlaku, plan ini, dan `EXECUTION_STATUS.md`. Periksa perubahan pengguna sebelum mengedit.
2. Temukan phase pertama yang belum `completed`, lalu periksa dependency-nya. Urutan default P00 → P12; jangan melompati gate yang menjadi prasyarat.
3. Bila pengguna meminta satu phase, kerjakan phase itu sampai gate-nya terbukti lulus, perbarui progres, lalu laporkan hasil. Bila pengguna meminta rentang phase atau seluruh implementasi, lanjutkan di dalam rentang tersebut tanpa meminta konfirmasi rutin antar-phase.
4. Status `completed` memerlukan keluaran nyata, perintah verifikasi, hasil aktual, dan timestamp. Checkbox saja bukan bukti.
5. Jika terputus di tengah phase, status tetap `in_progress`. Catat file yang telah diubah, pemeriksaan yang sudah lulus, sisa tugas, dan langkah berikutnya yang spesifik.
6. Jika dependency eksternal tidak tersedia, kerjakan bagian independen, catat hambatan dan dampaknya. Jangan mengubah nama hasil yang gagal menjadi sukses atau membuat URL/identitas fiktif.
7. Jika keputusan analisis berubah, catat alasan dan phase terdampak. Perubahan pipeline/metrik membuat keluaran turunannya perlu dihasilkan dan diverifikasi ulang sebelum dinyatakan selesai.

Jangan memulai implementasi proyek hanya karena dokumen ini sedang diperbarui. Dokumen ini menjadi panduan ketika pengguna meminta eksekusinya.

### 7.2 Status dan bukti

| Status | Arti |
| --- | --- |
| `not_started` | Belum ada pekerjaan untuk phase tersebut |
| `in_progress` | Pekerjaan sudah dimulai, gate belum lengkap |
| `completed` | Semua keluaran dan gate phase telah diverifikasi |
| `blocked` | Ada kebutuhan spesifik yang menghalangi penyelesaian; pekerjaan independen tetap dapat dilakukan |
| `deferred_external` | Hanya untuk P11: deployment ditunda karena kebutuhan eksternal yang dicatat; tidak dihitung sebagai deployment berhasil |

Catat bukti dalam `EXECUTION_STATUS.md`: file keluaran, perintah aktual, hasil singkat, tanggal/waktu Asia/Jakarta, masalah tersisa, dan langkah berikutnya. Untuk fase komputasi, laporan terstruktur di `reports/` menyimpan jumlah baris, flag, denominator, serta rekonsiliasi. Laporan boleh bertambah per phase; tahap awal tidak mengklaim pemeriksaan tahap akhir sudah lulus.

Checklist dalam plan adalah spesifikasi pekerjaan. Status eksekusi resmi dicatat di tracker agar AI berikutnya memiliki satu tempat untuk menentukan progres aktual.

### 7.3 Dependency dan checkpoint

| Phase | Fokus | Prasyarat untuk mulai | Checkpoint |
| --- | --- | --- | --- |
| P00 | Inventaris, sumber templat, identitas yang tersedia | Plan | Baseline workspace dan provenance diketahui |
| P01 | Lingkungan, struktur, konfigurasi | P00 inventaris tersedia | Proyek dapat mengimpor modul dari lingkungan yang dicatat |
| P02 | Gathering dan assessment mentah | P01 | Masalah nyata beserta rencana cleaning tercatat |
| P03 | Cleaning yang dapat diulang | P02 | Transformasi dan dampaknya terukur |
| P04 | Join dan kontrak tabel analisis | P03 | Satuan baris dan total nilai terjaga |
| P05 | EDA dan agregasi Q1–Q2 | P04 | Jawaban numerik penjualan/logistik dapat ditelusuri |
| P06 | RFM dan Q3 | P04; default sesudah P05 | Metrik dan aturan segmen tervalidasi |
| P07 | Notebook, visualisasi, kesimpulan | P05, P06; templat terverifikasi | Notebook lengkap dan berhasil dieksekusi |
| P08 | Ekspor data dashboard | P04–P06 | Ekspor deterministik dan dapat dibaca ulang |
| P09 | Dashboard Streamlit | P07, P08 | Alur dan filter berfungsi dengan angka yang benar |
| P10 | Reproduksibilitas dan dokumentasi | P09 | Proyek lokal siap ditinjau dan dipaketkan |
| P11 | Deployment Community Cloud | P10 dan konteks repositori/akun | URL aktif atau kebutuhan eksternal tercatat |
| P12 | ZIP dan audit akhir | P10; hasil P11 telah dicatat | Paket dapat dijalankan dari hasil ekstraksi |

Pekerjaan P01–P06 tidak perlu berhenti bila hanya salinan templat atau identitas yang belum tersedia. P07 memerlukan verifikasi templat; identitas yang belum lengkap dicatat sebagai bagian yang harus diselesaikan sebelum submission final. Kesiapan lokal dan keberhasilan deployment dilaporkan terpisah.

## 8. Panduan rinci per phase

### Phase P00 — Inventaris dan sumber acuan

**Tujuan:** memastikan pelaksana memahami kondisi aktual, bukan menganggap workspace masih sama seperti saat plan ditulis.

**Langkah:**

- [ ] Baca instruksi workspace, plan, dan tracker; inventaris file serta perubahan yang sudah ada.
- [ ] Pastikan sembilan CSV tersedia. Bedakan enam sumber analisis utama dan tiga sumber pendukung.
- [ ] Hitung ukuran byte dan SHA-256 setiap CSV. Jumlah baris/skema dapat dilengkapi P02. Simpan tanggal pemeriksaan dan versi plan dalam `reports/baseline.json`.
- [ ] Cocokkan temuan awal bagian 2 dengan sumber saat ini. Jika berubah, catat perbedaan dan hitung ulang; jangan mengedit sumber agar cocok dengan angka lama.
- [ ] Ambil salinan notebook dari tautan templat wajib melalui akses yang tersedia, simpan `references/notebook_template.ipynb`, dan catat URL serta waktu pengambilan. Jangan mengunduh ulang dataset.
- [ ] Periksa bahwa salinan benar-benar notebook JSON dengan sel, bukan halaman login/HTML. Catat daftar heading dan hash salinan untuk digunakan P07.
- [ ] Catat nama, email, dan Dicoding ID yang sudah diberikan secara eksplisit. Jika belum tersedia, tandai `needs_user_input`; pekerjaan data tetap berjalan.

**Keluaran:** `baseline.json`, salinan templat bila dapat diakses, dan entri P00 pada tracker. Saat akses templat gagal, catat `template_verified: false` sebagai hambatan khusus notebook.

**Gate:** setiap sumber teridentifikasi; asal templat diketahui; tidak ada klaim notebook/identitas telah terverifikasi tanpa bukti. Inventaris dapat diselesaikan walau salinan templat masih menjadi dependency P07.

**Handoff:** daftar sumber utama, status templat, kebutuhan identitas, dan runtime yang tersedia untuk disiapkan P01.

### Phase P01 — Lingkungan dan fondasi kode

**Tujuan:** menyediakan titik masuk yang konsisten untuk notebook, skrip, dan dashboard.

**Langkah:**

- [ ] Pilih versi Python dari runtime yang tersedia dan cocok dengan dependensi; catat versi aktual. Gunakan lingkungan terisolasi.
- [ ] Buat direktori yang dibutuhkan sekarang, `src/__init__.py`, `src/config.py`, dan fungsi loader awal pada `src/data_pipeline.py`.
- [ ] Definisikan periode, snapshot RFM, minimum sampel 50, ambang 30/90 hari, kategori fallback, dan schema inti di satu tempat.
- [ ] Siapkan dependensi runtime serta dependensi pengembangan. Catat versi yang benar-benar terpasang; finalisasi pin dan clean install dilakukan P10.
- [ ] Gunakan project root secara eksplisit. Path data diturunkan dari root, bukan direktori kerja yang kebetulan aktif. Entry point skrip/dashboard harus dapat menemukan paket `src` secara konsisten.
- [ ] Loader menjaga ID sebagai string, membaca sumber tanpa mengubahnya, dan memberikan kesalahan yang jelas bila file/kolom wajib tidak ada.
- [ ] Buat petunjuk setup awal README yang akan dilengkapi P10.

**Keluaran:** konfigurasi bersama, loader, berkas dependensi awal, README awal.

**Verifikasi:** impor paket dari root, muat satu CSV dengan schema yang diharapkan, dan pastikan file sumber tidak berubah. Uji entry point yang memakai `__file__` dari direktori kerja lain ketika skripnya sudah tersedia.

**Gate:** lingkungan yang dipakai tercatat, konfigurasi tidak digandakan, dan loader berhasil membaca data asli.

### Phase P02 — Gathering dan Assessing Data

**Tujuan:** menghasilkan daftar masalah yang nyata dan tindakan yang dapat dipertanggungjawabkan.

**Langkah:**

- [ ] Muat enam tabel utama; untuk sumber pendukung, cukup inventaris/profil ringkas sampai diperlukan.
- [ ] Lengkapi baseline dengan baris, kolom, tipe awal, rentang tanggal, status, dan jumlah nilai kosong.
- [ ] Uji keunikan kunci orders, customers, products, translation serta pasangan `(order_id, order_item_id)`.
- [ ] Bedakan duplikasi persis, kunci ulasan berulang, dan banyak ulasan per pesanan. Jangan menyamakan `review_id` berulang dengan baris identik.
- [ ] Hitung kegagalan parsing tanggal/numerik, harga negatif, skor di luar 1–5 atau bukan integer, kunci kosong, foreign key yang tidak ditemukan, dan urutan tanggal tidak masuk akal.
- [ ] Periksa missing value menurut status; pisahkan ketidaklengkapan struktural dengan masalah pada pesanan delivered.
- [ ] Periksa kategori kosong dan kode kategori yang tidak menemukan terjemahan secara terpisah.
- [ ] Susun tabel `issue_id`, sumber/kolom, jenis masalah, jumlah terdampak, arti bisnis, tindakan, dan metrik yang terpengaruh.
- [ ] Simpan hasil pada `reports/data_quality.json`; siapkan tabel ringkas untuk sel Assessing dan `Steps to Take` di notebook.

**Keluaran:** baseline lengkap, laporan kualitas, dan daftar tindakan cleaning yang merujuk `issue_id`.

**Gate:** minimal dua jenis masalah aktual teridentifikasi dengan bukti; setiap masalah mempunyai kebijakan; jumlah baris dan status dapat direproduksi. Tidak semua missing value harus diimputasi.

**Handoff:** keputusan mengenai kategori, review, tanggal, harga, dan ketidakcocokan kunci yang harus diterapkan P03.

### Phase P03 — Cleaning dan penanda kualitas

**Tujuan:** menghasilkan data bersih yang tetap mempertahankan cakupan transaksi dan alasan pengecualian.

**Langkah:**

- [ ] Implementasikan fungsi cleaning per tabel dalam `data_pipeline.py`; setiap fungsi mengembalikan tabel dan audit dampak transformasinya.
- [ ] Konversi timestamp, skor, dan uang dengan penanganan nilai gagal parsing yang terlihat pada laporan.
- [ ] Terapkan label kategori kosong dan fallback terjemahan sesuai bagian 4.
- [ ] Pilih review secara deterministik; pertahankan jejak jumlah alternatif dan alasan pilihan. Jangan menimpa atau menghapus sumber mentah.
- [ ] Buat flag validitas tanggal, skor, dan harga. Pertahankan nilai kosong sebagai tidak tersedia pada metrik yang tidak dapat dievaluasi.
- [ ] Terapkan penghapusan duplikasi persis hanya setelah dampak dan satuan barisnya diperiksa. Untuk benturan kunci yang berisi nilai berbeda, selesaikan dengan kebijakan terdokumentasi; hentikan join terkait bila konflik belum terselesaikan.
- [ ] Catat sebelum/sesudah untuk tiap `issue_id`, termasuk tindakan tanpa perubahan data dan alasan relevansinya.
- [ ] Tambahkan tes bermakna pada `tests/test_pipeline.py`: penerimaan pada hari estimasi, tanggal hilang, kronologi invalid, pemilihan review terbaru/tie, kategori tidak diketahui versus belum diterjemahkan.

**Keluaran:** fungsi cleaning, laporan dampak terstruktur, dan tes kasus berisiko.

**Gate:** transformasi dapat diulang dari sumber mentah; kunci wajib siap di-join; missing value tidak berubah menjadi ketepatan pengiriman palsu; hash sumber tetap sama dengan baseline.

### Phase P04 — Integrasi dan kontrak data analisis

**Tujuan:** membentuk tabel order/item tanpa menggandakan transaksi.

**Langkah:**

- [ ] Agregasikan item ke order untuk `order_value_cents`, jumlah item, dan kelengkapan nilai barang. Nilai pesanan tanpa item tetap kosong.
- [ ] Buat order-level melalui join orders → customers → agregat item → satu review terpilih. Pertahankan satu baris per pesanan dan seluruh status sumber.
- [ ] Buat item-level melalui join item → orders/customer → products → translation. Pertahankan satu baris per pasangan order/item.
- [ ] Terapkan flag kelayakan bagian 5; catat jumlah eligible dan alasan tidak eligible per metrik. Hindari satu filter universal yang membuat Q2 bergantung pada adanya harga atau review.
- [ ] Gunakan validasi kardinalitas pandas pada setiap join dan laporkan unmatched key, perubahan baris, serta total uang sebelum/sesudah join pada `reports/join_audit.json`.
- [ ] Catat schema minimum: nama, tipe, satuan, arti null, kunci unik, dan sumber setiap kolom turunan. Schema diekspor bersama data pada P08.
- [ ] Uji contoh kecil yang mempunyai beberapa item dan beberapa review; hasil order tetap satu dan nilai uang tidak bertambah. Jika pembayaran ikut digunakan, tambahkan kasus beberapa pembayaran.

**Kolom minimum:**

| Tabel | Kolom inti |
| --- | --- |
| Order-level | `order_id`, `customer_id`, `customer_unique_id`, `customer_state`, `order_status`, `order_purchase_timestamp`, `purchase_date`, `purchase_month`, `order_value_cents`, `item_count`, `review_score`, `days_late`, `is_late`, dan seluruh flag eligibility |
| Item-level | `order_id`, `order_item_id`, `product_id`, kode/nama kategori, `price_cents`, `freight_cents` bila dipakai, timestamp/bulan pembelian, negara bagian, dan flag eligibility yang diperlukan |

**Gate:** kunci unik; jumlah order tidak bertambah akibat join; jumlah price item tidak berubah akibat join kategori; total item dan agregat order cocok dalam populasi eligible sales yang sama. Perbedaan cakupan metrik dijelaskan dengan jumlah aktual.

### Phase P05 — Agregasi Q1 dan Q2

**Tujuan:** memastikan jawaban numerik benar sebelum mempercantik grafik.

**Langkah Q1:**

- [ ] Implementasikan fungsi filter eligible sales berdasarkan rentang tanggal dan negara bagian.
- [ ] Hitung nilai barang, item, pesanan unik, dan kontribusi kategori; pilih top 5 dari kategori diketahui dengan tie-breaker kode kategori yang stabil.
- [ ] Pisahkan kontribusi kategori tidak diketahui. Cek bahwa kontribusi seluruh kategori berjumlah 100% ketika denominator tidak nol.
- [ ] Pilih top 5 sekali untuk periode/filter yang dianalisis, kemudian gambarkan seri bulanan kategori yang sama; jangan mengganti anggota top 5 setiap bulan secara diam-diam.
- [ ] Tampilkan rentang bulan kalender sesuai filter. Nilai nol hanya untuk bulan yang tercakup dalam periode analisis dan tidak memiliki transaksi yang memenuhi filter; jelaskan bahwa nol teramati tidak membuktikan pencatatan sumber lengkap.

**Langkah Q2:**

- [ ] Hitung tingkat keterlambatan dengan denominator eligible delivery.
- [ ] Bandingkan ulasan buruk terlambat versus tepat waktu dengan denominator eligible review comparison pada masing-masing kelompok.
- [ ] Hitung selisih `bad_review_rate_late - bad_review_rate_on_time` dalam persentase poin, bukan persen relatif.
- [ ] Buat ringkasan wilayah: total delivered, delivery evaluable, jumlah terlambat, review-comparison evaluable, jumlah ulasan buruk, tingkat masing-masing, dan ukuran sampel.
- [ ] Peringkat wilayah memakai minimal 50 order eligible review comparison pada filter aktif; urutkan keterlambatan menurun, proporsi ulasan buruk menurun, ukuran sampel menurun, lalu kode state. Jelaskan bahwa ini aturan prioritas investigasi, bukan estimasi sebab-akibat.
- [ ] Tampilkan jumlah order yang tidak bisa dievaluasi agar coverage terlihat.

**Keluaran:** fungsi Q1/Q2 dalam `src/analytics.py`, ringkasan hasil aktual di `reports/analytical_results.json`, dan pemeriksaan di `tests/test_analytics.py`.

**Gate:** agregat dapat ditelusuri ke tabel baris; denominator dan cakupan eksplisit; kasus filter kosong, total nol, serta tidak ada ulasan menghasilkan nilai unavailable yang benar. Jangan menyimpulkan arah temuan sebelum perhitungan selesai.

### Phase P06 — RFM dan segmentasi Q3

**Tujuan:** membuat analisis lanjutan yang cocok dengan dominasi pembeli sekali.

**Langkah:**

- [ ] Agregasikan eligible RFM dari order-level menurut `customer_unique_id`.
- [ ] Hitung tanggal pembelian terakhir, recency kalender, frequency order unik, dan monetary cents. Atribut negara bagian mengikuti pesanan eligible terakhir.
- [ ] Terapkan lima aturan segmen bagian 4 secara eksklusif; tidak boleh ada pelanggan tanpa segmen atau masuk dua segmen.
- [ ] Hitung ambang monetary tinggi dari populasi acuan penuh sekali, simpan metode quantile dan nilainya; jangan menghitung ulang ambang ketika filter dashboard berubah.
- [ ] Hitung jumlah pelanggan, kontribusi pelanggan, total monetary, kontribusi monetary, median R/F/M, dan pelanggan bernilai tinggi per segmen.
- [ ] Catat sifat heuristik 30/90 hari, keterbatasan jendela observasi dan status snapshot, serta bahwa pembeli sekali bukan otomatis pelanggan churn.
- [ ] Tambahkan tes dua `customer_id` yang mempunyai satu `customer_unique_id`; frequency harus 2 untuk dua order berbeda, meskipun masing-masing order mempunyai beberapa item.
- [ ] Uji batas recency 30/31/90/91, frequency 1/2, monetary pada ambang, dan konsistensi state pesanan terakhir.

**Keluaran:** tabel RFM dalam memori, fungsi segmentasi, hasil Q3 dan rekonsiliasi dalam laporan.

**Gate:** recency tidak negatif; frequency integer minimal 1; satu pelanggan satu baris/segmen; total frequency sama dengan order unik eligible RFM; jumlah monetary sama dengan nilai order eligible RFM. Selisih terhadap eligible sales dijelaskan bila ada identitas pelanggan yang tidak dapat dipetakan.

### Phase P07 — Notebook, visualisasi, kesimpulan, rekomendasi

**Tujuan:** menghasilkan dokumen analisis yang memenuhi templat dan dapat dinilai tanpa membaca kode aplikasi.

**Langkah notebook:**

- [ ] Buat `notebook.ipynb` dari templat P00 yang sudah terverifikasi; pertahankan urutan heading wajib. Jangan mengganti struktur dengan notebook generik.
- [ ] Isi identitas yang sudah tersedia; catat bagian yang masih memerlukan informasi pengguna tanpa mengarangnya.
- [ ] Tampilkan pertanyaan SMART, penjelasan periode, pustaka, Gathering, Assessing beserta `Steps to Take`, Cleaning, EDA, Visualization & Explanatory Analysis, analisis lanjutan, serta Conclusion & Recommendation.
- [ ] Tampilkan pemetaan setiap Q terhadap Specific, Measurable, Action-Oriented, Relevant, dan Time-bound. Saat menyalin pertanyaan ke notebook, tuliskan periode Q2 dan periode observasi Q3 secara eksplisit agar pertanyaan tetap jelas ketika dibaca terpisah.
- [ ] Gunakan fungsi bersama per tahap, lalu tampilkan tabel, pemeriksaan, dan interpretasinya. Hindari satu sel `run_pipeline()` yang menyembunyikan seluruh proses.
- [ ] Di Gathering tampilkan cakupan sumber; di Assessing tampilkan bukti masalah; di Cleaning tampilkan hasil sebelum/sesudah; di EDA tampilkan temuan Q1–Q3; di Explanatory jelaskan pesan grafik.

**Daftar visual yang harus tersedia:**

| ID | Visual | Pesan/konteks yang harus terlihat |
| --- | --- | --- |
| V01 | Bar horizontal top 5 kategori | Nilai BRL, kontribusi, periode, dan kategori tidak diketahui secara terpisah |
| V02 | Tren bulanan kategori V01 | Anggota kategori konsisten dan cakupan bulan jelas |
| V03 | Ulasan buruk menurut ketepatan pengiriman | Persentase, n per kelompok, selisih persentase poin, batas interpretasi |
| V04 | Prioritas negara bagian | Tingkat keterlambatan, ulasan buruk, dan ukuran sampel; pisahkan skala jika memakai beberapa panel |
| V05 | Distribusi R, F, M | Hari/order/BRL jelas; dominasi frequency 1 terlihat |
| V06 | Jumlah dan kontribusi nilai segmen | Dua panel dengan denominator masing-masing dan tanggal acuan RFM |

- [ ] Buat fungsi visual bersama di `src/charts.py`. Untuk setiap visual gunakan judul konteks, unit, label, skala jujur, dan warna konsisten; bar chart mulai dari nol.
- [ ] Terapkan pemeriksaan desain dan integritas pada seluruh grafik yang ditampilkan, termasuk grafik eksploratif, analisis lanjutan, dan dashboard; bukan hanya enam visual utama.
- [ ] Ekspor figure ke `reports/figures/` dan periksa hasil render: label panjang, angka terpotong, legenda, kontras, ukuran teks, dan kerapian tampilan.
- [ ] Tulis satu kesimpulan per Q menggunakan angka hasil aktual. Setiap rekomendasi menyebut segmen/kategori/wilayah yang didukung data, tindakan, dan indikator evaluasi; jangan menjanjikan kenaikan penjualan tanpa bukti.
- [ ] Jalankan notebook dari kernel bersih dan simpan output. Periksa tidak ada sel error, hasil dari state lama, atau jawaban generik yang tidak sesuai angka.

**Gate:** semua bagian templat terisi; minimal satu visual menjawab tiap Q; insight Gathering–Explanatory tersedia; tiga Q mempunyai kesimpulan dan minimal satu action item. Eksekusi berhasil dan visual diperiksa. Jika identitas belum lengkap, laporkan notebook analitis siap dengan kebutuhan identitas tersisa, bukan submission final selesai.

### Phase P08 — Ekspor data dashboard dan metadata

**Tujuan:** menyediakan input dashboard yang cepat, konsisten, dan dapat diregenerasi.

**Langkah:**

- [ ] Buat `scripts/prepare_dashboard_data.py` untuk menjalankan ulang loader → cleaning → join → RFM dari `data/`.
- [ ] Ekspor tiga CSV ke `dashboard/` dengan urutan kolom dan baris stabil, format timestamp ISO, serta representasi null yang terdokumentasi.
- [ ] Ekspor `data_metadata.json`: schema/version, SHA-256 sumber, periode, snapshot, aturan segmen, quantile/ambang monetary, row count, cakupan eligibility, serta baseline KPI/agregasi default untuk pemeriksaan silang.
- [ ] Hindari membawa judul/pesan ulasan atau kolom tak terpakai ke dashboard. Kolom yang diperlukan audit/analisis tetap tersedia pada sumber lokal/laporan.
- [ ] Implementasikan pembacaan ulang dengan dtype eksplisit: ID string, uang integer, skor nullable integer, tanggal sebagai datetime, dan boolean nullable. String `'False'` tidak boleh diubah melalui `astype(bool)` yang menganggap string tidak kosong sebagai true.
- [ ] Jalankan ulang ekspor dan bandingkan isi data. Waktu pembuatan boleh berubah, tetapi baris, urutan deterministik, metrik, serta parameter harus konsisten.

**Gate:** round-trip CSV menjaga ID, null, boolean, tanggal, dan total uang; hasil sesuai notebook; file bisa dibuat ulang melalui satu perintah dari sumber lokal.

### Phase P09 — Dashboard Streamlit

**Tujuan:** menyampaikan Q1–Q3 melalui filter yang konsisten dan antarmuka bahasa Indonesia.

**Langkah:**

- [ ] Buat tiga tab: `Penjualan`, `Pengiriman & Ulasan`, dan `Pelanggan RFM`.
- [ ] Penjualan: filter tanggal pembelian dan negara bagian, KPI nilai barang/order/item, V01/V02, coverage kategori, serta ringkasan yang mengikuti filter.
- [ ] Pengiriman: filter tanggal/state dengan arti yang sama, KPI keterlambatan dan coverage, V03/V04, jumlah sampel, serta penjelasan kaitan teramati.
- [ ] RFM: tampilkan periode dan snapshot tetap, filter segmen dan `Wilayah pesanan terakhir`, jumlah pelanggan dan monetary, V05/V06, serta definisi segmentasi.
- [ ] Bedakan kontrol tanggal penjualan/pengiriman dari filter RFM. Jangan menampilkan kontrol yang terlihat global tetapi diabaikan tanpa penjelasan pada tab lain.
- [ ] Gunakan tanggal akhir pilihan pengguna secara inklusif melalui batas eksklusif hari berikutnya, supaya transaksi pada malam hari tidak hilang.
- [ ] Pastikan filter mengubah pembilang, denominator, top kategori, dan insight terkait secara konsisten. Insight dinamis dihitung dari hasil filter; narasi hasil global diberi konteks yang jelas.
- [ ] Tampilkan keadaan kosong, tidak ada ulasan, denominator nol, kurang dari lima kategori, kurang dari minimum sampel, dan pilihan rentang satu tanggal tanpa exception atau klaim palsu.
- [ ] Gunakan cache pembacaan/transformasi sesuai versi Streamlit terpasang dan hindari mutasi global DataFrame yang memengaruhi sesi/filter lain.
- [ ] Saat metadata/schema tidak cocok atau input belum dibuat, tampilkan langkah perbaikan yang dapat dijalankan, bukan traceback mentah sebagai satu-satunya petunjuk.
- [ ] Verifikasi widget secara otomatis bila fasilitas versi terpasang mendukungnya, lalu buka UI nyata untuk memeriksa layout, interaksi, keterbacaan, dan keadaan kosong.

**Gate:** aplikasi berjalan dengan `streamlit run dashboard/dashboard.py`; angka default sesuai notebook; hasil filter diperiksa pada populasi yang sama; tidak ada exception; grafik dan kontrol terbaca di browser. Server hidup atau endpoint health berhasil saja belum membuktikan dashboard benar.

### Phase P10 — Verifikasi lintas keluaran dan README

**Tujuan:** membuktikan proyek lokal dapat diulang dari lingkungan yang dicatat.

**Langkah:**

- [ ] Selesaikan `scripts/validate_outputs.py` untuk pemeriksaan sumber, kunci, cakupan, uang, RFM, schema, dan konsistensi metadata/ekspor. Skrip menghasilkan exit code gagal bila syarat wajib tidak terpenuhi.
- [ ] Jalankan tes kasus berisiko dan pemeriksaan dataset nyata. Simpan hasil aktual pada `reports/validation_results.json` beserta perintah dan versi lingkungan.
- [ ] Dari sumber asli, hasilkan ulang data dashboard lalu jalankan ulang notebook dari kernel bersih. Pastikan tidak bergantung pada output notebook sebelumnya.
- [ ] Cocokkan KPI/agregasi notebook, ekspor, dan dashboard default: nilai barang, order, keterlambatan dan denominator, ulasan buruk per kelompok, serta jumlah/monetary segmen.
- [ ] Finalisasi pin dependensi runtime dan development. Instal di lingkungan bersih yang tersedia, lalu jalankan alur README.
- [ ] Lengkapi README: tujuan, sumber lokal, struktur, versi Python, setup, regenerasi CSV, notebook, perintah Streamlit, definisi metrik, filter RFM, keterbatasan, dan rujukan.
- [ ] Periksa identitas pemilik dan seluruh placeholder. Jika data identitas belum diberikan, minta hanya informasi yang masih diperlukan dan lanjutkan pekerjaan independen; jangan mengklaim kelengkapan submission sampai terisi.
- [ ] Audit bahasa kesimpulan, kesesuaian saran Dicoding, path lokal hardcoded, file yang tidak disertakan, serta URL/claim yang belum terverifikasi.
- [ ] Audit orisinalitas: hasil, narasi, dan implementasi harus sesuai analisis dataset proyek ini. Cantumkan sumber dataset, templat wajib, serta kode/teknik yang diadaptasi. Contoh proyek menjadi referensi yang dijelaskan, bukan salinan hasil analisis atau identitas orang lain. Jangan mengarang aturan tambahan tentang alat bantu yang tidak tercantum pada instruksi yang diperiksa.

**Perintah target** — digunakan setelah berkas implementasinya benar-benar tersedia:

```bash
python -m pip install -r requirements-dev.txt
python scripts/prepare_dashboard_data.py
python scripts/validate_outputs.py
python -m pytest -q
python -m jupyter nbconvert --to notebook --execute --inplace notebook.ipynb --ExecutePreprocessor.timeout=600
python scripts/validate_outputs.py
python -m streamlit run dashboard/dashboard.py
```

`requirements-dev.txt` harus memasukkan runtime melalui `-r requirements.txt`. Skrip validasi juga dipanggil setelah regenerasi/eksekusi untuk mendeteksi drift. Perintah di atas adalah target kontrak, bukan bukti bahwa implementasi saat ini sudah ada atau telah dijalankan.

**Gate:** instalasi dan alur README berhasil; laporan integritas lulus; notebook dieksekusi; UI diperiksa; tidak ada error analitis yang belum diselesaikan. Jika ada kebutuhan identitas tersisa, bedakan kesiapan teknis lokal dengan kesiapan submission final.

### Phase P11 — Deployment Streamlit Community Cloud

**Tujuan:** menerapkan saran deployment setelah hasil lokal siap ditinjau.

**Langkah:**

- [ ] Periksa konteks akun dan repositori yang sudah tersedia/diotorisasi. Tunjukkan aplikasi lokal dan berkas siap deploy sebelum meminta informasi atau persetujuan yang memang masih diperlukan.
- [ ] Gunakan entry point `dashboard/dashboard.py`, dependensi yang sudah diuji, versi Python yang sesuai, modul bersama, dan tiga CSV beserta metadata.
- [ ] Pilih repositori, branch, dan visibilitas berdasarkan pilihan/otorisasi pengguna yang tersedia. Jangan mengarang nama repositori atau URL deployment.
- [ ] Bila akun/repo belum siap atau publikasi belum diotorisasi, catat kebutuhan spesifik sebagai `deferred_external`. Pekerjaan paket lokal tetap dilanjutkan; saran deployment tetap berstatus belum terpenuhi.
- [ ] Setelah deploy, baca log build/runtime dan buka URL aplikasi; periksa tab, KPI, filter, serta satu keadaan kosong. Label sumber/periodenya harus sama dengan versi lokal.
- [ ] Buat `url.txt` hanya setelah URL aktif dan terverifikasi. Catat URL dan versi kode/data yang dipublikasikan.

**Gate berhasil:** build dan uji aplikasi publik berhasil, URL aktif tersimpan, serta isi sesuai versi lokal. Status `deferred_external` bukan lulus deployment dan tidak boleh dilaporkan sebagai seluruh saran penilaian terpenuhi.

### Phase P12 — Pengemasan dan audit submission

**Tujuan:** menghasilkan paket yang benar-benar dapat dijalankan reviewer dari hasil ekstraksi.

**Langkah:**

- [ ] Buat pengemasan deterministik melalui `scripts/package_submission.py` dan daftar isi eksplisit. Sertakan sumber CSV yang digunakan, notebook dengan output, dashboard beserta data, `src`, skrip regenerasi/validasi, README, dan requirements.
- [ ] Sertakan `url.txt` hanya jika P11 berhasil. Tambahkan test/laporan ringkas yang diperlukan untuk reproduksi; jangan mengandalkan folder lokal yang tidak masuk ZIP.
- [ ] Kecualikan environment, cache, `.git`, `.DS_Store`, catatan kosong, serta `dist/` dari isi paket. Dataset sumber yang tidak digunakan tidak wajib dimasukkan hanya untuk memperbesar ZIP.
- [ ] Simpan ZIP dan manifest/checksum di `dist/`, di luar daftar sumber pengemasan.
- [ ] Ekstrak ZIP ke direktori sementara baru. Periksa sumber yang dibutuhkan lengkap dan file notebook masih memiliki output.
- [ ] Dari ekstraksi, jalankan instalasi yang didokumentasikan bila diperlukan, regenerasi data dashboard, validasi, dan dashboard. Periksa bahwa impor/path tidak bergantung pada workspace asli.
- [ ] Cocokkan checklist Dicoding bagian 10 terhadap isi ZIP dan bukti phase. Periksa identitas wajib yang masih kosong sebelum menandai siap submission.
- [ ] Jalankan checklist target maksimum bagian 10.1. Jika satu saran belum terpenuhi, laporkan tepat bagian yang masih kurang; status siap dijalankan secara lokal tidak sama dengan seluruh persyaratan bintang 5 terpenuhi.
- [ ] Catat nama ZIP, ukuran, checksum, hasil uji ekstraksi, URL bila ada, dan saran penilaian yang sudah/belum diterapkan.

**Gate:** paket dapat direproduksi dari hasil ekstraksi, persyaratan lokal terpenuhi, identitas lengkap, dan status deployment dijelaskan dengan benar. Pengiriman ke Dicoding adalah tindakan terpisah sesuai instruksi pengguna yang berlaku saat itu.

## 9. Pemeriksaan wajib dan respons terhadap kegagalan

| ID | Pemeriksaan | Bukti lulus | Jika gagal |
| --- | --- | --- | --- |
| C01 | Sumber tetap sesuai baseline | SHA-256 CSV sumber sama | Cari apakah pengguna mengubah data; hitung ulang baseline dengan alasan, jangan menimpa sumber |
| C02 | Satuan baris benar | Order unik; pasangan order/item unik; pelanggan RFM unik | Perbaiki cleaning/join sebelum menghasilkan agregasi |
| C03 | Uang tidak berlipat | Item cents sebelum/sesudah join dan agregat order sama pada populasi sama | Audit kardinalitas dan unmatched/invalid record |
| C04 | Kelayakan dipisahkan | Jumlah eligible dan alasan pengecualian per metrik tersedia | Perbaiki flag/denominator; jangan menyembunyikan kehilangan cakupan |
| C05 | Tanggal tepat waktu benar | Hari yang sama tepat waktu; missing/invalid tidak dianggap tepat waktu | Kembali ke P03/P04 dan regenerasi hasil terkait |
| C06 | Review satu per order | Pilihan deterministik; skor valid; counts tepat | Perbaiki seleksi sebelum menghitung proporsi |
| C07 | Proporsi dan filter benar | Pembilang ≤ denominator; 0–100%; n=0 unavailable | Perbaiki fungsi agregasi dan keadaan kosong |
| C08 | RFM direkonsiliasi | Frequency = order unik eligible RFM; monetary = nilai order populasi itu | Audit identitas unik, filter, item, dan grouping |
| C09 | Segmentasi lengkap | Satu pelanggan tepat satu segmen; batas 30/90 lolos | Perbaiki aturan, bukan menyesuaikan hasil manual |
| C10 | Ekspor terbaca konsisten | Dtype/null dan total tetap setelah CSV round-trip | Perbaiki schema/loader ekspor |
| C11 | Semua keluaran selaras | Notebook = agregat ekspor = dashboard pada filter sama | Temukan sumber drift; jangan mengubah narasi/metadata agar menutupi perbedaan |
| C12 | Notebook reproduktif | Eksekusi kernel bersih tanpa error, output tersimpan | Perbaiki dependency/state/path dan jalankan ulang |
| C13 | UI dapat digunakan | Default, filter sempit, sampel kecil, dan hasil kosong diperiksa | Perbaiki UI atau komputasi terkait lalu ulang skenario terdampak |
| C14 | Paket mandiri | Alur README berhasil dari ekstraksi baru | Tambahkan dependensi/berkas yang kurang dan buat ulang ZIP |
| C15 | Deployment nyata | URL dapat dibuka dan fungsi utama lolos | Perbaiki deployment atau laporkan P11 deferred/blocked dengan jujur |
| C16 | Orisinalitas dan atribusi | Sumber/adaptasi tercantum; hasil dan narasi berasal dari analisis proyek ini | Tinjau ulang bagian yang disalin atau klaim yang tidak didukung sebelum pengemasan |
| C17 | Desain seluruh visualisasi | Grafik notebook, EDA, RFM, dan dashboard sudah diperiksa | Perbaiki seluruh grafik yang tidak memenuhi prinsip, bukan hanya visual utama |

Tes memakai kasus kecil yang sengaja memunculkan risiko bisnis dan pemeriksaan pada dataset asli. Jangan membuat tes yang hanya menyalin rumus implementasi atau mengganti hasil yang diharapkan agar tes lulus. Perubahan kosmetik cukup diperiksa render/UI; perluasan tes dilakukan bila ada kegagalan atau risiko yang belum tercakup.

Jika pipeline/metrik berubah setelah P05, perbarui P05/P06 yang terdampak, notebook, ekspor, dashboard, laporan validasi, deployment bila sudah ada, dan ZIP. Tracker menyimpan status verifikasi terakhir; hasil lama tidak otomatis tetap sah.

## 10. Pemetaan ke kriteria Dicoding

| Kriteria/saran | Phase pemilik | Bukti yang akan tersedia |
| --- | --- | --- |
| Menggunakan dataset yang disediakan | P00, P02, P12 | CSV lokal yang digunakan dan provenance dalam paket |
| Minimal 2 pertanyaan SMART | P05–P07 | Q1–Q3, periode, populasi, metrik, dan tujuan tindakan |
| Gathering, Assessing, Cleaning | P02, P03, P07 | Sel notebook, masalah, `Steps to Take`, tindakan, dan dampak |
| EDA menjawab pertanyaan | P05, P06, P07 | Tabel agregasi dan insight per Q |
| Minimal 2 visualisasi | P07 | V01–V06; minimal satu menjawab setiap Q |
| Minimal 2 kesimpulan dan 1 rekomendasi | P07 | Kesimpulan tiap Q dan tindakan berbasis hasil aktual |
| Templat notebook rapi dan dieksekusi | P00, P07, P10 | Templat terverifikasi, identitas, output tersimpan |
| Dashboard Streamlit lokal | P08–P10 | Aplikasi, input, petunjuk, dan hasil uji |
| Dokumentasi setiap tahap | P07 | Insight Gathering sampai Explanatory Analysis |
| Desain dan integritas visual | P07, P09 | Label/unit, skala, denominator, dan pemeriksaan render |
| Analisis lanjutan tanpa ML | P06, P07 | RFM/manual grouping beserta tujuan dan aturan |
| Deployment cloud | P11 | URL aktif dan `url.txt`; belum terpenuhi jika deferred |
| Ketentuan ZIP | P12 | Paket lengkap dan uji hasil ekstraksi |

### 10.1 Checklist khusus target penilaian maksimum

Checklist berikut merujuk tab **Kriteria**, **Penilaian**, **Ketentuan Berkas Submission**, dan **Lainnya** pada halaman instruksi. Kolom ini merupakan syarat hasil akhir, belum merupakan bukti implementasi sudah selesai.

| Bagian rubrik | Kondisi yang harus benar pada hasil akhir | Pemeriksaan terakhir |
| --- | --- | --- |
| Wajib 1 — Dataset | Dataset E-Commerce yang disediakan digunakan, dan CSV sumber yang dipakai ikut dalam ZIP | P02, P12 |
| Wajib 2 — Proses lengkap | Minimal 2 pertanyaan SMART; minimal 2 masalah data aktual beserta tindakan cleaning; EDA menjawab pertanyaan; minimal 2 visualisasi dan satu untuk setiap Q; kesimpulan setiap Q dan minimal 1 action item | P02–P07, P10 |
| Wajib 3 — Notebook | Mengikuti templat yang disediakan, isi terisi rapi, dan output hasil eksekusi sudah tersimpan | P00, P07, P10 |
| Wajib 4 — Dashboard | Streamlit interaktif berjalan lancar secara lokal | P09, P10, P12 |
| Saran 1 — Dokumentasi | Markdown/text cell menjelaskan setiap tahap dan merangkum insight dari Gathering Data sampai Explanatory Analysis | P07 |
| Saran 2 — Visualisasi | Seluruh visualisasi menerapkan prinsip desain dan integritas, termasuk unit, skala, label, konteks, dan denominator | P07, P09, C17 |
| Saran 3 — Deployment | Dashboard benar-benar di-deploy ke Streamlit Cloud, URL berfungsi, dan URL tersebut ditulis dalam `url.txt` di ZIP | P11 harus `completed`, P12 |
| Saran 4 — Analisis lanjutan | RFM/manual grouping relevan dengan perilaku pembelian E-Commerce, tidak memakai algoritma ML, dan tujuan/tekniknya dijelaskan pada markdown/text cell notebook | P06, P07 |
| Berkas | ZIP memuat dataset yang digunakan, notebook terjalankan, dashboard `.py`, modul pendukung, `requirements.txt`, README cara menjalankan, dan `url.txt` untuk deployment | P12 |
| Orisinalitas | Tidak ada plagiarisme/kecurangan; sumber dan adaptasi dijelaskan dan hasil analisis dapat ditelusuri | P10, C16 |

Tidak wajib menerapkan seluruh contoh analisis lanjutan sekaligus. RFM yang relevan dan dijelaskan dengan baik memenuhi rancangan untuk saran keempat; geospatial analysis dan teknik lain tidak perlu ditambahkan hanya untuk memperbanyak fitur. Penggunaan seluruh sembilan CSV juga tidak diwajibkan bila hanya enam yang diperlukan untuk menjawab pertanyaan.

Status akhir yang boleh dilaporkan:

- **Siap teknis lokal:** gate lokal lulus, dengan kebutuhan identitas/deployment yang masih ada dinyatakan eksplisit.
- **Seluruh butir target bintang 5 terpenuhi secara internal:** semua baris checklist ini memiliki bukti aktual, termasuk P11 `completed`, URL aktif, dan paket ZIP yang lulus uji.
- **Nilai bintang 5 diperoleh:** hanya setelah hasil review Dicoding menyatakannya. Kelengkapan internal tidak menjamin keputusan reviewer.

## 11. Format laporan dan prompt eksekusi

Setiap phase diakhiri dengan laporan singkat: pekerjaan selesai, berkas berubah, pemeriksaan yang benar-benar dijalankan dan hasilnya, hambatan tersisa, serta phase berikutnya. Tambahkan angka hasil hanya setelah dihitung. Untuk langkah yang belum dijalankan, tulis status rencana, bukan kalimat seolah sudah berhasil.

Contoh prompt untuk satu phase:

> Baca IMPLEMENTATION_PLAN.md dan EXECUTION_STATUS.md. Eksekusi Phase P00 saja sampai gate-nya terpenuhi. Periksa instruksi workspace, kerjakan keluaran yang direncanakan, verifikasi hasilnya, lalu perbarui EXECUTION_STATUS.md dengan bukti aktual. Jangan memulai phase berikutnya. Jika ada dependency eksternal yang belum tersedia, selesaikan bagian independen dan catat kebutuhan spesifiknya.

Contoh prompt untuk rentang phase:

> Baca plan dan tracker, lalu eksekusi P01 sampai P04 berurutan. Lanjutkan antar-phase setelah gate lulus tanpa konfirmasi rutin. Perbarui tracker setelah setiap phase. Jangan melewati pemeriksaan integritas atau mengubah data sumber untuk membuat hasil cocok dengan ekspektasi.

Contoh prompt melanjutkan pekerjaan:

> Lanjutkan implementasi dari phase pertama yang belum completed dalam EXECUTION_STATUS.md. Periksa dahulu bahwa keluaran dependency masih ada dan sesuai baseline. Gunakan catatan handoff agar tidak mengulang pekerjaan yang sudah valid, selesaikan phase aktif sampai gate lulus, dan perbarui bukti serta langkah berikutnya.

Contoh prompt seluruh implementasi lokal:

> Eksekusi P00 sampai P10 berdasarkan plan, lanjutkan selama dependency terpenuhi, dan siapkan paket P12 setelah status kebutuhan P11 dicatat. Tampilkan hasil lokal yang dapat ditinjau dan catat secara spesifik kebutuhan deployment/identitas yang belum tersedia. Jangan menyatakan saran deployment terpenuhi sebelum URL aktif terverifikasi.
