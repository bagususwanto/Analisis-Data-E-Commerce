"""Kontrak keluaran P04, dipakai untuk validasi dan metadata ekspor P08."""
from .config import ANALYSIS_START, ANALYSIS_END_EXCLUSIVE, CURRENCY, SALES_ORDER_STATUS


def field(dtype, unit, meaning, source, null_meaning=None):
    return dict(dtype=dtype, unit=unit, meaning=meaning, source=source,
                nullable=null_meaning is not None,
                null_meaning=null_meaning or 'Tidak boleh kosong')


ORDER_FIELDS = {
    'order_id': field('string', 'ID', 'Kunci satu pesanan', 'orders_dataset.order_id'),
    'customer_id': field('string', 'ID', 'Identitas pelanggan pada pesanan', 'orders_dataset.customer_id', 'Referensi pelanggan tidak tersedia'),
    'customer_unique_id': field('string', 'ID', 'Identitas pelanggan lintas pesanan', 'customers_dataset.customer_unique_id', 'Pelanggan tidak cocok atau identitas tidak tersedia'),
    'customer_state': field('string', 'kode negara bagian', 'Wilayah pelanggan pesanan', 'customers_dataset.customer_state', 'Pelanggan tidak cocok atau wilayah tidak tersedia'),
    'order_status': field('string', 'status', 'Status pada snapshot sumber', 'orders_dataset.order_status', 'Status tidak tersedia'),
    'order_purchase_timestamp': field('datetime64[ns]', 'timestamp tanpa timezone', 'Waktu pembelian sumber', 'orders_dataset.order_purchase_timestamp', 'Tanggal kosong atau gagal parsing'),
    'purchase_date': field('datetime64[ns]', 'tanggal kalender', 'Tanggal pembelian dinormalisasi ke tengah malam', 'order_purchase_timestamp', 'Waktu pembelian tidak tersedia'),
    'purchase_month': field('string', 'YYYY-MM', 'Bulan pembelian', 'order_purchase_timestamp', 'Waktu pembelian tidak tersedia'),
    'order_approved_at': field('datetime64[ns]', 'timestamp tanpa timezone', 'Waktu persetujuan', 'orders_dataset.order_approved_at', 'Tanggal kosong atau gagal parsing'),
    'order_delivered_carrier_date': field('datetime64[ns]', 'timestamp tanpa timezone', 'Waktu diserahkan ke kurir', 'orders_dataset.order_delivered_carrier_date', 'Tanggal kosong atau gagal parsing'),
    'order_delivered_customer_date': field('datetime64[ns]', 'timestamp tanpa timezone', 'Waktu penerimaan pelanggan', 'orders_dataset.order_delivered_customer_date', 'Tanggal kosong atau gagal parsing'),
    'order_estimated_delivery_date': field('datetime64[ns]', 'tanggal estimasi', 'Estimasi pengiriman sumber', 'orders_dataset.order_estimated_delivery_date', 'Tanggal kosong atau gagal parsing'),
    'order_value_cents': field('Int64', f'sen {CURRENCY}', 'Total price semua item; seluruh harga harus valid', 'order_items_dataset.price_cents; agregasi order_id', 'Pesanan tanpa item atau sedikitnya satu harga invalid; tidak dihitung sebagian'),
    'item_count': field('Int64', 'baris item', 'Jumlah item termasuk yang harganya invalid; nol jika tanpa item', 'order_items_dataset; count per order_id'),
    'valid_price_item_count': field('Int64', 'baris item', 'Jumlah item dengan harga valid', 'order_items_dataset.price_valid; count per order_id'),
    'invalid_price_item_count': field('Int64', 'baris item', 'Jumlah item dengan harga invalid', 'item_count - valid_price_item_count'),
    'has_items': field('boolean', 'flag', 'Ada sedikitnya satu item', 'item_count > 0'),
    'items_value_complete': field('boolean', 'flag', 'Ada item dan semua harganya valid', 'has_items; invalid_price_item_count; order_value_cents'),
    'customer_matched': field('boolean', 'flag', 'Referensi customer_id menemukan pelanggan', 'join orders -> customers'),
    'customer_identity_valid': field('boolean', 'flag', 'Pelanggan cocok dan customer_unique_id nonkosong', 'customer_matched; customers_dataset.customer_unique_id_valid'),
    'review_matched': field('boolean', 'flag', 'Tersedia satu review terpilih', 'join orders -> selected reviews'),
    'review_id': field('string', 'ID', 'Review terpilih; tidak unik lintas pesanan', 'order_reviews_dataset.review_id (P03)', 'Tidak ada review terpilih'),
    'review_score': field('Int64', 'skor 1–5', 'Skor dari review terpilih', 'order_reviews_dataset.review_score (P03)', 'Tidak ada review atau skor terpilih invalid'),
    'review_score_valid': field('boolean', 'flag', 'Review terpilih memiliki skor integer 1–5', 'review_matched; order_reviews_dataset.review_score_valid'),
    'review_candidate_count': field('Int64', 'baris review', 'Kandidat setelah exact dedup P03; nol jika tanpa review', 'order_reviews_dataset.review_candidate_count'),
    'review_created_before_purchase': field('boolean', 'flag', 'Metadata tanggal ulasan mendahului tanggal pembelian', 'order_reviews_dataset.review_created_before_purchase', 'Tidak ada review atau tanggal tidak dapat dibandingkan'),
    'has_lifecycle_chronology_issue': field('boolean', 'flag', 'Ada inversi urutan tanggal yang teramati', 'orders_dataset.has_lifecycle_chronology_issue (P03)'),
    'delivery_dates_valid': field('boolean', 'flag', 'Tanggal pembelian/aktual/estimasi valid; penerimaan dan tanggal estimasi tidak mendahului pembelian', 'orders_dataset.delivery_dates_valid (P03)'),
    'is_late': field('boolean', 'flag', 'Tanggal kalender penerimaan melewati estimasi; status/periode belum diterapkan', 'orders_dataset.is_late (P03)', 'Pasangan tanggal tidak dapat dievaluasi; bukan tepat waktu'),
    'days_late': field('Int64', 'hari kalender', 'Selisih aktual-estimasi dengan minimum nol', 'orders_dataset.days_late (P03)', 'Pasangan tanggal tidak dapat dievaluasi; bukan nol hari'),
    'in_analysis_period': field('boolean', 'flag', f'{ANALYSIS_START} <= pembelian < {ANALYSIS_END_EXCLUSIVE}', 'order_purchase_timestamp; src.config'),
    'eligible_sales': field('boolean', 'flag', f'Dalam periode; {SALES_ORDER_STATUS}; ada item; seluruh harga valid', 'in_analysis_period; order_status; has_items; items_value_complete'),
    'eligible_delivery': field('boolean', 'flag', f'Dalam periode; {SALES_ORDER_STATUS}; tanggal delivery valid', 'in_analysis_period; order_status; delivery_dates_valid'),
    'eligible_review_comparison': field('boolean', 'flag', 'Eligible delivery dan skor review terpilih valid', 'eligible_delivery; review_score_valid'),
    'eligible_rfm': field('boolean', 'flag', 'Eligible sales dan identitas pelanggan unik valid', 'eligible_sales; customer_identity_valid'),
}

ITEM_FIELDS = {
    'order_id': field('string', 'ID', 'Bagian kunci order/item', 'order_items_dataset.order_id'),
    'order_item_id': field('string', 'ID urutan item', 'Bagian kunci order/item; bentuk teks sumber', 'order_items_dataset.order_item_id'),
    'product_id': field('string', 'ID', 'Referensi produk', 'order_items_dataset.product_id', 'Referensi produk kosong'),
    'seller_id': field('string', 'ID', 'Referensi penjual; sumber penjual belum dipakai', 'order_items_dataset.seller_id', 'Referensi penjual kosong'),
    'price_cents': field('Int64', f'sen {CURRENCY}', 'Nilai barang per item, tidak termasuk freight', 'order_items_dataset.price_cents (P03)', 'Harga sumber kosong/invalid; lihat price_valid'),
    'price_valid': field('boolean', 'flag', 'Harga item valid, termasuk harga nol', 'order_items_dataset.price_valid (P03)'),
    'freight_cents': field('Int64', f'sen {CURRENCY}', 'Ongkos kirim per item', 'order_items_dataset.freight_cents (P03)', 'Freight sumber kosong/invalid; tidak otomatis membatalkan sales'),
    'order_matched': field('boolean', 'flag', 'Referensi order_id menemukan pesanan', 'join items -> order_level'),
    'customer_id': field('string', 'ID', 'Identitas pelanggan pada pesanan', 'order_level.customer_id', 'Pesanan tidak cocok atau referensi tidak tersedia'),
    'customer_unique_id': field('string', 'ID', 'Identitas pelanggan lintas pesanan', 'order_level.customer_unique_id', 'Pesanan/pelanggan tidak cocok atau identitas tidak tersedia'),
    'customer_state': field('string', 'kode negara bagian', 'Wilayah pelanggan pesanan', 'order_level.customer_state', 'Pesanan/pelanggan tidak cocok atau wilayah tidak tersedia'),
    'order_status': field('string', 'status', 'Status snapshot pesanan', 'order_level.order_status', 'Pesanan tidak cocok atau status tidak tersedia'),
    'order_purchase_timestamp': field('datetime64[ns]', 'timestamp tanpa timezone', 'Waktu pembelian pesanan', 'order_level.order_purchase_timestamp', 'Pesanan tidak cocok atau waktu tidak tersedia'),
    'purchase_date': field('datetime64[ns]', 'tanggal kalender', 'Tanggal pembelian dinormalisasi', 'order_level.purchase_date', 'Waktu pembelian tidak tersedia'),
    'purchase_month': field('string', 'YYYY-MM', 'Bulan pembelian pesanan', 'order_level.purchase_month', 'Waktu pembelian tidak tersedia'),
    'in_analysis_period': field('boolean', 'flag', 'Pesanan dalam periode utama; false untuk referensi order tidak cocok', 'order_level.in_analysis_period'),
    'eligible_sales': field('boolean', 'flag', 'Eligibility seluruh order; semua item order invalid dikeluarkan bersama', 'order_level.eligible_sales; order_matched'),
    'product_matched': field('boolean', 'flag', 'Referensi product_id menemukan produk', 'join items -> products'),
    'category_code': field('string', 'kode kategori sumber', 'Kunci kategori; terjemahan tidak mengubah kode', 'products_dataset.category_code (P03)', 'Kategori kosong atau produk tidak cocok'),
    'category_name': field('string', 'nama kategori', 'Nama Inggris, fallback kode sumber, atau label Tidak diketahui', 'translation.product_category_name_english; category_code; src.config'),
    'category_missing': field('boolean', 'flag', 'Kode kategori tidak tersedia, termasuk produk yang tidak cocok', 'category_code'),
    'category_translation_matched': field('boolean', 'flag', 'Kode kategori menemukan baris terjemahan', 'join item category_code -> translation'),
    'category_translation_missing': field('boolean', 'flag', 'Kode kategori ada tetapi nama terjemahan tidak tersedia', 'category_code; translation.product_category_name_english'),
}

TABLE_CONTRACTS = {
    'order_level': {'grain': 'Satu baris per pesanan; seluruh status dipertahankan',
                    'primary_key': ['order_id'], 'fields': ORDER_FIELDS},
    'item_level': {'grain': 'Satu baris per pasangan order/item; denominator Q2 memakai order_level',
                   'primary_key': ['order_id','order_item_id'], 'fields': ITEM_FIELDS},
}


def conform_table(frame, table):
    """Proyeksikan kolom final, tipe eksplisit, nullability, dan keunikan kunci."""
    from .data_pipeline import DataQualityError
    contract = TABLE_CONTRACTS[table]
    missing = set(contract['fields']) - set(frame.columns)
    if missing:
        raise DataQualityError(f'{table}: kolom kontrak hilang: {sorted(missing)}')
    result = frame[list(contract['fields'])].copy()
    for name, spec in contract['fields'].items():
        result[name] = result[name].astype(spec['dtype'])
        if not spec['nullable'] and result[name].isna().any():
            raise DataQualityError(f'{table}.{name}: null melanggar kontrak')
    if result.duplicated(contract['primary_key']).any():
        raise DataQualityError(f'{table}: kunci keluaran tidak unik')
    return result.reset_index(drop=True)


# Kontrak RFM terpisah: registry P04 tetap hanya order/item yang dibangunnya.
RFM_CUSTOMER_CONTRACT = {
    'grain':'Satu baris per customer_unique_id; metrik seluruh periode acuan',
    'primary_key':['customer_unique_id'],
    'fields':{
        'customer_unique_id':field('string','ID','Identitas pelanggan lintas pesanan','order_level.customer_unique_id'),
        'last_order_id':field('string','ID','Order eligible terakhir; tie timestamp lalu order_id leksikografis terbesar','order_level.order_id'),
        'last_purchase_timestamp':field('datetime64[ns]','timestamp tanpa timezone','Waktu pembelian eligible terakhir','order_level.order_purchase_timestamp'),
        'last_purchase_date':field('datetime64[ns]','tanggal kalender','Tanggal pembelian eligible terakhir, dinormalisasi','last_purchase_timestamp'),
        'last_order_state':field('string','kode negara bagian','Wilayah pesanan terakhir; filter tidak menghitung ulang R/F/M','order_level.customer_state pada last_order_id','Wilayah pesanan terakhir tidak tersedia; tidak diganti wilayah order lama'),
        'recency_days':field('Int64','hari kalender','Tanggal acuan dikurangi last_purchase_date','src.config.RFM_REFERENCE_DATE; last_purchase_date'),
        'frequency':field('Int64','pesanan unik','Jumlah order eligible pelanggan dalam periode acuan','order_level.order_id dengan eligible_rfm'),
        'monetary_cents':field('Int64',f'sen {CURRENCY}','Jumlah nilai barang seluruh order eligible pelanggan, tidak termasuk freight','order_level.order_value_cents dengan eligible_rfm'),
        'segment':field('string','segmen manual','Satu dari lima segmen mutually exclusive menurut recency/frequency','src.config.RFM_SEGMENTS; RECENCY_NEW_DAYS; RECENCY_ACTIVE_DAYS'),
        'is_high_value':field('boolean','flag','Monetary >= P75 global; pembandingan rasio integer tanpa pembulatan','monetary_cents; metadata ambang dari build_rfm'),
    },
}
