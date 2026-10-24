"""Gate P06: RFM/Q3, oracle CSV, filter wilayah, dan pelestarian Q1/Q2."""
from collections import defaultdict
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from scripts.assess_data import verify_inputs
from scripts.check_analytics import serial
from src.analytics import build_rfm, analyze_q3, analyze_q1, analyze_q2
from src.config import (
    ANALYSIS_START, ANALYSIS_END_EXCLUSIVE, RFM_REFERENCE_DATE,
    RECENCY_NEW_DAYS, RECENCY_ACTIVE_DAYS, RFM_SEGMENTS,
    HIGH_VALUE_QUANTILE, HIGH_VALUE_INTERPOLATION, SALES_ORDER_STATUS,
)
from src.data_contracts import RFM_CUSTOMER_CONTRACT
from src.data_pipeline import build_analysis_tables


def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def payload_sha(value):
    return hashlib.sha256(json.dumps(serial(value),sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def independent_customers():
    """CSV/Decimal/datetime + dict; tidak memakai flags/segmentasi pandas."""
    def read(name):
        with (ROOT/'data'/f'{name}.csv').open(newline='',encoding='utf-8-sig') as stream: return list(csv.DictReader(stream))
    customers={r['customer_id']:r for r in read('customers_dataset')}
    item_values=defaultdict(list)
    for row in read('order_items_dataset'):
        try:
            number=Decimal(row['price']); scaled=number*100
            valid=number.is_finite() and number>=0 and scaled==scaled.to_integral_value()
        except InvalidOperation: valid=False
        item_values[row['order_id']].append(int(scaled) if valid else None)
    groups={};sales_count=0;sales_value=0;identity_orders=0;identity_value=0
    for row in read('orders_dataset'):
        purchase=datetime.strptime(row['order_purchase_timestamp'],'%Y-%m-%d %H:%M:%S') if row['order_purchase_timestamp'] else None
        values=item_values[row['order_id']]
        if not (purchase and ANALYSIS_START<=purchase.date()<ANALYSIS_END_EXCLUSIVE and row['order_status']==SALES_ORDER_STATUS
                and values and all(v is not None for v in values)): continue
        value=sum(values);sales_count+=1;sales_value+=value
        customer=customers.get(row['customer_id'],{});uid=customer.get('customer_unique_id')
        if not uid or not uid.strip():identity_orders+=1;identity_value+=value;continue
        group=groups.setdefault(uid,{'orders':set(),'monetary':0,'last':None,'last_state':None})
        group['orders'].add(row['order_id']);group['monetary']+=value
        key=(purchase,row['order_id'])
        if group['last'] is None or key>group['last']:
            group['last']=key;group['last_state']=customer.get('customer_state') or None
    refs={}
    for uid,group in groups.items():
        purchase,order_id=group['last'];r=(RFM_REFERENCE_DATE-purchase.date()).days;f=len(group['orders'])
        if f==1: label=RFM_SEGMENTS[0] if r<=RECENCY_NEW_DAYS else RFM_SEGMENTS[1] if r<=RECENCY_ACTIVE_DAYS else RFM_SEGMENTS[2]
        else:label=RFM_SEGMENTS[3] if r<=RECENCY_ACTIVE_DAYS else RFM_SEGMENTS[4]
        refs[uid]={'last_order_id':order_id,'last_purchase_timestamp':purchase.isoformat(),
                   'last_purchase_date':purchase.date().isoformat()+'T00:00:00',
                   'last_order_state':group['last_state'],'recency_days':r,'frequency':f,
                   'monetary_cents':group['monetary'],'segment':label}
    values=[r['monetary_cents'] for r in refs.values()]
    # Algoritmo independen NumPy; data asli jauh di bawah batas representasi integer float.
    assert not values or max(values)<2**53
    threshold=float(np.quantile(np.asarray(values,dtype='int64'),HIGH_VALUE_QUANTILE,method=HIGH_VALUE_INTERPOLATION)) if values else None
    for row in refs.values():row['is_high_value']=row['monetary_cents']>=threshold
    return refs,threshold,{'eligible_sales_orders':sales_count,'eligible_sales_value_cents':sales_value,
                          'excluded_identity_orders':identity_orders,'excluded_identity_value_cents':identity_value}


def verify_summary(q3,refs):
    states=q3['filters']['states'];selected=[r for r in refs.values() if states is None or r['last_order_state'] in states]
    count=len(selected);money=sum(r['monetary_cents'] for r in selected)
    summary=q3['summary']
    assert summary['customer_count']==count and summary['monetary_cents']==money
    assert summary['order_count']==sum(r['frequency'] for r in selected)
    repeat=sum(r['frequency']>=2 for r in selected);high=sum(r['is_high_value'] for r in selected)
    assert summary['repeat_customers']==repeat and summary['high_value_customers']==high
    for row in q3['segments']:
        group=[r for r in selected if r['segment']==row['segment']]
        value=sum(r['monetary_cents'] for r in group)
        assert row['customer_count']==len(group) and row['monetary_cents']==value
        assert row['order_count']==sum(r['frequency'] for r in group)
        assert row['high_value_customers']==sum(r['is_high_value'] for r in group)
        for field,source in [('median_recency_days','recency_days'),('median_frequency','frequency'),('median_monetary_cents','monetary_cents')]:
            expected=statistics.median(r[source] for r in group) if group else None
            assert row[field]==expected
        assert row['customer_contribution_pct']==(100*len(group)/count if count else None)
        assert row['monetary_contribution_pct']==(100*value/money if money else None)
    return {'customer_count':count,'order_count':summary['order_count'],'monetary_cents':money,
            'repeat_customers':repeat,'high_value_customers':high,'reference_matches':True}


def main():
    report_path=ROOT/'reports/analytical_results.json';existing=json.loads(report_path.read_text())
    p5path=ROOT/'reports/analytics_validation.json';p5=json.loads(p5path.read_text())
    assert p5['status']=='passed' and sha(report_path)==p5['analytical_results_sha256']
    p4path=ROOT/'reports/join_audit.json';p4=json.loads(p4path.read_text())
    assert sha(p4path)==existing['join_audit_sha256']==p5['join_audit_sha256']
    baseline=json.loads((ROOT/'reports/baseline.json').read_text());before=verify_inputs(baseline)
    assert before==existing['source_sha256']==p4['source_sha256']
    tables,audit=build_analysis_tables()
    for key in ['aggregation','joins','eligibility','reconciliation','coverage','contracts','payments_policy']:assert audit[key]==p4[key]
    q1=serial(analyze_q1(tables['item_level']));q2=serial(analyze_q2(tables['order_level']))
    assert q1==existing['q1'] and q2==existing['q2'],'Hasil Q1/Q2 berubah; perbarui P05 dahulu'
    for scenario in existing['filter_scenario_summaries'].values():
        f=scenario['filters'];kwargs={'start':f['requested_start'],'end_exclusive':f['requested_end_exclusive'],'states':f['states']}
        assert serial(analyze_q1(tables['item_level'],**kwargs))['summary']==scenario['q1_summary']
        assert serial(analyze_q2(tables['order_level'],**kwargs))['summary']==scenario['q2_summary']
    rfm,metadata=build_rfm(tables['order_level'])
    repeat,repeat_meta=build_rfm(tables['order_level'].sample(frac=1,random_state=42))
    assert_frame_equal(rfm,repeat);assert metadata==repeat_meta
    refs,threshold,coverage=independent_customers()
    assert len(refs)==len(rfm)
    comparisons=0
    for row in serial(rfm):
        ref=refs[row['customer_unique_id']]
        for name,value in ref.items():assert row[name]==value,(row['customer_unique_id'],name);comparisons+=1
    assert metadata['high_value']['threshold_cents']==threshold
    for key,value in coverage.items():assert metadata['reconciliation'][key]==value
    scenarios={'default':None,'SP':['SP'],'RJ':['RJ'],'RR':['RR'],'empty_states':[],'unknown_state':['XX']}
    checks={};summaries={};original=rfm.copy(deep=True)
    for name,states in scenarios.items():
        result=serial(analyze_q3(rfm,metadata,states=states))
        assert result==serial(analyze_q3(rfm,metadata,states=states))
        assert result['high_value']==metadata['high_value']
        checks[name]=verify_summary(result,refs);summaries[name]={'filters':result['filters'],'summary':result['summary']}
        if name=='default':q3=result
    assert_frame_equal(rfm,original)
    rec=metadata['reconciliation'];assert rec['rfm_frequency_sum']==p4['eligibility']['metrics']['eligible_rfm']['eligible_orders']
    assert rec['rfm_monetary_sum_cents']==p4['eligibility']['coverage_differences']['rfm_value_cents']
    assert rfm['recency_days'].ge(0).all() and rfm['frequency'].ge(1).all()
    after=verify_inputs(baseline);assert before==after
    stamp=datetime.now(ZoneInfo('Asia/Jakarta')).isoformat(timespec='seconds')
    dictionary={'phase':'P06','generated_at':stamp,**RFM_CUSTOMER_CONTRACT,
        'fields':{name:{**spec,'observed_dtype':str(rfm[name].dtype),'observed_null_count':int(rfm[name].isna().sum())}
                  for name,spec in RFM_CUSTOMER_CONTRACT['fields'].items()},'metadata':metadata}
    dictionary_path=ROOT/'reports/rfm_data_dictionary.json'
    dictionary_path.write_text(json.dumps(dictionary,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    old_p05=existing.get('p05_original_report_sha256',sha(report_path))
    q3.update({'rfm_metadata':metadata,'filter_scenario_summaries':summaries,
               'data_dictionary':{'path':'reports/rfm_data_dictionary.json','sha256':sha(dictionary_path)}})
    report={**existing,'phase':'P06','generated_at':stamp,'generator':'scripts/check_rfm.py',
            'p05_generated_at':existing.get('p05_generated_at',existing['generated_at']),
            'p05_original_report_sha256':old_p05,
            'runtime':{'python':platform.python_version(),'pandas':pd.__version__,'invocation_cwd':str(Path.cwd())},
            'q3':q3,'gate':{**existing['gate'],'rfm_passed':True,'rfm_deterministic_on_shuffled_orders':True,
                           'q1_q2_preserved_and_reverified':True},
            'scope':'Q1/Q2 dan RFM/Q3; tabel pelanggan dalam memori, ekspor CSV P08 dan visualisasi/narasi akhir P07 belum dibuat.'}
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    # P05 tetap benar: payload Q1/Q2 tidak berubah, hanya laporan bersama diperluas Q3.
    p5['p05_original_report_sha256']=old_p05
    p5['analytical_results_sha256']=sha(report_path)
    p5['extended_by_P06']={'verified_at':stamp,'q1_q2_payload_sha256':payload_sha({'q1':q1,'q2':q2}),
                          'q1_q2_and_six_filter_summaries_unchanged':True,'shared_report_includes_q3':True}
    p5path.write_text(json.dumps(p5,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    validation={'phase':'P06','status':'passed','verified_at':stamp,'invocation_cwd':str(Path.cwd()),
        'analytical_results_sha256':sha(report_path),'rfm_data_dictionary_sha256':sha(dictionary_path),
        'source_sha256':after,'template_hash_unchanged':True,'q1_q2_preserved_and_reverified':True,
        'deterministic_on_shuffled_orders':True,'independent_customer_count':len(refs),
        'independent_field_comparisons':comparisons,'independent_threshold_cents':threshold,
        'reconciliation':rec,'scenarios':checks,'risk_tests_note':'Hasil pytest aktual dicatat pada EXECUTION_STATUS.md.'}
    (ROOT/'reports/rfm_validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(f'PASS P06: {len(rfm):,} customers; frequency {rec["rfm_frequency_sum"]:,}; monetary {rec["rfm_monetary_sum_cents"]:,} cents; Q1/Q2 preserved.')
    print(json.dumps({'summary':q3['summary'],'high_value':q3['high_value'],'segments':q3['segments']},ensure_ascii=False))


if __name__=='__main__':main()
