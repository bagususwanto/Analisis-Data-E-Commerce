"""Reproduksi dan gate P03; tidak mengekspor tabel analisis milik P04/P08."""
import csv
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import platform
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
from pandas.testing import assert_frame_equal
from scripts.assess_data import verify_inputs
from src.config import PRIMARY_SOURCES
from src.data_pipeline import clean_primary_sources


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def impact_register(quality, tables, audits):
    o, p, r = [tables[n] for n in ('orders_dataset', 'products_dataset', 'order_reviews_dataset')]
    rv = audits['order_reviews_dataset']['review_selection']
    count = lambda frame, col: int(frame[col].sum())
    results = {
        'DQ01': (int(p['category_name'].isna().sum()), 'products without display name', 'handled_with_label', count(p,'category_missing')),
        'DQ02': (int(p.loc[p['category_translation_missing'],'category_name'].isna().sum()), 'untranslated products without fallback display', 'handled_with_fallback', count(p,'category_translation_missing')),
        'DQ03': (int(r.groupby('order_id').size().gt(1).sum()), 'orders with multiple selected reviews', 'resolved_by_selection', rv['orders_with_multiple_candidates']),
        'DQ04': (rv['repeated_review_id_additional_after'], 'additional repeated review IDs among selected rows', 'retained_by_policy', 0),
        'DQ05': (int(o['order_delivered_customer_date'].isna().sum()), 'orders with null receipt timestamp', 'retained_nullable_with_flag', 0),
        'DQ06': (int(o['order_delivered_carrier_date'].isna().sum()), 'orders with null carrier timestamp', 'retained_nullable_with_flag', 0),
        'DQ07': (int(o['order_approved_at'].isna().sum()), 'orders with null approval timestamp', 'retained_nullable_with_flag', 0),
        'DQ08': (count(r,'review_comment_title_missing'), 'selected reviews with missing title', 'retained_nullable_with_flag', 0),
        'DQ09': (count(r,'review_comment_message_missing'), 'selected reviews with missing message', 'retained_nullable_with_flag', 0),
        'DQ10': (count(p,'optional_attributes_missing'), 'products with missing optional attributes', 'retained_nullable_with_flag', 0),
        'DQ11': (count(o,'has_lifecycle_chronology_issue'), 'orders flagged for observed chronology inversions', 'flagged_no_date_correction', 0),
        'DQ12': (count(tables['order_items_dataset'],'shipping_limit_after_purchase_snapshot'), 'item rows flagged for shipping deadline after purchase snapshot', 'flagged_documentation', 0),
        'DQ13': (int((~o['order_id'].isin(tables['order_items_dataset']['order_id'])).sum()), 'orders without item coverage retained', 'deferred_to_P04', 0),
        'DQ14': (int((~o['order_id'].isin(r['order_id'])).sum()), 'orders without review coverage retained', 'deferred_to_P04', 0),
        'DQ17': (count(r,'review_created_before_purchase'), 'selected reviews flagged for creation before purchase', 'flagged_metadata_score_retained', 0),
        'DQ19': (count(p,'product_weight_zero'), 'products with zero weight retained and flagged', 'flagged_unused_attribute', 0),
    }
    notes = {
        'DQ01': 'Kode sumber kosong tetap tersedia; kondisi awal tidak dianggap kategori berhasil ditemukan. Label bukan kategori rekomendasi.',
        'DQ02': 'Kode nonkosong dipertahankan; nama asli menjadi fallback. Tidak dicampur dengan kategori kosong.',
        'DQ03': f'{rv["alternative_rows_removed"]} alternatif tersisih setelah exact dedup. Trace mencatat kandidat, pemenang, ordinal sumber, serta alasan tie-break.',
        'DQ04': 'Tidak ada penghapusan berdasarkan review_id. Perubahan jumlah akhir berasal dari seleksi per order DQ03, bukan ID dedup.',
        'DQ08': f'Sebelum pada semua kandidat: {rv["candidate_missing_title"]}; sesudah pada review terpilih. Perbedaan cakupan hanya seleksi DQ03, bukan imputasi.',
        'DQ09': f'Sebelum pada semua kandidat: {rv["candidate_missing_message"]}; sesudah pada review terpilih. Perbedaan cakupan hanya seleksi DQ03, bukan imputasi.',
        'DQ11': 'Timestamp asli disimpan; inversi approval/carrier saja tidak membatalkan pasangan tanggal delivery. Estimasi sebelum pembelian ditandai dan tidak menghasilkan label keterlambatan.',
        'DQ17': f'Semua kandidat terflag: {rv["candidate_created_before_purchase"]}; sesudah memakai review terpilih. Skor integer 1–5 tidak dihapus karena metadata waktu.',
    }
    result = []
    for issue in quality['issues']:
        ident = issue['issue_id']
        if ident in results:
            after, measure, status, changed = results[ident]
        else:
            after, measure, status, changed = issue['affected_count'], 'same supporting-source condition; no transformation', 'documented_not_used', 0
            if issue['owner_phase'] == 'P04':
                status = 'deferred_to_P04'
        result.append({
            'issue_id': ident, 'source': issue['source'], 'owner_phase': issue['owner_phase'],
            'before_count': issue['affected_count'], 'before_unit': issue['affected_unit'],
            'before_population': 'raw source records (P02)', 'after_count': after, 'after_measure': measure,
            'after_population': 'selected review records' if ident in ('DQ04','DQ08','DQ09','DQ17') else 'same source population, unless explicitly stated',
            'values_repaired_or_replaced': changed, 'status': status,
            'action': issue['planned_action'],
            'notes': notes.get(ident, 'Tidak ada imputasi. Kondisi yang dipertahankan/ditunda dicatat sesuai relevansi metrik dan phase pemilik.'),
            'counts_not_additive': True,
        })
    return result


def independent_checks(tables):
    """Rekonsiliasi dari csv/Decimal tanpa memakai helper parsing/seleksi pipeline."""
    expected, price_total, freight_total = {}, 0, 0
    with (ROOT / 'data/order_reviews_dataset.csv').open(newline='', encoding='utf-8-sig') as stream:
        for rownum, row in enumerate(csv.DictReader(stream), 1):
            def timestamp(value):
                return datetime.strptime(value, '%Y-%m-%d %H:%M:%S') if value.strip() else datetime.min
            key = (timestamp(row['review_creation_date']), timestamp(row['review_answer_timestamp']), row['review_id'], rownum)
            prior = expected.get(row['order_id'])
            if prior is None or key > prior[0]:
                expected[row['order_id']] = (key, rownum, row['review_id'], row['review_score'])
    actual = tables['order_reviews_dataset']
    assert len(actual) == len(expected)
    for row in actual[['order_id','review_id','source_row_number','review_score_raw']].itertuples(index=False):
        ref = expected[row.order_id]
        assert (row.source_row_number,row.review_id,row.review_score_raw) == ref[1:]
    with (ROOT / 'data/order_items_dataset.csv').open(newline='', encoding='utf-8-sig') as stream:
        for row in csv.DictReader(stream):
            price = Decimal(row['price']) * 100
            freight = Decimal(row['freight_value']) * 100
            assert price == price.to_integral_value() and freight == freight.to_integral_value()
            price_total += int(price); freight_total += int(freight)
    items = tables['order_items_dataset']
    assert int(items['price_cents'].sum()) == price_total
    assert int(items['freight_cents'].sum()) == freight_total
    orders = tables['orders_dataset']
    invalid = ~orders['delivery_dates_valid']
    assert orders.loc[invalid,'is_late'].isna().all() and orders.loc[invalid,'days_late'].isna().all()
    delivered_no_receipt = orders['order_status'].eq('delivered') & orders['order_delivered_customer_date'].isna()
    assert int(delivered_no_receipt.sum()) == 8
    assert orders.loc[delivered_no_receipt,'is_late'].isna().all()
    for name, cols in {
        'orders_dataset':['order_id'], 'customers_dataset':['customer_id'],
        'products_dataset':['product_id'], 'product_category_name_translation':['product_category_name'],
        'order_items_dataset':['order_id','order_item_id'], 'order_reviews_dataset':['order_id'],
    }.items():
        assert not tables[name].duplicated(cols).any()
        assert not tables[name][cols].isna().any().any()
    return {
        'independent_review_winners_match': len(expected),
        'raw_and_clean_price_total_cents': price_total,
        'raw_and_clean_freight_total_cents': freight_total,
        'invalid_delivery_pairs_with_null_labels': int(invalid.sum()),
        'delivered_missing_receipt_with_null_labels': int(delivered_no_receipt.sum()),
        'required_keys_unique_and_complete': True,
    }


def main():
    baseline = json.loads((ROOT/'reports/baseline.json').read_text())
    quality_path = ROOT/'reports/data_quality.json'
    quality = json.loads(quality_path.read_text())
    assessment_validation = json.loads((ROOT/'reports/assessment_validation.json').read_text())
    assert quality['phase'] == 'P02' and quality['gate']['passed']
    assert sha(quality_path) == assessment_validation['data_quality_sha256'], 'Laporan P02 berubah setelah verifikasi'
    before = verify_inputs(baseline)
    assert before == quality['source_sha256']
    tables, audits = clean_primary_sources()
    again, again_audits = clean_primary_sources()
    for name in PRIMARY_SOURCES:
        assert_frame_equal(tables[name], again[name])
        assert audits[name] == again_audits[name]
        p = quality['profiles'][name]
        assert audits[name]['rows_before'] == p['row_count']
        assert audits[name]['exact_duplicate_rows_removed'] == p['exact_duplicate_additional_rows']
    del again, again_audits
    checks = independent_checks(tables)
    impacts = impact_register(quality, tables, audits)
    assert {i['issue_id'] for i in impacts} == {i['issue_id'] for i in quality['issues']}
    # Bukti masalah awal masih sesuai assessment pada populasi yang sama.
    rv = audits['order_reviews_dataset']['review_selection']
    assert rv['orders_with_multiple_candidates'] == quality['facts']['reviews']['order_id']['duplicate_key_groups']
    assert rv['candidate_created_before_purchase'] == quality['facts']['reviews']['creation_calendar_before_purchase']
    assert audits['orders_dataset']['flags']['has_lifecycle_chronology_issue'] == quality['facts']['orders_with_any_lifecycle_or_estimate_chronology_issue']
    after = verify_inputs(baseline)
    assert before == after
    stamp = datetime.now(ZoneInfo('Asia/Jakarta')).isoformat(timespec='seconds')
    trace = audits['order_reviews_dataset'].pop('selection_trace')
    trace_columns = ['order_id','review_id','source_row_number','review_creation_date','review_answer_timestamp',
                     'review_score_raw','review_score_valid','review_candidate_count','selected_source_row_number','selected','selection_reason']
    trace_path = ROOT/'reports/review_selection.csv'
    pd.DataFrame(trace, columns=trace_columns).to_csv(trace_path, index=False)
    audits['order_reviews_dataset']['selection_trace_file'] = {
        'path':'reports/review_selection.csv', 'rows':len(trace), 'sha256':sha(trace_path),
        'scope':'Kandidat pada order dengan beberapa baris setelah exact dedup; single candidate tercatat pada tabel hasil cleaning',
    }
    report = {
        'phase':'P03', 'status':'completed', 'verified_at':stamp,
        'generator':'scripts/check_cleaning.py',
        'runtime':{'python':platform.python_version(),'pandas':pd.__version__,'invocation_cwd':str(Path.cwd())},
        'source_sha256':after, 'assessment_sha256':sha(quality_path),
        'scope':'Cleaning enam sumber; status/periode tidak difilter. Tabel analisis/eligibility/ekspor dashboard belum dibuat.',
        'sources':audits, 'issue_impacts':impacts,
        'table_schemas':{name:{c:str(frame[c].dtype) for c in frame} for name,frame in tables.items()},
        'gate':{'passed':True, 'deterministic_second_run':True,'source_hashes_unchanged':True,
                'all_assessment_issues_accounted_for':True, **checks},
    }
    audit_path=ROOT/'reports/cleaning_audit.json'
    audit_path.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    validation={
        'phase':'P03','status':'passed','verified_at':stamp,'invocation_cwd':str(Path.cwd()),
        'checks':checks,'deterministic_second_run':True,'nine_source_hashes_unchanged':True,
        'template_hash_unchanged':True,'p02_report_hash_matches_verification':True,
        'cleaning_audit_sha256':sha(audit_path),'review_selection_sha256':sha(trace_path),
        'rows_after':{n:len(t) for n,t in tables.items()},
        'note':'Tes kasus risiko dijalankan terpisah melalui pytest; lihat EXECUTION_STATUS.md.',
    }
    (ROOT/'reports/cleaning_validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
    print(f'PASS P03: {len(tables)} cleaned tables, {len(impacts)} issues accounted for; review {rv["rows_before_selection"]} -> {rv["rows_after_selection"]}.')
    print(json.dumps(checks,ensure_ascii=False))


if __name__ == '__main__':
    main()
