# Assessment P02 — bahan notebook

Dihasilkan oleh `scripts/assess_data.py` dari sumber mentah; tindakan berikut merupakan rencana P03/P04.

## Gathering Data

| Sumber | Peran | Baris | Kolom | Duplikasi persis tambahan |
| --- | --- | ---: | ---: | ---: |
| orders_dataset | formal | 99,441 | 8 | 0 |
| customers_dataset | formal | 99,441 | 5 | 0 |
| order_items_dataset | formal | 112,650 | 7 | 0 |
| products_dataset | formal | 32,951 | 9 | 0 |
| order_reviews_dataset | formal | 99,224 | 7 | 0 |
| product_category_name_translation | formal | 71 | 2 | 0 |
| order_payments_dataset | supporting_summary | 103,886 | 5 | 0 |
| sellers_dataset | supporting_summary | 3,095 | 4 | 0 |
| geolocation_dataset | supporting_summary | 1,000,163 | 5 | 261,831 |

Semua kolom awal berupa string; parsing hanya dilakukan pada salinan untuk assessment. Sembilan hash sumber cocok dengan baseline sebelum dan setelah assessment.

## Assessing Data

| Issue | Sumber/kolom | Jenis | Jumlah | Arti bisnis |
| --- | --- | --- | ---: | --- |
| DQ01 | products_dataset: product_category_name | missing_category | 610 products | Item tanpa kategori tidak dapat direkomendasikan sebagai kategori produk. |
| DQ02 | products_dataset: product_category_name | missing_translation | 13 products | Kode kategori ada tetapi tidak mempunyai nama Inggris. |
| DQ03 | order_reviews_dataset: order_id | multiple_reviews_per_order | 547 orders | Join ulasan mentah dapat memperbanyak nilai transaksi dan membobot skor secara keliru. |
| DQ04 | order_reviews_dataset: review_id | repeated_review_id | 814 additional_rows | Review ID berulang tidak membuktikan baris identik dan dapat terkait pesanan berbeda. |
| DQ05 | orders_dataset: order_delivered_customer_date, order_status | missing_lifecycle_date | 2,965 orders | Tanggal kosong harus dibaca menurut status; 8 delivered terdampak. |
| DQ06 | orders_dataset: order_delivered_carrier_date, order_status | missing_lifecycle_date | 1,783 orders | Tanggal kosong harus dibaca menurut status; 2 delivered terdampak. |
| DQ07 | orders_dataset: order_approved_at, order_status | missing_lifecycle_date | 160 orders | Tanggal kosong harus dibaca menurut status; 14 delivered terdampak. |
| DQ08 | order_reviews_dataset: review_comment_title | optional_text_missing | 87,658 review_rows | Teks ulasan opsional; skor tetap dapat dipakai. |
| DQ09 | order_reviews_dataset: review_comment_message | optional_text_missing | 58,274 review_rows | Teks ulasan opsional; skor tetap dapat dipakai. |
| DQ10 | products_dataset: product_name_lenght, product_description_lenght, product_photos_qty, product_weight_g, product_length_cm, product_height_cm, product_width_cm | missing_optional_product_attributes | 611 products | Atribut deskripsi dan ukuran tidak digunakan dalam Q1–Q3. |
| DQ11 | orders_dataset: order_purchase_timestamp, order_approved_at, order_delivered_carrier_date, order_delivered_customer_date | lifecycle_chronology | 1,382 orders_union | Urutan approval/kurir/penerimaan dapat terbalik; pengaruh terhadap metrik bergantung tanggal yang dipakai. |
| DQ12 | order_items_dataset: shipping_limit_date | shipping_deadline_after_purchase_snapshot | 4 item_rows | Batas pengiriman melampaui tanggal pembelian terakhir; tidak membuktikan transaksi sampai tahun tersebut. |
| DQ13 | orders_dataset: order_id, order_status | orders_without_items | 775 orders | Pesanan tanpa item tidak mempunyai nilai barang yang dapat dihitung. |
| DQ14 | orders_dataset: order_id | orders_without_review | 768 orders | Tidak semua pesanan memiliki skor untuk perbandingan. |
| DQ15 | order_payments_dataset: order_id | multiple_payments_per_order | 2,961 orders | Join pembayaran mentah berisiko menggandakan nilai item. |
| DQ16 | geolocation_dataset: geolocation_zip_code_prefix | nonunique_zip_prefix | 17,972 zip_prefixes | Satu kode pos memiliki banyak titik; bukan dimensi unik untuk join. |
| DQ17 | order_reviews_dataset: review_creation_date, order_id | review_calendar_before_purchase | 64 review_rows | Tanggal pembuatan ulasan mendahului tanggal pembelian sehingga metadata waktu ulasan perlu dicermati. |
| DQ18 | geolocation_dataset: geolocation_zip_code_prefix, geolocation_lat, geolocation_lng, geolocation_city, geolocation_state | exact_duplicate_supporting_rows | 261,831 additional_rows | Sumber pendukung mengandung titik identik berulang. |
| DQ19 | products_dataset: product_weight_g | zero_product_weight | 4 products | Berat nol perlu ditinjau jika analisis berat atau ongkos kirim dikembangkan. |
| DQ20 | orders_dataset: order_id | orders_without_payment | 1 orders | Cakupan sumber pembayaran tidak mencakup seluruh pesanan. |
| DQ21 | order_payments_dataset: payment_installments | zero_payment_installments | 2 payment_rows | Jumlah cicilan nol perlu dipahami sebelum analisis pembayaran. |

Jumlah antar-issue dapat tumpang tindih dan tidak boleh dijumlahkan menjadi total baris bermasalah.

## Steps to Take

| Issue | Tindakan | Metrik | Pemilik |
| --- | --- | --- | --- |
| DQ01 | Beri label Tidak diketahui; pertahankan nilai barang dalam total/denominator dan pisahkan dari top 5. | Q1 | P03 |
| DQ02 | Pertahankan kode asli sebagai kunci dan nama tampilan fallback; jangan gabungkan dengan kategori kosong. | Q1 | P03 |
| DQ03 | Pilih satu review per order: creation terbaru, answer terbaru, review_id leksikografis terbesar, lalu nomor baris sumber terbesar; null tanggal sebelum tanggal valid. Pilih sebelum validasi skor. | Q2, join_integrity | P03 |
| DQ04 | Jangan deduplikasi berdasarkan review_id; gunakan nomor baris sumber untuk audit dan pilih review pada tingkat order. | Q2 | P03 |
| DQ05 | Pertahankan NaT dan flag. Tanggal aktual hilang mengecualikan evaluasi keterlambatan; approval/carrier kosong tidak otomatis mengecualikan sales/RFM atau delivery yang tanggal wajibnya valid. | Q2, coverage | P03 |
| DQ06 | Pertahankan NaT dan flag. Tanggal aktual hilang mengecualikan evaluasi keterlambatan; approval/carrier kosong tidak otomatis mengecualikan sales/RFM atau delivery yang tanggal wajibnya valid. | Q2, coverage | P03 |
| DQ07 | Pertahankan NaT dan flag. Tanggal aktual hilang mengecualikan evaluasi keterlambatan; approval/carrier kosong tidak otomatis mengecualikan sales/RFM atau delivery yang tanggal wajibnya valid. | Q2, coverage | P03 |
| DQ08 | Tandai kosong termasuk whitespace untuk dokumentasi; jangan imputasi atau membuang skor valid. | Q2 | P03 |
| DQ09 | Tandai kosong termasuk whitespace untuk dokumentasi; jangan imputasi atau membuang skor valid. | Q2 | P03 |
| DQ10 | Parse numerik dengan audit dan pertahankan null; jangan imputasi ukuran atau menghapus item terkait. | documentation | P03 |
| DQ11 | Flag setiap pasangan tanggal tanpa menebak tanggal pengganti. Tanggal penerimaan sebelum pembelian membuat delivery tidak eligible; inversi approval/carrier saja tidak mengecualikan sales/RFM atau delivery. Estimasi sebelum tanggal pembelian harus diinvestigasi jika ditemukan. | Q2, coverage | P03 |
| DQ12 | Dokumentasikan sebagai anomali untuk inspeksi, pertahankan tanggal dan jangan gunakan sebagai batas periode analisis. | period_context | documentation |
| DQ13 | Pertahankan order; order_value null dan sales/RFM tidak eligible. Evaluasi delivery secara independen. | Q1, Q3, coverage | P04 |
| DQ14 | Pertahankan order; review null, tidak eligible untuk perbandingan skor. Delivery/sales tidak bergantung pada review. | Q2, coverage | P04 |
| DQ15 | Sumber pendukung; jika dipakai kelak, agregasikan per order sebelum join. Q1–Q3 memakai price item. | join_integrity | P04 |
| DQ16 | Simpan sebagai sumber pendukung; tidak digunakan untuk analisis negara bagian. Agregasikan dengan kebijakan eksplisit jika dipakai kelak. | join_integrity | documentation |
| DQ17 | Flag kronologi ulasan, pertahankan timestamp dan aturan seleksi deterministik plan. Skor integer 1–5 tetap tersedia; jangan mengubah tanggal atau membuang skor hanya karena anomali metadata ini. | Q2, review_selection | P03 |
| DQ18 | Catat tanpa mengubah sumber; belum perlu deduplikasi karena geolocation tidak dipakai Q1–Q3. Tinjau satuan baris sebelum analisis peta kelak. | documentation | documentation |
| DQ19 | Flag berat nol dan pertahankan nilai sumber; atribut tidak dipakai Q1–Q3 sehingga transaksi tidak dikeluarkan. | documentation | P03 |
| DQ20 | Dokumentasikan sumber pendukung; jangan mengubah nilai barang menjadi nol atau mengecualikan Q1–Q3 yang memakai item. | documentation | documentation |
| DQ21 | Catat tanpa imputasi; pembayaran tidak dipakai dalam Q1–Q3. Payment_value nol tidak otomatis invalid. | documentation | documentation |

## Konteks dan pemeriksaan tanpa pelanggaran

- Keunikan kunci wajib, missing per kolom/status, kegagalan parsing, domain skor, nilai negatif/nol, presisi sen, dan foreign key (termasuk hasil nol) tersedia di JSON.
- Kode pos geolocation bukan kunci unik. Duplikasi geolocation belum dihapus karena sumber tersebut tidak dipakai untuk Q1–Q3.
- Harga tinggi tidak dipangkas. Freight bernilai nol tetap valid; monetary berasal dari price item.
- Periode utama mengikuti config. Hitungan per bulan hanya menunjukkan kepadatan pencatatan, bukan bukti kelengkapan bulan atau tren bisnis final.
- Missing approval/carrier tidak otomatis membuktikan kesalahan pada semua status. Missing penerimaan pada delivered perlu dilaporkan sebagai keterbatasan evaluasi delivery.
- Tidak ada imputasi, seleksi ulasan, filter transaksi, atau ekspor tabel analisis pada P02.
