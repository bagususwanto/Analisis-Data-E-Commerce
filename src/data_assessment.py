"""Assessment P02: observasi mentah dan rencana tindakan, tanpa cleaning sumber."""
from decimal import Decimal, InvalidOperation
from itertools import combinations

import pandas as pd

from .config import ANALYSIS_START, ANALYSIS_END_EXCLUSIVE, PRIMARY_SOURCES
from .data_pipeline import load_source

DATE_COLUMNS = {
    'orders_dataset': ('order_purchase_timestamp', 'order_approved_at',
                       'order_delivered_carrier_date', 'order_delivered_customer_date',
                       'order_estimated_delivery_date'),
    'order_items_dataset': ('shipping_limit_date',),
    'order_reviews_dataset': ('review_creation_date', 'review_answer_timestamp'),
}
NUMERIC_COLUMNS = {
    'order_items_dataset': ('order_item_id', 'price', 'freight_value'),
    'products_dataset': ('product_name_lenght', 'product_description_lenght',
                         'product_photos_qty', 'product_weight_g', 'product_length_cm',
                         'product_height_cm', 'product_width_cm'),
    'order_reviews_dataset': ('review_score',),
    'order_payments_dataset': ('payment_sequential', 'payment_installments', 'payment_value'),
    'geolocation_dataset': ('geolocation_lat', 'geolocation_lng'),
}
MONEY_COLUMNS = {'price', 'freight_value', 'payment_value'}
KEYS = {
    'orders_dataset': ('order_id',), 'customers_dataset': ('customer_id',),
    'products_dataset': ('product_id',),
    'product_category_name_translation': ('product_category_name',),
    'order_items_dataset': ('order_id', 'order_item_id'),
    'sellers_dataset': ('seller_id',),
}


def blank(series):
    """Field kosong atau hanya whitespace; tidak mengubah Series sumber."""
    return series.isna() | series.str.strip().eq('').fillna(False)


def key_profile(frame, columns):
    missing = frame[list(columns)].apply(blank).any(axis=1)
    valid = frame.loc[~missing]
    duplicate = valid.duplicated(list(columns), keep=False)
    return {
        'columns': list(columns), 'rows_with_missing_key': int(missing.sum()),
        'distinct_nonmissing_keys': int(len(valid.drop_duplicates(list(columns)))),
        'rows_in_duplicate_keys': int(duplicate.sum()),
        'additional_duplicate_keys': int(valid.duplicated(list(columns)).sum()),
        'duplicate_key_groups': int(len(valid.loc[duplicate, list(columns)].drop_duplicates())),
        'unique_and_complete': bool(not missing.any() and not duplicate.any()),
    }


def numeric_profile(series, *, money=False):
    counts = dict(nonmissing=0, missing=int(blank(series).sum()), parse_failures=0,
                  nonfinite=0, negative=0, zero=0, noninteger=0)
    if money:
        counts['beyond_cent_precision'] = 0
    values = []
    for raw, frequency in series.loc[~blank(series)].value_counts().items():
        n = int(frequency)
        counts['nonmissing'] += n
        try:
            value = Decimal(raw)
        except InvalidOperation:
            counts['parse_failures'] += n
            continue
        if not value.is_finite():
            counts['nonfinite'] += n
            continue
        values.append(value)
        counts['negative'] += n if value < 0 else 0
        counts['zero'] += n if value == 0 else 0
        counts['noninteger'] += n if value != value.to_integral_value() else 0
        if money and value * 100 != (value * 100).to_integral_value():
            counts['beyond_cent_precision'] += n
    counts['min'] = str(min(values)) if values else None
    counts['max'] = str(max(values)) if values else None
    return counts


def profile_source(name, frame):
    profile = {
        'scope': 'formal' if name in PRIMARY_SOURCES else 'supporting_summary',
        'row_count': len(frame), 'column_count': len(frame.columns),
        'columns': list(frame.columns),
        'raw_dtypes': {c: str(frame[c].dtype) for c in frame},
        'empty_field_counts': {c: int(frame[c].isna().sum()) for c in frame},
        'missing_including_whitespace': {c: int(blank(frame[c]).sum()) for c in frame},
        'whitespace_only_counts': {c: int((~frame[c].isna() & blank(frame[c])).sum()) for c in frame},
        'surrounding_whitespace_counts': {
            c: int((frame[c].notna() & frame[c].ne(frame[c].str.strip())).sum()) for c in frame
        },
        'exact_duplicate_additional_rows': int(frame.duplicated().sum()),
        'exact_duplicate_all_rows': int(frame.duplicated(keep=False).sum()),
        'dates': {}, 'numeric': {},
    }
    if name in KEYS:
        profile['key'] = key_profile(frame, KEYS[name])
    for col in DATE_COLUMNS.get(name, ()):
        parsed = pd.to_datetime(frame[col], format='%Y-%m-%d %H:%M:%S', errors='coerce')
        profile['dates'][col] = {
            'missing': int(blank(frame[col]).sum()),
            'parse_failures': int((~blank(frame[col]) & parsed.isna()).sum()),
            'min': str(parsed.min()) if parsed.notna().any() else None,
            'max': str(parsed.max()) if parsed.notna().any() else None,
        }
    for col in NUMERIC_COLUMNS.get(name, ()):
        profile['numeric'][col] = numeric_profile(frame[col], money=col in MONEY_COLUMNS)
    return profile


def assess_sources():
    """Muat sumber melalui loader P01; kembalikan bukti dan issue register."""
    frames = {name: load_source(name) for name in PRIMARY_SOURCES}
    profiles = {name: profile_source(name, frame) for name, frame in frames.items()}
    # Sumber pendukung dibaca satu per satu untuk membatasi pemakaian memori.
    for name in ('order_payments_dataset', 'sellers_dataset', 'geolocation_dataset'):
        frames[name] = load_source(name)
        profiles[name] = profile_source(name, frames[name])
        if name == 'geolocation_dataset':
            profiles[name]['zip_prefix'] = key_profile(frames[name], ('geolocation_zip_code_prefix',))
            geo = frames.pop(name)
            del geo
    orders = frames['orders_dataset']
    items = frames['order_items_dataset']
    products = frames['products_dataset']
    reviews = frames['order_reviews_dataset']
    customers = frames['customers_dataset']
    translation = frames['product_category_name_translation']
    dates = {col: pd.to_datetime(orders[col], format='%Y-%m-%d %H:%M:%S', errors='coerce')
             for col in DATE_COLUMNS['orders_dataset']}
    purchase = dates['order_purchase_timestamp']
    in_period = purchase.ge(pd.Timestamp(ANALYSIS_START)) & purchase.lt(pd.Timestamp(ANALYSIS_END_EXCLUSIVE))
    delivered = orders['order_status'].eq('delivered')
    status = {str(k): int(v) for k, v in orders['order_status'].value_counts(dropna=False).sort_index().items()}
    profiles['orders_dataset']['status_counts'] = status
    month_counts = purchase.dt.to_period('M').value_counts().reindex(
        pd.period_range(purchase.min(), purchase.max(), freq='M'), fill_value=0)
    by_status = {}
    for state, group in orders.groupby('order_status', dropna=False):
        by_status[str(state)] = {
            'rows': len(group),
            'missing_dates': {col: int(blank(group[col]).sum()) for col in DATE_COLUMNS['orders_dataset']},
            'orders_without_items': int((~group['order_id'].isin(items['order_id'])).sum()),
            'orders_without_review': int((~group['order_id'].isin(reviews['order_id'])).sum()),
        }
    chronology = {}
    lifecycle = ('order_purchase_timestamp', 'order_approved_at',
                 'order_delivered_carrier_date', 'order_delivered_customer_date')
    for earlier, later in combinations(lifecycle, 2):
        comparable = dates[earlier].notna() & dates[later].notna()
        invalid = comparable & dates[later].lt(dates[earlier])
        calendar_invalid = comparable & dates[later].dt.normalize().lt(dates[earlier].dt.normalize())
        chronology[f'{later}_before_{earlier}'] = {
            'comparable_rows': int(comparable.sum()), 'affected_rows': int(invalid.sum()),
            'affected_delivered': int((invalid & delivered).sum()),
            'affected_in_period_delivered': int((invalid & delivered & in_period).sum()),
            'calendar_date_affected_rows': int(calendar_invalid.sum()),
        }
    estimate_before_purchase = dates['order_estimated_delivery_date'].dt.normalize().lt(purchase.dt.normalize())
    chronology['estimated_calendar_date_before_purchase'] = {
        'comparable_rows': int((dates['order_estimated_delivery_date'].notna() & purchase.notna()).sum()),
        'affected_rows': int(estimate_before_purchase.sum()),
        'affected_delivered': int((estimate_before_purchase & delivered).sum()),
        'affected_in_period_delivered': int((estimate_before_purchase & delivered & in_period).sum()),
    }
    fk = {}
    relations = [
        ('orders_dataset', 'customer_id', 'customers_dataset', 'customer_id'),
        ('order_items_dataset', 'order_id', 'orders_dataset', 'order_id'),
        ('order_items_dataset', 'product_id', 'products_dataset', 'product_id'),
        ('order_items_dataset', 'seller_id', 'sellers_dataset', 'seller_id'),
        ('order_reviews_dataset', 'order_id', 'orders_dataset', 'order_id'),
        ('products_dataset', 'product_category_name', 'product_category_name_translation', 'product_category_name'),
        ('order_payments_dataset', 'order_id', 'orders_dataset', 'order_id'),
    ]
    for child, ccol, parent, pcol in relations:
        series = frames[child][ccol]
        missing = blank(series)
        unmatched = ~missing & ~series.isin(frames[parent][pcol])
        fk[f'{child}.{ccol} -> {parent}.{pcol}'] = {
            'child_rows': len(series), 'missing_key_rows': int(missing.sum()),
            'unmatched_nonmissing_rows': int(unmatched.sum()),
            'unmatched_distinct_keys': int(series[unmatched].nunique()),
            'unmatched_key_examples': sorted(series[unmatched].drop_duplicates().tolist())[:5],
        }
    review_keys = {col: key_profile(reviews, (col,)) for col in ('review_id', 'order_id')}
    review_keys['review_id_order_id'] = key_profile(reviews, ('review_id', 'order_id'))
    review_keys['review_ids_linked_to_multiple_orders'] = int(
        reviews.groupby('review_id')['order_id'].nunique().gt(1).sum())
    pair_counts = reviews.groupby(['review_id', 'order_id']).size()
    review_keys['repeated_id_order_pairs'] = int(pair_counts.gt(1).sum())
    scores = pd.to_numeric(reviews['review_score'], errors='coerce')
    valid_scores = scores.isin([1, 2, 3, 4, 5])
    review_keys['score_validity'] = {
        'missing': int(blank(reviews['review_score']).sum()),
        'noninteger': int((scores.notna() & scores.mod(1).ne(0)).sum()),
        'out_of_range': int((scores.notna() & ~scores.between(1, 5)).sum()),
        'invalid_or_missing': int((~valid_scores).sum()),
        'score_counts': {str(k): int(v) for k, v in reviews['review_score'].value_counts(dropna=False).sort_index().items()},
    }
    review_created = pd.to_datetime(reviews['review_creation_date'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    review_answer = pd.to_datetime(reviews['review_answer_timestamp'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    review_purchase = reviews['order_id'].map(pd.Series(purchase.array, index=orders['order_id']))
    review_keys['answer_before_creation'] = int(review_answer.lt(review_created).sum())
    review_keys['creation_calendar_before_purchase'] = int(review_created.dt.normalize().lt(review_purchase.dt.normalize()).sum())
    review_keys['latest_creation_timestamp_tied_orders'] = int(
        reviews.loc[review_created.eq(review_created.groupby(reviews['order_id']).transform('max'))]
        .groupby('order_id').size().gt(1).sum())
    payment_counts = frames['order_payments_dataset'].groupby('order_id').size()
    category_missing = blank(products['product_category_name'])
    category_untranslated = ~category_missing & ~products['product_category_name'].isin(translation['product_category_name'])
    missing_product_ids = products.loc[category_missing, 'product_id']
    untranslated_product_ids = products.loc[category_untranslated, 'product_id']
    ship = pd.to_datetime(items['shipping_limit_date'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    ship_after_snapshot = ship.ge(purchase.max().normalize() + pd.Timedelta(days=1))
    item_purchase = items['order_id'].map(pd.Series(purchase.array, index=orders['order_id']))
    shipping_before_purchase = ship.lt(item_purchase)
    facts = {
        'order_status_counts': status, 'missing_and_coverage_by_status': by_status,
        'purchase_month_counts': {str(k): int(v) for k, v in month_counts.items()},
        'analysis_period_order_count': int(in_period.sum()),
        'analysis_period_delivered_count': int((in_period & delivered).sum()),
        'date_chronology': chronology, 'foreign_keys': fk, 'reviews': review_keys,
        'delivered_missing_dates': {col: {
            'all_periods': int((delivered & blank(orders[col])).sum()),
            'analysis_period': int((delivered & in_period & blank(orders[col])).sum()),
        } for col in DATE_COLUMNS['orders_dataset']},
        'categories': {
            'missing_products': int(category_missing.sum()),
            'missing_category_item_rows': int(items['product_id'].isin(missing_product_ids).sum()),
            'untranslated_products': int(category_untranslated.sum()),
            'untranslated_codes': sorted(products.loc[category_untranslated, 'product_category_name'].unique().tolist()),
            'untranslated_category_item_rows': int(items['product_id'].isin(untranslated_product_ids).sum()),
            'translation_missing_english_rows': int(blank(translation['product_category_name_english']).sum()),
        },
        'shipping_limit': {
            'after_last_purchase_calendar_day_rows': int(ship_after_snapshot.sum()),
            'after_last_purchase_affected_orders': int(items.loc[ship_after_snapshot, 'order_id'].nunique()),
            'before_purchase_timestamp_rows': int(shipping_before_purchase.sum()),
            'after_last_purchase_year_counts': {str(k): int(v) for k, v in ship[ship_after_snapshot].dt.year.value_counts().sort_index().items()},
        },
        'supporting': {
            'orders_with_multiple_payments': int(payment_counts.gt(1).sum()),
            'additional_payment_rows_per_order': int((payment_counts - 1).sum()),
            'payment_key': key_profile(frames['order_payments_dataset'], ('order_id', 'payment_sequential')),
            'orders_without_payment': int((~orders['order_id'].isin(frames['order_payments_dataset']['order_id'])).sum()),
        },
    }
    issues = []
    def issue(issue_id, source, columns, kind, count, unit, meaning, action, metrics, evidence, *, role='cleaning'):
        if count:
            issues.append(dict(issue_id=issue_id, source=source, columns=list(columns), kind=kind,
                affected_count=int(count), affected_unit=unit, business_meaning=meaning,
                planned_action=action, affected_metrics=list(metrics), evidence=evidence,
                owner_phase='P03' if role == 'cleaning' else role, status='assessed_action_pending'))
    issue('DQ01', 'products_dataset', ['product_category_name'], 'missing_category', category_missing.sum(), 'products',
          'Item tanpa kategori tidak dapat direkomendasikan sebagai kategori produk.',
          'Beri label Tidak diketahui; pertahankan nilai barang dalam total/denominator dan pisahkan dari top 5.',
          ['Q1'], 'facts.categories')
    issue('DQ02', 'products_dataset', ['product_category_name'], 'missing_translation', category_untranslated.sum(), 'products',
          'Kode kategori ada tetapi tidak mempunyai nama Inggris.',
          'Pertahankan kode asli sebagai kunci dan nama tampilan fallback; jangan gabungkan dengan kategori kosong.',
          ['Q1'], 'facts.categories')
    issue('DQ03', 'order_reviews_dataset', ['order_id'], 'multiple_reviews_per_order', review_keys['order_id']['duplicate_key_groups'], 'orders',
          'Join ulasan mentah dapat memperbanyak nilai transaksi dan membobot skor secara keliru.',
          'Pilih satu review per order: creation terbaru, answer terbaru, review_id leksikografis terbesar, lalu nomor baris sumber terbesar; null tanggal sebelum tanggal valid. Pilih sebelum validasi skor.',
          ['Q2', 'join_integrity'], 'facts.reviews.order_id')
    issue('DQ04', 'order_reviews_dataset', ['review_id'], 'repeated_review_id', review_keys['review_id']['additional_duplicate_keys'], 'additional_rows',
          'Review ID berulang tidak membuktikan baris identik dan dapat terkait pesanan berbeda.',
          'Jangan deduplikasi berdasarkan review_id; gunakan nomor baris sumber untuk audit dan pilih review pada tingkat order.',
          ['Q2'], 'facts.reviews')
    for col, ident in [('order_delivered_customer_date', 'DQ05'), ('order_delivered_carrier_date', 'DQ06'), ('order_approved_at', 'DQ07')]:
        issue(ident, 'orders_dataset', [col, 'order_status'], 'missing_lifecycle_date', blank(orders[col]).sum(), 'orders',
              f'Tanggal kosong harus dibaca menurut status; {facts["delivered_missing_dates"][col]["all_periods"]} delivered terdampak.',
              'Pertahankan NaT dan flag. Tanggal aktual hilang mengecualikan evaluasi keterlambatan; approval/carrier kosong tidak otomatis mengecualikan sales/RFM atau delivery yang tanggal wajibnya valid.',
              ['Q2', 'coverage'], 'facts.missing_and_coverage_by_status; facts.delivered_missing_dates')
    for col, ident in [('review_comment_title', 'DQ08'), ('review_comment_message', 'DQ09')]:
        issue(ident, 'order_reviews_dataset', [col], 'optional_text_missing', blank(reviews[col]).sum(), 'review_rows',
              'Teks ulasan opsional; skor tetap dapat dipakai.',
              'Tandai kosong termasuk whitespace untuk dokumentasi; jangan imputasi atau membuang skor valid.',
              ['Q2'], f'profiles.order_reviews_dataset.missing_including_whitespace.{col}')
    product_attributes = [c for c in products if c not in ('product_id', 'product_category_name')]
    attr_missing = products[product_attributes].apply(blank).any(axis=1)
    issue('DQ10', 'products_dataset', product_attributes, 'missing_optional_product_attributes', attr_missing.sum(), 'products',
          'Atribut deskripsi dan ukuran tidak digunakan dalam Q1–Q3.',
          'Parse numerik dengan audit dan pertahankan null; jangan imputasi ukuran atau menghapus item terkait.',
          ['documentation'], 'profiles.products_dataset.missing_including_whitespace')
    lifecycle_masks = [dates[later].lt(dates[earlier]) for earlier, later in combinations(lifecycle, 2)]
    any_chronology = pd.concat(lifecycle_masks, axis=1).any(axis=1) | estimate_before_purchase
    facts['orders_with_any_lifecycle_or_estimate_chronology_issue'] = int(any_chronology.sum())
    issue('DQ11', 'orders_dataset', lifecycle, 'lifecycle_chronology', any_chronology.sum(), 'orders_union',
          'Urutan approval/kurir/penerimaan dapat terbalik; pengaruh terhadap metrik bergantung tanggal yang dipakai.',
          'Flag setiap pasangan tanggal tanpa menebak tanggal pengganti. Tanggal penerimaan sebelum pembelian membuat delivery tidak eligible; inversi approval/carrier saja tidak mengecualikan sales/RFM atau delivery. Estimasi sebelum tanggal pembelian harus diinvestigasi jika ditemukan.',
          ['Q2', 'coverage'], 'facts.date_chronology')
    issue('DQ12', 'order_items_dataset', ['shipping_limit_date'], 'shipping_deadline_after_purchase_snapshot', ship_after_snapshot.sum(), 'item_rows',
          'Batas pengiriman melampaui tanggal pembelian terakhir; tidak membuktikan transaksi sampai tahun tersebut.',
          'Dokumentasikan sebagai anomali untuk inspeksi, pertahankan tanggal dan jangan gunakan sebagai batas periode analisis.',
          ['period_context'], 'facts.shipping_limit', role='documentation')
    no_items = ~orders['order_id'].isin(items['order_id'])
    facts['orders_without_items'] = int(no_items.sum())
    facts['delivered_orders_without_items'] = int((no_items & delivered).sum())
    issue('DQ13', 'orders_dataset', ['order_id', 'order_status'], 'orders_without_items', no_items.sum(), 'orders',
          'Pesanan tanpa item tidak mempunyai nilai barang yang dapat dihitung.',
          'Pertahankan order; order_value null dan sales/RFM tidak eligible. Evaluasi delivery secara independen.',
          ['Q1', 'Q3', 'coverage'], 'facts.missing_and_coverage_by_status', role='P04')
    no_review = ~orders['order_id'].isin(reviews['order_id'])
    facts['orders_without_review'] = int(no_review.sum())
    issue('DQ14', 'orders_dataset', ['order_id'], 'orders_without_review', no_review.sum(), 'orders',
          'Tidak semua pesanan memiliki skor untuk perbandingan.',
          'Pertahankan order; review null, tidak eligible untuk perbandingan skor. Delivery/sales tidak bergantung pada review.',
          ['Q2', 'coverage'], 'facts.missing_and_coverage_by_status', role='P04')
    issue('DQ15', 'order_payments_dataset', ['order_id'], 'multiple_payments_per_order', facts['supporting']['orders_with_multiple_payments'], 'orders',
          'Join pembayaran mentah berisiko menggandakan nilai item.',
          'Sumber pendukung; jika dipakai kelak, agregasikan per order sebelum join. Q1–Q3 memakai price item.',
          ['join_integrity'], 'facts.supporting', role='P04')
    issue('DQ16', 'geolocation_dataset', ['geolocation_zip_code_prefix'], 'nonunique_zip_prefix', profiles['geolocation_dataset']['zip_prefix']['duplicate_key_groups'], 'zip_prefixes',
          'Satu kode pos memiliki banyak titik; bukan dimensi unik untuk join.',
          'Simpan sebagai sumber pendukung; tidak digunakan untuk analisis negara bagian. Agregasikan dengan kebijakan eksplisit jika dipakai kelak.',
          ['join_integrity'], 'profiles.geolocation_dataset.zip_prefix', role='documentation')
    issue('DQ17', 'order_reviews_dataset', ['review_creation_date', 'order_id'], 'review_calendar_before_purchase', review_keys['creation_calendar_before_purchase'], 'review_rows',
          'Tanggal pembuatan ulasan mendahului tanggal pembelian sehingga metadata waktu ulasan perlu dicermati.',
          'Flag kronologi ulasan, pertahankan timestamp dan aturan seleksi deterministik plan. Skor integer 1–5 tetap tersedia; jangan mengubah tanggal atau membuang skor hanya karena anomali metadata ini.',
          ['Q2', 'review_selection'], 'facts.reviews.creation_calendar_before_purchase')
    issue('DQ18', 'geolocation_dataset', profiles['geolocation_dataset']['columns'], 'exact_duplicate_supporting_rows', profiles['geolocation_dataset']['exact_duplicate_additional_rows'], 'additional_rows',
          'Sumber pendukung mengandung titik identik berulang.',
          'Catat tanpa mengubah sumber; belum perlu deduplikasi karena geolocation tidak dipakai Q1–Q3. Tinjau satuan baris sebelum analisis peta kelak.',
          ['documentation'], 'profiles.geolocation_dataset.exact_duplicate_additional_rows', role='documentation')
    issue('DQ19', 'products_dataset', ['product_weight_g'], 'zero_product_weight', profiles['products_dataset']['numeric']['product_weight_g']['zero'], 'products',
          'Berat nol perlu ditinjau jika analisis berat atau ongkos kirim dikembangkan.',
          'Flag berat nol dan pertahankan nilai sumber; atribut tidak dipakai Q1–Q3 sehingga transaksi tidak dikeluarkan.',
          ['documentation'], 'profiles.products_dataset.numeric.product_weight_g')
    issue('DQ20', 'orders_dataset', ['order_id'], 'orders_without_payment', facts['supporting']['orders_without_payment'], 'orders',
          'Cakupan sumber pembayaran tidak mencakup seluruh pesanan.',
          'Dokumentasikan sumber pendukung; jangan mengubah nilai barang menjadi nol atau mengecualikan Q1–Q3 yang memakai item.',
          ['documentation'], 'facts.supporting.orders_without_payment', role='documentation')
    issue('DQ21', 'order_payments_dataset', ['payment_installments'], 'zero_payment_installments', profiles['order_payments_dataset']['numeric']['payment_installments']['zero'], 'payment_rows',
          'Jumlah cicilan nol perlu dipahami sebelum analisis pembayaran.',
          'Catat tanpa imputasi; pembayaran tidak dipakai dalam Q1–Q3. Payment_value nol tidak otomatis invalid.',
          ['documentation'], 'profiles.order_payments_dataset.numeric.payment_installments', role='documentation')
    # Tambahkan masalah generik jika sumber aktual mengandung pelanggaran yang belum dicakup.
    for name, profile in profiles.items():
        if name in KEYS:
            key = profile['key']
            issue(f'KEY-{name}', name, KEYS[name], 'missing_or_conflicting_required_key',
                  key['rows_with_missing_key'] + key['rows_in_duplicate_keys'], 'rows',
                  'Kunci wajib belum aman untuk join tervalidasi.',
                  'Inspeksi konflik; jangan memilih baris arbitrer. Hentikan join terkait sampai keputusan terukur tersedia.',
                  ['join_integrity'], f'profiles.{name}.key')
        for col, detail in profile['dates'].items():
            issue(f'DATE-{name}-{col}', name, [col], 'date_parse_failure', detail['parse_failures'], 'rows',
                  'Tanggal tidak dapat dievaluasi.', 'Coerce ke NaT dengan flag parsing dan laporkan pengecualian metrik.',
                  ['coverage'], f'profiles.{name}.dates.{col}')
        for col, detail in profile['numeric'].items():
            invalid = detail['parse_failures'] + detail['nonfinite']
            if col in MONEY_COLUMNS:
                invalid += detail['negative'] + detail['beyond_cent_precision']
            issue(f'NUM-{name}-{col}', name, [col], 'invalid_numeric', invalid, 'rows',
                  'Nilai tidak aman untuk agregasi numerik/uang.',
                  'Flag nilai invalid; untuk uang dengan presisi di luar sen selesaikan kebijakan sebelum konversi, tanpa pembulatan diam-diam. Harga invalid membuat seluruh order tidak eligible sales.',
                  ['Q1', 'Q3', 'coverage'], f'profiles.{name}.numeric.{col}')
        if name != 'geolocation_dataset':
            issue(f'DUP-{name}', name, profile['columns'], 'exact_duplicate_rows', profile['exact_duplicate_additional_rows'], 'additional_rows',
                  'Baris identik perlu ditinjau menurut satuan baris sumber.',
                  'Periksa satuan baris dan dampak sebelum menghapus duplikasi persis; audit jumlah sebelum/sesudah.',
                  ['join_integrity'], f'profiles.{name}.exact_duplicate_additional_rows')
    for relation, detail in fk.items():
        if relation.startswith('products_dataset.product_category_name'):
            continue  # DQ02 telah menangani kode tanpa terjemahan.
        child_col = relation.split(' -> ')[0]
        source, col = child_col.split('.')
        issue(f'FK-{source}-{col}', source, [col], 'unmatched_foreign_key', detail['unmatched_nonmissing_rows'], 'rows',
              'Referensi sumber tidak dapat dipetakan.',
              'Pertahankan transaksi dengan left join dan flag unmatched; kecualikan hanya metrik yang memerlukan atribut hilang.',
              ['join_integrity', 'coverage'], f'facts.foreign_keys.{relation}', role='P04')
    issue('SCORE-order_reviews_dataset', 'order_reviews_dataset', ['review_score'], 'invalid_review_score',
          review_keys['score_validity']['invalid_or_missing'], 'review_rows',
          'Skor tidak memenuhi domain integer 1–5.',
          'Pilih review terbaru dahulu, lalu flag skor invalid menjadi tidak tersedia; jangan kembali ke review lama.',
          ['Q2'], 'facts.reviews.score_validity')
    return profiles, facts, issues
