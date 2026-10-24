"""Loader mentah dan cleaning yang dapat diaudit; CSV sumber tidak ditulis."""
from decimal import Decimal, InvalidOperation
from itertools import combinations
from pathlib import Path

import pandas as pd

from .config import (
    DATA_DIR, MONEY_SCALE, PRIMARY_SOURCES, PROJECT_ROOT, SOURCE_SCHEMAS,
    UNKNOWN_CATEGORY_LABEL, VALID_REVIEW_SCORES,
)


class SourceSchemaError(ValueError):
    """Sumber tidak memenuhi kontrak kolom yang dibutuhkan."""


def load_source(name: str, *, data_dir: str | Path | None = None) -> pd.DataFrame:
    """Baca sumber terdaftar, misalnya ``load_source("orders_dataset")``.

    Semua kolom memakai pandas StringDtype agar ID, awalan kode pos, tanggal,
    dan representasi desimal uang tetap utuh untuk assessment berikutnya.
    Hanya field kosong menjadi pd.NA; whitespace dan literal seperti "NA"
    dipertahankan. Direktori relatif dihitung dari PROJECT_ROOT, bukan cwd.
    Kolom tambahan dipertahankan; kolom wajib yang hilang memicu error.
    """
    if name not in SOURCE_SCHEMAS:
        raise ValueError(
            f"Sumber tidak dikenal: {name!r}. Pilih: {', '.join(SOURCE_SCHEMAS)}"
        )
    directory = DATA_DIR if data_dir is None else Path(data_dir)
    if not directory.is_absolute():
        directory = PROJECT_ROOT / directory
    path = directory / f"{name}.csv"
    if not path.is_file():
        raise FileNotFoundError(f"CSV sumber tidak ditemukan: {path}")
    try:
        frame = pd.read_csv(
            path, dtype="string", encoding="utf-8-sig",
            keep_default_na=False, na_values=[""],
        )
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeError) as exc:
        raise SourceSchemaError(f"CSV sumber tidak dapat dibaca: {path}: {exc}") from exc
    missing = sorted(set(SOURCE_SCHEMAS[name]) - set(frame.columns))
    if missing:
        raise SourceSchemaError(
            f"Kolom wajib tidak ditemukan pada {path}: {', '.join(missing)}"
        )
    return frame


# Cleaning P03. Semua transformasi memakai copy; load_source tetap loader mentah.
class DataQualityError(ValueError):
    """Konflik kualitas yang harus diselesaikan sebelum tabel boleh di-join."""


class MoneyPrecisionError(DataQualityError):
    """Uang dengan presisi di luar sen tidak boleh dibulatkan diam-diam."""

    def __init__(self, column, affected_count):
        self.column = column
        self.affected_count = affected_count
        super().__init__(f'{column}: {affected_count} nilai di luar presisi sen; perlu kebijakan eksplisit')


def _blank(series):
    return series.isna() | series.astype('string').str.strip().eq('').fillna(False)


def _require_unique(frame, columns, source):
    if any(_blank(frame[col]).any() for col in columns):
        raise DataQualityError(f'{source}: kunci kosong pada {columns}')
    if frame.duplicated(list(columns)).any():
        raise DataQualityError(f'{source}: konflik kunci {columns}; inspeksi sebelum join')


def _prepare(raw, source, keys=None):
    missing = sorted(set(SOURCE_SCHEMAS[source]) - set(raw.columns))
    if missing:
        raise SourceSchemaError(f'{source}: kolom wajib hilang: {missing}')
    if 'source_row_number' in raw:
        raise DataQualityError('Cleaning memerlukan data mentah, bukan tabel yang sudah dibersihkan')
    frame = raw.copy(deep=True).reset_index(drop=True)
    duplicate = frame.duplicated(keep='first')
    frame['source_row_number'] = pd.array(range(1, len(frame) + 1), dtype='Int64')
    removed = frame.loc[duplicate, 'source_row_number'].astype(int).tolist()
    frame = frame.loc[~duplicate].copy()
    if keys:
        _require_unique(frame, keys, source)
    audit = {
        'source': source, 'rows_before': len(raw), 'rows_after_exact_dedup': len(frame),
        'rows_after': len(frame), 'exact_duplicate_rows_removed': int(duplicate.sum()),
        'exact_duplicate_source_rows_removed': removed,
        'source_row_number_definition': 'Ordinal 1-based data record sebelum dedup, tidak termasuk header; bukan nomor baris fisik CSV',
        'key_columns': list(keys or ()), 'dates': {}, 'numeric': {}, 'flags': {},
    }
    return frame, audit


def _parse_dates(frame, columns, audit):
    for col in columns:
        raw = frame[col].copy()
        missing = _blank(raw)
        parsed = pd.to_datetime(raw.mask(missing), format='%Y-%m-%d %H:%M:%S', errors='coerce')
        frame[f'{col}_raw'] = raw
        frame[col] = parsed
        frame[f'{col}_missing'] = missing.astype('boolean')
        frame[f'{col}_parse_failed'] = (~missing & parsed.isna()).astype('boolean')
        frame[f'{col}_valid'] = parsed.notna().astype('boolean')
        audit['dates'][col] = {
            'missing_before': int(missing.sum()), 'parse_failures': int((~missing & parsed.isna()).sum()),
            'null_after': int(parsed.isna().sum()), 'valid_after': int(parsed.notna().sum()),
        }


def _parse_integers(frame, columns, audit, *, allowed=None):
    """Nilai integer invalid menjadi NA; teks asli dan alasan tetap tersedia."""
    for col in columns:
        raw = frame[col].copy()
        result, reasons = [], []
        for value in raw:
            if pd.isna(value) or not str(value).strip():
                result.append(pd.NA); reasons.append('missing'); continue
            try:
                number = Decimal(str(value))
            except InvalidOperation:
                result.append(pd.NA); reasons.append('parse_failed'); continue
            if not number.is_finite():
                reason = 'nonfinite'
            elif number != number.to_integral_value():
                reason = 'noninteger'
            elif allowed is not None and number not in allowed:
                reason = 'out_of_domain'
            elif not -(2**63) <= number <= 2**63 - 1:
                reason = 'overflow'
            else:
                reason = 'valid'
            result.append(int(number) if reason == 'valid' else pd.NA)
            reasons.append(reason)
        frame[f'{col}_raw'] = raw
        frame[col] = pd.array(result, dtype='Int64')
        frame[f'{col}_quality'] = pd.array(reasons, dtype='string')
        frame[f'{col}_valid'] = frame[col].notna().astype('boolean')
        audit['numeric'][col] = {
            'quality_counts': {str(k): int(v) for k, v in frame[f'{col}_quality'].value_counts().items()},
            'null_after': int(frame[col].isna().sum()),
        }


def _parse_money(frame, column, audit):
    """Konversi teks Decimal ke Int64 sen; nol valid, negatif/invalid nullable."""
    cents, reasons, precision_count = [], [], 0
    for value in frame[column]:
        if pd.isna(value) or not str(value).strip():
            cents.append(pd.NA); reasons.append('missing'); continue
        try:
            number = Decimal(str(value))
        except InvalidOperation:
            cents.append(pd.NA); reasons.append('parse_failed'); continue
        cent_value = None
        if not number.is_finite():
            reason = 'nonfinite'
        else:
            # Rasio integer menghindari pembulatan context Decimal pada teks
            # dengan >28 digit signifikan, termasuk pecahan kecil di luar sen.
            numerator, denominator = number.as_integer_ratio()
            scaled = numerator * MONEY_SCALE
            if scaled % denominator:
                precision_count += 1
                reason = 'beyond_cent_precision'
            elif number < 0:
                reason = 'negative'
            elif scaled // denominator > 2**63 - 1:
                reason = 'overflow'
            else:
                reason = 'valid'
                cent_value = scaled // denominator
        cents.append(cent_value if reason == 'valid' else pd.NA)
        reasons.append(reason)
    if precision_count:
        raise MoneyPrecisionError(column, precision_count)
    target = 'price_cents' if column == 'price' else 'freight_cents'
    frame[target] = pd.array(cents, dtype='Int64')
    frame[f'{column}_quality'] = pd.array(reasons, dtype='string')
    frame[f'{column}_valid'] = frame[target].notna().astype('boolean')
    audit['numeric'][column] = {
        'target': target,
        'quality_counts': {str(k): int(v) for k, v in frame[f'{column}_quality'].value_counts().items()},
        'valid_zero_rows': int(frame[target].eq(0).sum()),
        'valid_total_cents': int(frame[target].sum()), 'null_after': int(frame[target].isna().sum()),
    }


def _before(later, earlier, *, calendar=False):
    if calendar:
        later, earlier = later.dt.normalize(), earlier.dt.normalize()
    comparable = later.notna() & earlier.notna()
    result = pd.Series(pd.NA, index=later.index, dtype='boolean')
    result.loc[comparable] = later.loc[comparable].lt(earlier.loc[comparable])
    return result


def _finish(frame, audit):
    audit['rows_after'] = len(frame)
    audit['flags'] = {c: int(frame[c].sum()) for c in frame if str(frame[c].dtype) == 'boolean'}
    return frame.reset_index(drop=True), audit


def clean_orders(raw):
    """Parse tanggal dan flag kalender; status/periode/eligibility diterapkan P04."""
    frame, audit = _prepare(raw, 'orders_dataset', ('order_id',))
    _parse_dates(frame, SOURCE_SCHEMAS['orders_dataset'][3:], audit)
    lifecycle = ('order_purchase_timestamp', 'order_approved_at',
                 'order_delivered_carrier_date', 'order_delivered_customer_date')
    chronology = []
    for earlier, later in combinations(lifecycle, 2):
        flag = f'{later}_before_{earlier}'
        frame[flag] = _before(frame[later], frame[earlier])
        chronology.append(flag)
    estimate_flag = 'estimated_date_before_purchase'
    frame[estimate_flag] = _before(frame['order_estimated_delivery_date'], frame['order_purchase_timestamp'], calendar=True)
    chronology.append(estimate_flag)
    frame['has_lifecycle_chronology_issue'] = frame[chronology].fillna(False).any(axis=1).astype('boolean')
    frame['customer_id_valid'] = (~_blank(frame['customer_id'])).astype('boolean')
    required = ['order_purchase_timestamp', 'order_delivered_customer_date', 'order_estimated_delivery_date']
    valid = frame[required].notna().all(axis=1)
    valid &= ~frame['order_delivered_customer_date_before_order_purchase_timestamp'].fillna(True)
    valid &= ~frame[estimate_flag].fillna(True)
    frame['delivery_dates_valid'] = valid.astype('boolean')
    difference = (frame['order_delivered_customer_date'].dt.normalize()
                  - frame['order_estimated_delivery_date'].dt.normalize()).dt.days
    frame['is_late'] = pd.Series(pd.NA, index=frame.index, dtype='boolean')
    frame['days_late'] = pd.Series(pd.NA, index=frame.index, dtype='Int64')
    frame.loc[valid, 'is_late'] = difference.loc[valid].gt(0)
    frame.loc[valid, 'days_late'] = difference.loc[valid].clip(lower=0).astype('Int64')
    audit['delivery_label_scope'] = 'Tanggal valid saja; status delivered dan periode belum difilter (P04). Inversi approval/carrier tidak membatalkan pasangan tanggal aktual/estimasi.'
    audit['null_lateness_rows'] = int(frame['is_late'].isna().sum())
    return _finish(frame, audit)


def clean_customers(raw):
    frame, audit = _prepare(raw, 'customers_dataset', ('customer_id',))
    frame['customer_unique_id_valid'] = (~_blank(frame['customer_unique_id'])).astype('boolean')
    frame['customer_state_valid'] = (~_blank(frame['customer_state'])).astype('boolean')
    return _finish(frame, audit)


def clean_translation(raw):
    frame, audit = _prepare(raw, 'product_category_name_translation', ('product_category_name',))
    frame['translation_name_valid'] = (~_blank(frame['product_category_name_english'])).astype('boolean')
    return _finish(frame, audit)


def clean_products(raw, translation):
    frame, audit = _prepare(raw, 'products_dataset', ('product_id',))
    _require_unique(translation, ('product_category_name',), 'translation lookup')
    category = frame['product_category_name'].mask(_blank(frame['product_category_name']))
    english = translation.set_index('product_category_name')['product_category_name_english']
    english = english.mask(_blank(english))
    names = category.map(english).astype('string')
    frame['category_code'] = category.astype('string')
    frame['category_missing'] = category.isna().astype('boolean')
    frame['category_translation_missing'] = (category.notna() & names.isna()).astype('boolean')
    frame['category_name'] = names.fillna(category).fillna(UNKNOWN_CATEGORY_LABEL).astype('string')
    attrs = list(SOURCE_SCHEMAS['products_dataset'][2:])
    frame['optional_attributes_missing'] = frame[attrs].apply(_blank).any(axis=1).astype('boolean')
    _parse_integers(frame, attrs, audit)
    frame['product_weight_zero'] = frame['product_weight_g'].eq(0).fillna(False).astype('boolean')
    audit['category_lookup'] = {
        'rows_before': len(frame), 'rows_after': len(frame), 'translation_key_unique': True,
        'missing_category_products': int(frame['category_missing'].sum()),
        'untranslated_products': int(frame['category_translation_missing'].sum()),
        'unknown_display_name_after': int(frame['category_name'].eq(UNKNOWN_CATEGORY_LABEL).sum()),
        'untranslated_codes': sorted(frame.loc[frame['category_translation_missing'], 'category_code'].unique().tolist()),
    }
    return _finish(frame, audit)


def clean_order_items(raw, orders):
    frame, audit = _prepare(raw, 'order_items_dataset', ('order_id', 'order_item_id'))
    _parse_dates(frame, ('shipping_limit_date',), audit)
    # ID asli tetap string; angka urutan hanya atribut validasi, bukan pengganti ID.
    original = frame['order_item_id'].copy()
    _parse_integers(frame, ('order_item_id',), audit)
    if frame['order_item_id'].isna().any() or frame['order_item_id'].le(0).any():
        raise DataQualityError('order_item_id harus integer positif sebelum join')
    if frame.duplicated(['order_id', 'order_item_id']).any():
        raise DataQualityError('order_item_id berbeda secara teks tetapi bentrok sebagai nomor item')
    frame['order_item_number'] = frame['order_item_id']
    frame['order_item_id'] = original
    _parse_money(frame, 'price', audit)
    _parse_money(frame, 'freight_value', audit)
    _require_unique(orders, ('order_id',), 'orders lookup')
    purchase = frame['order_id'].map(orders.set_index('order_id')['order_purchase_timestamp'])
    frame['shipping_limit_before_purchase'] = _before(frame['shipping_limit_date'], purchase)
    last_purchase = orders['order_purchase_timestamp'].max()
    if pd.isna(last_purchase):
        frame['shipping_limit_after_purchase_snapshot'] = pd.Series(pd.NA, index=frame.index, dtype='boolean')
    else:
        valid = frame['shipping_limit_date'].notna()
        frame['shipping_limit_after_purchase_snapshot'] = (
            frame['shipping_limit_date'].dt.normalize().gt(last_purchase.normalize())
            .astype('boolean').mask(~valid))
    return _finish(frame, audit)


def _selection_reason(group):
    if len(group) == 1:
        return 'single_candidate'
    remaining = group
    for col, reason in [
        ('review_creation_date', 'latest_creation_date'),
        ('review_answer_timestamp', 'latest_answer_timestamp'),
        ('review_id', 'lexical_review_id'), ('source_row_number', 'source_row_number'),
    ]:
        nonmissing = remaining[col].dropna()
        if not nonmissing.empty:
            remaining = remaining.loc[remaining[col].eq(nonmissing.max()).fillna(False)]
        if len(remaining) == 1:
            return reason
    raise DataQualityError('Seleksi review tidak dapat menentukan pemenang')


def clean_reviews(raw, orders):
    """Pilih terbaru sebelum validasi skor; audit jejak seluruh kandidat bersaing."""
    frame, audit = _prepare(raw, 'order_reviews_dataset')
    if _blank(frame['order_id']).any() or _blank(frame['review_id']).any():
        raise DataQualityError('Kunci order_id/review_id kosong pada review; inspeksi sebelum seleksi')
    _parse_dates(frame, ('review_creation_date', 'review_answer_timestamp'), audit)
    _require_unique(orders, ('order_id',), 'orders lookup')
    purchase = frame['order_id'].map(orders.set_index('order_id')['order_purchase_timestamp'])
    frame['review_created_before_purchase'] = _before(frame['review_creation_date'], purchase, calendar=True)
    frame['review_answer_before_creation'] = _before(frame['review_answer_timestamp'], frame['review_creation_date'])
    for col in ('review_comment_title', 'review_comment_message'):
        frame[f'{col}_raw'] = frame[col].copy()
        frame[f'{col}_missing'] = _blank(frame[col]).astype('boolean')
        frame[col] = frame[col].mask(frame[f'{col}_missing'])
    frame['review_candidate_count'] = frame.groupby('order_id')['order_id'].transform('size').astype('Int64')
    ordering = ['order_id', 'review_creation_date', 'review_answer_timestamp', 'review_id', 'source_row_number']
    ordered = frame.sort_values(ordering, na_position='first', kind='stable')
    selected = ordered.drop_duplicates('order_id', keep='last').copy()
    reasons = {order: _selection_reason(group) for order, group in frame.groupby('order_id', sort=False) if len(group) > 1}
    selected['review_selection_reason'] = selected['order_id'].map(reasons).astype('string').fillna('single_candidate')
    # Skor baru diperiksa setelah pemenang ditentukan. Kandidat lama tidak menjadi fallback.
    _parse_integers(frame, ('review_score',), audit, allowed=VALID_REVIEW_SCORES)
    selected = selected.drop(columns='review_score').join(
        frame[['review_score', 'review_score_raw', 'review_score_quality', 'review_score_valid']], how='left', validate='one_to_one')
    winner_rows = selected.set_index('order_id')['source_row_number']
    trace = frame.loc[frame['review_candidate_count'].gt(1), [
        'order_id', 'review_id', 'source_row_number', 'review_creation_date',
        'review_answer_timestamp', 'review_score_raw', 'review_score_valid', 'review_candidate_count',
    ]].copy()
    trace['selected_source_row_number'] = trace['order_id'].map(winner_rows).astype('Int64')
    trace['selected'] = trace['source_row_number'].eq(trace['selected_source_row_number'])
    trace['selection_reason'] = trace['order_id'].map(reasons)
    # JSON serializable, timestamp-null ditulis None. Skrip mengekspor tabel jejak ke CSV.
    audit['selection_trace'] = [
        {k: (None if pd.isna(v) else str(v) if isinstance(v, pd.Timestamp) else v)
         for k, v in row.items()} for row in trace.to_dict('records')
    ]
    audit['review_selection'] = {
        'rows_before_selection': len(frame), 'rows_after_selection': len(selected),
        'alternative_rows_removed': len(frame) - len(selected),
        'orders_with_multiple_candidates': len(reasons),
        'repeated_review_id_additional_before': int(frame['review_id'].duplicated().sum()),
        'repeated_review_id_additional_after': int(selected['review_id'].duplicated().sum()),
        'reason_counts': {str(k): int(v) for k, v in selected['review_selection_reason'].value_counts().items()},
        'candidate_missing_title': int(frame['review_comment_title_missing'].sum()),
        'candidate_missing_message': int(frame['review_comment_message_missing'].sum()),
        'candidate_created_before_purchase': int(frame['review_created_before_purchase'].sum()),
        'candidate_answer_before_creation': int(frame['review_answer_before_creation'].sum()),
        'candidate_invalid_scores': int((~frame['review_score_valid']).sum()),
        'selected_invalid_scores': int((~selected['review_score_valid']).sum()),
        'selection_policy': 'Max creation, answer, lexical review_id, source_row_number; tanggal null sebelum valid. Skor tidak ikut menentukan pemenang.',
    }
    _require_unique(selected, ('order_id',), 'selected reviews')
    audit['key_columns'] = ['order_id']
    return _finish(selected.sort_values('source_row_number'), audit)


def clean_primary_sources(*, data_dir=None):
    """Cleaning enam sumber mentah, mengembalikan (tables, audits), tanpa ekspor CSV."""
    raw = {name: load_source(name, data_dir=data_dir) for name in PRIMARY_SOURCES}
    tables, audits = {}, {}
    for name, cleaner in [
        ('orders_dataset', clean_orders), ('customers_dataset', clean_customers),
        ('product_category_name_translation', clean_translation),
    ]:
        tables[name], audits[name] = cleaner(raw[name])
    tables['products_dataset'], audits['products_dataset'] = clean_products(
        raw['products_dataset'], tables['product_category_name_translation'])
    tables['order_items_dataset'], audits['order_items_dataset'] = clean_order_items(
        raw['order_items_dataset'], tables['orders_dataset'])
    tables['order_reviews_dataset'], audits['order_reviews_dataset'] = clean_reviews(
        raw['order_reviews_dataset'], tables['orders_dataset'])
    return tables, audits


# Integrasi P04: setiap join mempertahankan sisi kiri dan diaudit.
def _money_totals(frame):
    return {
        c: {'known_total_cents': sum(int(v) for v in frame[c].dropna()),
            'nonnull_rows': int(frame[c].notna().sum()), 'null_rows': int(frame[c].isna().sum())}
        for c in frame if c.endswith('_cents')
    }


def _table_snapshot(frame):
    return {'rows': len(frame), 'unique_orders': int(frame['order_id'].nunique()) if 'order_id' in frame else None,
            'money': _money_totals(frame)}


def _audited_left_join(left, right, *, on, relationship, name, audit):
    _require_unique(right, (on,), f'{name} right')
    overlaps = (set(left) & set(right)) - {on}
    if overlaps:
        raise DataQualityError(f'{name}: kolom saling menimpa: {sorted(overlaps)}')
    marker = f'_{name}_merge'
    if marker in left or marker in right:
        raise DataQualityError(f'{name}: kolom audit sudah ada')
    before = _table_snapshot(left)
    joined = left.merge(right, on=on, how='left', validate=relationship, indicator=marker, sort=False)
    after = _table_snapshot(joined)
    if before['rows'] != after['rows'] or before['unique_orders'] != after['unique_orders']:
        raise DataQualityError(f'{name}: join memperbanyak/menghilangkan baris atau pesanan kiri')
    for col, value in before['money'].items():
        if after['money'][col] != value:
            raise DataQualityError(f'{name}: nilai uang kiri berubah pada {col}')
    unmatched = joined[marker].eq('left_only')
    unused = ~right[on].isin(left[on])
    left_blank = _blank(left[on])
    audit.append({
        'join': name, 'key': on, 'how': 'left', 'validate': relationship,
        'before_left': before, 'before_right': _table_snapshot(right), 'after': after,
        'unmatched_left_rows': int(unmatched.sum()),
        'left_missing_key_rows': int(left_blank.sum()),
        'unmatched_nonmissing_left_rows': int((~left_blank & ~left[on].isin(right[on])).sum()),
        'unmatched_nonmissing_key_examples': sorted(left.loc[~left_blank & ~left[on].isin(right[on]),on].drop_duplicates().astype(str).tolist())[:5],
        'unused_right_rows': int(unused.sum()), 'unused_right_money': _money_totals(right.loc[unused]),
        'left_rows_orders_and_money_preserved': True,
    })
    return joined, joined[marker].eq('both').astype('boolean'), marker


def aggregate_order_items(items):
    """Satu baris per order; satu harga invalid membuat nilai order tidak tersedia."""
    _require_unique(items, ('order_id','order_item_id'), 'clean items')
    valid = items['price_valid'].fillna(False) & items['price_cents'].notna() & items['price_cents'].ge(0).fillna(False)
    work = items[['order_id','order_item_id']].copy()
    work['_valid_price'] = valid
    group = work.groupby('order_id', sort=False)
    result = group.agg(item_count=('order_item_id','size'), valid_price_item_count=('_valid_price','sum'))
    result['invalid_price_item_count'] = result['item_count'] - result['valid_price_item_count']
    # object/Python integer voorkomt overflow in tussensommen; nooit een partial orderbedrag.
    sums = items['price_cents'].where(valid).astype(object).groupby(items['order_id'], sort=False).sum(min_count=1)
    complete = result['invalid_price_item_count'].eq(0)
    sums = sums.where(complete, pd.NA)
    try:
        result['order_value_cents'] = pd.array(sums, dtype='Int64')
    except (OverflowError, TypeError) as exc:
        raise DataQualityError('Orderbedrag past niet in Int64 sen; expliciete opslagkeuze nodig') from exc
    for col in ('item_count','valid_price_item_count','invalid_price_item_count'):
        result[col] = result[col].astype('Int64')
    result['items_value_complete'] = complete.astype('boolean')
    result = result.reset_index()
    known_price = sum(int(v) for v in items.loc[valid,'price_cents'])
    complete_price = sum(int(v) for v in result['order_value_cents'].dropna())
    return result, {
        'rows_before': len(items), 'orders_after': len(result),
        'item_count_after': int(result['item_count'].sum()),
        'invalid_price_items': int((~valid).sum()),
        'incomplete_value_orders': int((~complete).sum()),
        'valid_item_price_total_cents': known_price,
        'complete_order_value_total_cents': complete_price,
        'suppressed_known_price_cents_on_incomplete_orders': known_price - complete_price,
        'no_partial_order_values': True,
    }


def _apply_order_eligibility(orders):
    from .config import ANALYSIS_START, ANALYSIS_END_EXCLUSIVE, SALES_ORDER_STATUS
    orders['purchase_date'] = orders['order_purchase_timestamp'].dt.normalize()
    orders['purchase_month'] = orders['order_purchase_timestamp'].dt.strftime('%Y-%m').astype('string')
    orders['in_analysis_period'] = (
        orders['order_purchase_timestamp'].ge(pd.Timestamp(ANALYSIS_START))
        & orders['order_purchase_timestamp'].lt(pd.Timestamp(ANALYSIS_END_EXCLUSIVE))
    ).fillna(False).astype('boolean')
    delivered = orders['order_status'].eq(SALES_ORDER_STATUS).fillna(False)
    base = orders['in_analysis_period'] & delivered
    orders['eligible_sales'] = (base & orders['has_items'] & orders['items_value_complete']).astype('boolean')
    orders['eligible_delivery'] = (base & orders['delivery_dates_valid']).astype('boolean')
    orders['eligible_review_comparison'] = (orders['eligible_delivery'] & orders['review_score_valid']).astype('boolean')
    orders['eligible_rfm'] = (orders['eligible_sales'] & orders['customer_identity_valid']).astype('boolean')
    return orders


def _eligibility_audit(orders):
    from .config import SALES_ORDER_STATUS
    delivered = orders['order_status'].eq(SALES_ORDER_STATUS).fillna(False)
    conditions = {
        'outside_analysis_period': orders['in_analysis_period'],
        'not_delivered': delivered, 'no_items': orders['has_items'],
        'incomplete_item_prices': orders['items_value_complete'],
        'invalid_delivery_dates': orders['delivery_dates_valid'],
        'no_valid_selected_review': orders['review_score_valid'],
        'no_valid_customer_identity': orders['customer_identity_valid'],
    }
    factors = {
        'eligible_sales': ['outside_analysis_period','not_delivered','no_items','incomplete_item_prices'],
        'eligible_delivery': ['outside_analysis_period','not_delivered','invalid_delivery_dates'],
        'eligible_review_comparison': ['outside_analysis_period','not_delivered','invalid_delivery_dates','no_valid_selected_review'],
        'eligible_rfm': ['outside_analysis_period','not_delivered','no_items','incomplete_item_prices','no_valid_customer_identity'],
    }
    base = orders['in_analysis_period'] & delivered
    metrics = {}
    for flag, reasons in factors.items():
        remaining = pd.Series(True, index=orders.index, dtype='boolean')
        exclusive = {}
        for reason in reasons:
            good = conditions[reason].fillna(False)
            exclusive[reason] = int((remaining & ~good).sum())
            remaining &= good
        eligible = orders[flag]
        if not remaining.equals(eligible):
            raise DataQualityError(f'{flag}: kelayakan tidak cocok dengan audit alasan')
        metrics[flag] = {
            'population_orders': len(orders), 'eligible_orders': int(eligible.sum()),
            'ineligible_orders': int((~eligible).sum()),
            'overlapping_failure_counts': {reason:int((~conditions[reason]).sum()) for reason in reasons},
            'exclusive_first_failure_counts': exclusive,
            'analysis_period_delivered_orders': int(base.sum()),
            'eligible_in_analysis_period_delivered': int((base & eligible).sum()),
            'failures_within_analysis_period_delivered': {
                reason:int((base & ~conditions[reason]).sum()) for reason in reasons[2:]},
        }
    sales = orders['eligible_sales']; rfm = orders['eligible_rfm']; delivery = orders['eligible_delivery']
    return {
        'metrics': metrics,
        'reason_count_note': 'overlapping_failure_counts tidak dijumlahkan; exclusive_first_failure_counts saling eksklusif dalam urutan tertera',
        'coverage_differences': {
            'sales_without_delivery': int((sales & ~delivery).sum()),
            'delivery_without_sales': int((delivery & ~sales).sum()),
            'delivery_without_valid_review': int((delivery & ~orders['review_score_valid']).sum()),
            'sales_without_rfm_identity': int((sales & ~rfm).sum()),
            'sales_value_cents': sum(int(v) for v in orders.loc[sales,'order_value_cents']),
            'rfm_value_cents': sum(int(v) for v in orders.loc[rfm,'order_value_cents']),
        },
    }


def build_analysis_tables(cleaned=None, *, data_dir=None):
    """Kembalikan ({order_level, item_level}, audit P04); tidak menulis CSV."""
    from .data_contracts import TABLE_CONTRACTS, conform_table
    if cleaned is None:
        cleaned, _ = clean_primary_sources(data_dir=data_dir)
    elif data_dir is not None:
        raise ValueError('Pilih cleaned atau data_dir, bukan keduanya')
    orders = cleaned['orders_dataset']; items = cleaned['order_items_dataset']
    customers = cleaned['customers_dataset']; products = cleaned['products_dataset']
    reviews = cleaned['order_reviews_dataset']; translation = cleaned['product_category_name_translation']
    _require_unique(orders, ('order_id',), 'orders')
    _require_unique(reviews, ('order_id',), 'selected reviews')
    order_cols = ['order_id','customer_id','order_status','order_purchase_timestamp','order_approved_at',
                  'order_delivered_carrier_date','order_delivered_customer_date','order_estimated_delivery_date',
                  'has_lifecycle_chronology_issue','delivery_dates_valid','is_late','days_late']
    order_level = orders[order_cols].copy()
    joins = []
    customer_fields = ['customer_id','customer_unique_id','customer_state','customer_unique_id_valid']
    order_level, matched, marker = _audited_left_join(order_level, customers[customer_fields], on='customer_id',
        relationship='many_to_one', name='orders_customers', audit=joins)
    order_level['customer_matched'] = matched
    order_level['customer_identity_valid'] = (matched & order_level['customer_unique_id_valid'].fillna(False)
        & ~_blank(order_level['customer_unique_id'])).astype('boolean')
    order_level = order_level.drop(columns=[marker,'customer_unique_id_valid'])
    aggregate, aggregate_audit = aggregate_order_items(items)
    order_level, _, marker = _audited_left_join(order_level, aggregate, on='order_id',
        relationship='one_to_one', name='orders_item_aggregate', audit=joins)
    for col in ('item_count','valid_price_item_count','invalid_price_item_count'):
        order_level[col] = order_level[col].fillna(0).astype('Int64')
    order_level['has_items'] = order_level['item_count'].gt(0).astype('boolean')
    order_level['items_value_complete'] = order_level['items_value_complete'].fillna(False).astype('boolean')
    order_level = order_level.drop(columns=marker)
    review_fields = ['order_id','review_id','review_score','review_score_valid','review_candidate_count','review_created_before_purchase']
    order_level, matched, marker = _audited_left_join(order_level, reviews[review_fields], on='order_id',
        relationship='one_to_one', name='orders_selected_reviews', audit=joins)
    order_level['review_matched'] = matched
    order_level['review_score_valid'] = (matched & order_level['review_score_valid'].fillna(False)).astype('boolean')
    order_level['review_candidate_count'] = order_level['review_candidate_count'].fillna(0).astype('Int64')
    order_level = _apply_order_eligibility(order_level.drop(columns=marker))
    order_level = conform_table(order_level, 'order_level')
    item_fields = ['order_id','order_item_id','product_id','seller_id','price_cents','price_valid','freight_cents']
    order_payload = ['order_id','customer_id','customer_unique_id','customer_state','order_status',
                     'order_purchase_timestamp','purchase_date','purchase_month','in_analysis_period','eligible_sales']
    item_level, matched, marker = _audited_left_join(items[item_fields], order_level[order_payload], on='order_id',
        relationship='many_to_one', name='items_orders_customers', audit=joins)
    item_level['order_matched'] = matched
    for col in ('in_analysis_period','eligible_sales'):
        item_level[col] = item_level[col].fillna(False).astype('boolean')
    item_level = item_level.drop(columns=marker)
    item_level, matched, marker = _audited_left_join(item_level, products[['product_id','category_code']], on='product_id',
        relationship='many_to_one', name='items_products', audit=joins)
    item_level['product_matched'] = matched
    item_level = item_level.drop(columns=marker)
    lookup = translation[['product_category_name','product_category_name_english']].rename(columns={'product_category_name':'category_code'})
    item_level, matched, marker = _audited_left_join(item_level, lookup, on='category_code',
        relationship='many_to_one', name='items_translation', audit=joins)
    english = item_level['product_category_name_english'].mask(_blank(item_level['product_category_name_english']))
    code = item_level['category_code'].mask(_blank(item_level['category_code']))
    item_level['category_code'] = code
    item_level['category_name'] = english.fillna(code).fillna(UNKNOWN_CATEGORY_LABEL).astype('string')
    item_level['category_missing'] = code.isna().astype('boolean')
    item_level['category_translation_matched'] = matched
    item_level['category_translation_missing'] = (code.notna() & english.isna()).astype('boolean')
    item_level = conform_table(item_level.drop(columns=[marker,'product_category_name_english']), 'item_level')
    eligible_orders = order_level.loc[order_level['eligible_sales']]
    eligible_items = item_level.loc[item_level['eligible_sales']]
    order_total = sum(int(v) for v in eligible_orders['order_value_cents'])
    item_total = sum(int(v) for v in eligible_items['price_cents'])
    eligible_item_count = int(eligible_orders['item_count'].sum())
    if order_total != item_total or eligible_item_count != len(eligible_items):
        raise DataQualityError('Rekonsiliasi item dan order eligible sales gagal')
    if _money_totals(items[item_fields]) != _money_totals(item_level):
        raise DataQualityError('Total uang item berubah setelah join kategori')
    audit = {
        'aggregation': aggregate_audit, 'joins': joins, 'eligibility': _eligibility_audit(order_level),
        'reconciliation': {
            'order_rows_before': len(orders), 'order_rows_after': len(order_level),
            'item_rows_before': len(items), 'item_rows_after': len(item_level),
            'all_item_money_before': _money_totals(items[item_fields]), 'all_item_money_after': _money_totals(item_level),
            'eligible_sales_orders': len(eligible_orders), 'eligible_sales_items': len(eligible_items),
            'eligible_order_item_count': eligible_item_count,
            'eligible_order_value_cents': order_total, 'eligible_item_price_cents': item_total,
            'eligible_items_unique_orders': int(eligible_items['order_id'].nunique()),
            'matched_item_order_totals_equal': True,
        },
        'coverage': {
            'orders_without_customer_match': int((~order_level['customer_matched']).sum()),
            'orders_without_items': int((~order_level['has_items']).sum()),
            'orders_without_review': int((~order_level['review_matched']).sum()),
            'items_without_order': int((~item_level['order_matched']).sum()),
            'items_without_product': int((~item_level['product_matched']).sum()),
            'items_without_category_code': int(item_level['category_missing'].sum()),
            'items_with_untranslated_category': int(item_level['category_translation_missing'].sum()),
        },
        'contracts': {name:{'grain':c['grain'],'primary_key':c['primary_key'],
                            'columns':len(c['fields']),'validated':True} for name,c in TABLE_CONTRACTS.items()},
        'payments_policy': 'Tidak digunakan; tidak ada join pembayaran mentah. Jika digunakan kelak harus diagregasi per order terlebih dahulu.',
    }
    return {'order_level':order_level,'item_level':item_level}, audit
