"""Gate P04: joins, eligibility, kontrak, serta rekonsiliasi independen CSV."""
from collections import Counter, defaultdict
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
from src.config import ANALYSIS_START, ANALYSIS_END_EXCLUSIVE, CURRENCY, SALES_ORDER_STATUS
from src.data_contracts import TABLE_CONTRACTS
from src.data_pipeline import build_analysis_tables, clean_primary_sources


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_rows(name):
    with (ROOT/'data'/f'{name}.csv').open(newline='',encoding='utf-8-sig') as stream:
        return list(csv.DictReader(stream))


def independent_reference(tables):
    """Gunakan csv/datetime/Decimal/dict, tanpa helper join/eligibility pipeline."""
    raw_orders=read_rows('orders_dataset'); raw_items=read_rows('order_items_dataset')
    customers={r['customer_id']:r for r in read_rows('customers_dataset')}
    products={r['product_id']:r for r in read_rows('products_dataset')}
    translation={r['product_category_name']:r['product_category_name_english'] for r in read_rows('product_category_name_translation')}
    grouped=defaultdict(list); item_refs={}; selected={}
    def dt(value):
        return datetime.strptime(value,'%Y-%m-%d %H:%M:%S') if value.strip() else None
    def cents(value):
        if not value.strip():
            return None
        number=Decimal(value)
        assert number.is_finite() and number>=0
        value=number*100
        assert value==value.to_integral_value()
        return int(value)
    for row in raw_items:
        grouped[row['order_id']].append(row)
        item_refs[(row['order_id'],row['order_item_id'])]=row
    for rownum,row in enumerate(read_rows('order_reviews_dataset'),1):
        key=(dt(row['review_creation_date']) or datetime.min,dt(row['review_answer_timestamp']) or datetime.min,row['review_id'],rownum)
        if row['order_id'] not in selected or key>selected[row['order_id']][0]:
            selected[row['order_id']]=(key,row)
    refs={}; flags=Counter(); expected_price=0; expected_items=0
    for raw in raw_orders:
        order_id=raw['order_id']; rows=grouped[order_id]; purchase=dt(raw['order_purchase_timestamp'])
        receipt=dt(raw['order_delivered_customer_date']); estimate=dt(raw['order_estimated_delivery_date'])
        in_period=bool(purchase and ANALYSIS_START<=purchase.date()<ANALYSIS_END_EXCLUSIVE)
        delivered=raw['order_status']==SALES_ORDER_STATUS
        values=[cents(i['price']) for i in rows]
        complete=bool(rows) and all(v is not None for v in values)
        value=sum(values) if complete else None
        sale=in_period and delivered and complete
        valid_dates=bool(purchase and receipt and estimate and receipt>=purchase and estimate.date()>=purchase.date())
        delivery=in_period and delivered and valid_dates
        review=selected.get(order_id,(None,None))[1]
        score=Decimal(review['review_score']) if review and review['review_score'].strip() else None
        score_valid=bool(score is not None and score.is_finite() and score==score.to_integral_value() and 1<=score<=5)
        customer=customers.get(raw['customer_id'])
        identity=bool(customer and customer['customer_unique_id'].strip())
        reference={
            'order_value_cents':value, 'item_count':len(rows),
            'customer_matched':customer is not None, 'customer_identity_valid':identity,
            'review_matched':review is not None, 'review_score':int(score) if score_valid else None,
            'review_score_valid':score_valid,'in_analysis_period':in_period,
            'eligible_sales':sale,'eligible_delivery':delivery,
            'eligible_review_comparison':delivery and score_valid,'eligible_rfm':sale and identity,
            'is_late':receipt.date()>estimate.date() if valid_dates else None,
            'days_late':max((receipt.date()-estimate.date()).days,0) if valid_dates else None,
            'purchase_month':purchase.strftime('%Y-%m') if purchase else None,
            'customer_unique_id':customer['customer_unique_id'] if identity else None,
            'customer_state':customer['customer_state'] if customer and customer['customer_state'] else None,
        }
        refs[order_id]=reference
        for flag in ('eligible_sales','eligible_delivery','eligible_review_comparison','eligible_rfm'):
            flags[flag]+=int(reference[flag])
        if sale:
            expected_price+=value; expected_items+=len(rows)
    orders=tables['order_level']; items=tables['item_level']
    assert len(orders)==len(raw_orders) and len(items)==len(raw_items)
    assert set(orders['order_id'])==set(refs)
    comparisons=0
    for row in orders.to_dict('records'):
        expected=refs[row['order_id']]
        for name,value in expected.items():
            actual=None if pd.isna(row[name]) else row[name]
            assert actual==value, f'Independent reference mismatch: order {row["order_id"]}, {name}'
            comparisons+=1
    for row in items.to_dict('records'):
        source=item_refs[(row['order_id'],row['order_item_id'])]
        product=products.get(source['product_id']); code=product['product_category_name'] if product else None
        code=code if code and code.strip() else None
        english=translation.get(code) if code else None
        english=english if english and english.strip() else None
        assert row['price_cents']==cents(source['price'])
        assert row['freight_cents']==cents(source['freight_value'])
        assert row['category_name']==(english or code or 'Tidak diketahui')
        assert bool(row['category_missing'])==(code is None)
        assert bool(row['category_translation_missing'])==bool(code and not english)
        assert bool(row['eligible_sales'])==refs[row['order_id']]['eligible_sales']
    eligible_items=items.loc[items['eligible_sales']]
    assert sum(int(v) for v in eligible_items['price_cents'])==expected_price
    assert len(eligible_items)==expected_items
    assert orders['order_status'].value_counts().to_dict()==dict(Counter(o['order_status'] for o in raw_orders))
    return {'order_field_comparisons':comparisons,'item_rows_checked':len(items),
            'order_rows_checked':len(orders),'eligibility_counts':dict(flags),
            'eligible_sales_value_cents':expected_price,'eligible_sales_item_count':expected_items,
            'all_order_statuses_preserved':True}


def main():
    baseline=json.loads((ROOT/'reports/baseline.json').read_text())
    cleaning_path=ROOT/'reports/cleaning_audit.json'
    previous=json.loads((ROOT/'reports/cleaning_validation.json').read_text())
    assert previous['status']=='passed' and sha(cleaning_path)==previous['cleaning_audit_sha256']
    assert sha(ROOT/'reports/review_selection.csv')==previous['review_selection_sha256']
    before=verify_inputs(baseline)
    assert before==json.loads(cleaning_path.read_text())['source_sha256']
    cleaned,_=clean_primary_sources()
    tables,audit=build_analysis_tables(cleaned)
    repeat,repeat_audit=build_analysis_tables(cleaned)
    for name,frame in tables.items():
        assert_frame_equal(frame,repeat[name])
    assert audit==repeat_audit
    del repeat,repeat_audit
    reference=independent_reference(tables)
    for flag,count in reference['eligibility_counts'].items():
        assert audit['eligibility']['metrics'][flag]['eligible_orders']==count
        reasons=audit['eligibility']['metrics'][flag]['exclusive_first_failure_counts']
        assert sum(reasons.values())+count==len(tables['order_level'])
    after=verify_inputs(baseline)
    assert before==after
    stamp=datetime.now(ZoneInfo('Asia/Jakarta')).isoformat(timespec='seconds')
    dictionary={
        'schema_version':1,'phase':'P04','generated_at':stamp,
        'currency':CURRENCY,'analysis_period':{'start_inclusive':str(ANALYSIS_START),'end_exclusive':str(ANALYSIS_END_EXCLUSIVE)},
        'status_policy':'Snapshot dataset; bukan rekonstruksi status historis setiap bulan',
        'money_policy':'Integer sen; null untuk order tanpa item atau setidaknya satu harga invalid. Bukan laba atau total pembayaran.',
        'tables':{name:{'grain':TABLE_CONTRACTS[name]['grain'],
                        'primary_key':TABLE_CONTRACTS[name]['primary_key'],'row_count':len(frame),
                        'fields':{col:{**spec,'observed_dtype':str(frame[col].dtype),'observed_null_count':int(frame[col].isna().sum())}
                                  for col,spec in TABLE_CONTRACTS[name]['fields'].items()}}
                  for name,frame in tables.items()},
    }
    dictionary_path=ROOT/'reports/data_dictionary.json'
    dictionary_path.write_text(json.dumps(dictionary,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    report={
        'phase':'P04','status':'completed','verified_at':stamp,'generator':'scripts/check_integration.py',
        'runtime':{'python':platform.python_version(),'pandas':pd.__version__,'invocation_cwd':str(Path.cwd())},
        'source_sha256':after,'cleaning_audit_sha256':sha(cleaning_path),
        'data_dictionary':{'path':'reports/data_dictionary.json','sha256':sha(dictionary_path)},
        **audit,
        'assessment_issue_handoff':{
            'DQ13':{'status':'handled','orders_without_items':audit['coverage']['orders_without_items'],'policy':'Order dipertahankan, item_count 0, order_value null, sales/RFM false; delivery independen.'},
            'DQ14':{'status':'handled','orders_without_review':audit['coverage']['orders_without_review'],'policy':'Order dipertahankan; review null, comparison false; sales/delivery independen.'},
            'DQ15':{'status':'documented_not_used','policy':audit['payments_policy']},
        },
        'gate':{'passed':True,'deterministic_second_build':True,'source_hashes_unchanged':True,
                'six_validated_left_joins':len(audit['joins'])==6,'independent_reference':reference},
        'scope':'Tabel order/item direproduksi dalam memori. Ekspor CSV/dashboard dan metadata paket menjadi milik P08; analisis Q1–Q3 belum dikerjakan.',
    }
    report_path=ROOT/'reports/join_audit.json'
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    validation={
        'phase':'P04','status':'passed','verified_at':stamp,'invocation_cwd':str(Path.cwd()),
        'join_audit_sha256':sha(report_path),'data_dictionary_sha256':sha(dictionary_path),
        'nine_source_hashes_unchanged':True,'template_hash_unchanged':True,
        'deterministic_second_build':True,'independent_reference':reference,
        'rows_after':{name:len(frame) for name,frame in tables.items()},
        'note':'Tes pipeline dijalankan terpisah; hasil aktual dicatat dalam EXECUTION_STATUS.md.',
    }
    (ROOT/'reports/integration_validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
    print(f'PASS P04: {len(tables["order_level"]):,} orders, {len(tables["item_level"]):,} items, 6 validated left joins.')
    print(json.dumps(reference,ensure_ascii=False))


if __name__=='__main__':
    main()
