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
    if frame[list(columns)].apply(_blank).any(axis=1).any():
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
