"""Gate P05: hasil aktual, skenario filter, dan referensi CSV independen."""
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
import csv
import hashlib
import json
import math
from pathlib import Path
import platform
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import numpy as np
import pandas as pd
from src.analytics import analyze_q1, analyze_q2
from src.config import BAD_REVIEW_SCORES, CURRENCY, MIN_STATE_SAMPLE, SALES_ORDER_STATUS, UNKNOWN_CATEGORY_LABEL
from src.data_pipeline import build_analysis_tables
from scripts.assess_data import verify_inputs


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def serial(value):
    if isinstance(value,pd.DataFrame): return serial(value.to_dict('records'))
    if isinstance(value,dict): return {str(k):serial(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)): return [serial(v) for v in value]
    if value is None or value is pd.NA: return None
    if isinstance(value,np.generic): return serial(value.item())
    if isinstance(value,float) and math.isnan(value): return None
    if isinstance(value,pd.Timestamp): return value.isoformat()
    return value


def raw_reference():
    def read(name):
        with (ROOT/'data'/f'{name}.csv').open(newline='',encoding='utf-8-sig') as stream:
            return list(csv.DictReader(stream))
    def dt(value): return datetime.strptime(value,'%Y-%m-%d %H:%M:%S') if value.strip() else None
    orders={r['order_id']:r for r in read('orders_dataset')}
    customers={r['customer_id']:r for r in read('customers_dataset')}
    products={r['product_id']:r for r in read('products_dataset')}
    translation={r['product_category_name']:r['product_category_name_english'] for r in read('product_category_name_translation')}
    items=read('order_items_dataset'); invalid_orders=set(); populated_orders=set()
    for row in items:
        populated_orders.add(row['order_id'])
        try:
            value=Decimal(row['price']); scaled=value*100
            valid=value.is_finite() and value>=0 and scaled==scaled.to_integral_value()
        except InvalidOperation: valid=False
        if not valid: invalid_orders.add(row['order_id'])
        row['cents']=int(scaled) if valid else None
    latest={}
    for n,row in enumerate(read('order_reviews_dataset'),1):
        key=(dt(row['review_creation_date']) or datetime.min,dt(row['review_answer_timestamp']) or datetime.min,row['review_id'],n)
        if row['order_id'] not in latest or key>latest[row['order_id']][0]: latest[row['order_id']]=(key,row)
    for row in orders.values():
        customer=customers.get(row['customer_id'],{})
        row['state']=customer.get('customer_state') or None
        row['purchase']=dt(row['order_purchase_timestamp'])
        row['receipt']=dt(row['order_delivered_customer_date']); row['estimate']=dt(row['order_estimated_delivery_date'])
        review=latest.get(row['order_id'],(None,None))[1]
        try:
            score=Decimal(review['review_score']) if review else None
            valid=score is not None and score.is_finite() and score==score.to_integral_value() and 1<=score<=5
        except InvalidOperation: valid=False
        row['score']=int(score) if valid else None
    return orders,items,products,translation,invalid_orders,populated_orders


def assert_value(actual,expected,context):
    if expected is None: assert actual is None, context
    elif isinstance(expected,float): assert actual is not None and math.isclose(actual,expected,rel_tol=1e-12,abs_tol=1e-10),context
    else: assert actual==expected,context


def verify_reference(q1,q2,raw):
    orders,items,products,translation,invalid,populated=raw
    filters=q1['filters']; states=filters['states']
    start=datetime.fromisoformat(filters['effective_start']) if filters['effective_start'] else None
    end=datetime.fromisoformat(filters['effective_end_exclusive']) if start else None
    selected={k:v for k,v in orders.items() if start and v['purchase'] and start<=v['purchase']<end and (states is None or v['state'] in states)}
    sales_ids={k for k,v in selected.items() if v['order_status']==SALES_ORDER_STATUS and k in populated and k not in invalid}
    categories={}; monthly=defaultdict(lambda: {'value':0,'items':0,'orders':set()}); unique=set(); total=0; nitems=0
    for row in items:
        if row['order_id'] not in sales_ids: continue
        product=products.get(row['product_id'],{}); code=product.get('product_category_name') or None
        name=translation.get(code) or code or UNKNOWN_CATEGORY_LABEL
        cat=categories.setdefault(code,{'value':0,'items':0,'orders':set(),'name':name})
        cat['value']+=row['cents']; cat['items']+=1; cat['orders'].add(row['order_id'])
        month=selected[row['order_id']]['purchase'].strftime('%Y-%m'); m=monthly[(code,month)]
        m['value']+=row['cents'];m['items']+=1;m['orders'].add(row['order_id'])
        total+=row['cents'];nitems+=1;unique.add(row['order_id'])
    s=q1['summary']
    assert (s['sales_value_cents'],s['item_count'],s['order_count'])==(total,nitems,len(unique))
    assert len(q1['categories'])==len(categories)
    for row in q1['categories']:
        code=row['category_code']; ref=categories[code]
        assert (row['sales_value_cents'],row['item_count'],row['order_count'],row['category_name'])==(ref['value'],ref['items'],len(ref['orders']),ref['name'])
        assert_value(row['contribution_pct'],100*ref['value']/total if total else None,'category share')
    top=sorted((k for k in categories if k is not None),key=lambda k:(-categories[k]['value'],k))[:5]
    assert [r['category_code'] for r in q1['top_categories']]==top
    for row in q1['monthly_top_categories']:
        ref=monthly[(row['category_code'],row['month'])]
        assert (row['sales_value_cents'],row['item_count'],row['order_count'])==(ref['value'],ref['items'],len(ref['orders']))
    # Oracle Q2 accumuleert tellers rechtstreeks uit bronrecords, zonder pandas flags.
    def metrics(rows):
        counts={k:0 for k in ['total_delivered','delivery_evaluable','late_orders','on_time_orders','delivery_unavailable',
            'review_comparison_evaluable','comparison_late_orders','comparison_on_time_orders','bad_review_orders',
            'bad_reviews_late','bad_reviews_on_time','review_unavailable_among_delivery']}
        score_sums={True:0,False:0}
        for row in rows:
            if row['order_status']!=SALES_ORDER_STATUS: continue
            counts['total_delivered']+=1
            purchase,receipt,estimate=row['purchase'],row['receipt'],row['estimate']
            if not (purchase and receipt and estimate and receipt>=purchase and estimate.date()>=purchase.date()):
                counts['delivery_unavailable']+=1;continue
            counts['delivery_evaluable']+=1
            late=receipt.date()>estimate.date()
            counts['late_orders' if late else 'on_time_orders']+=1
            if row['score'] is None:
                counts['review_unavailable_among_delivery']+=1;continue
            counts['review_comparison_evaluable']+=1
            counts['comparison_late_orders' if late else 'comparison_on_time_orders']+=1
            score_sums[late]+=row['score']
            if row['score'] in BAD_REVIEW_SCORES:
                counts['bad_review_orders']+=1;counts['bad_reviews_late' if late else 'bad_reviews_on_time']+=1
        pct=lambda n,d:100*n/d if d else None
        a=pct(counts['bad_reviews_late'],counts['comparison_late_orders']);b=pct(counts['bad_reviews_on_time'],counts['comparison_on_time_orders'])
        return {**counts,'late_rate_pct':pct(counts['late_orders'],counts['delivery_evaluable']),
                'bad_review_rate_pct':pct(counts['bad_review_orders'],counts['review_comparison_evaluable']),
                'bad_review_rate_late_pct':a,'bad_review_rate_on_time_pct':b,
                'bad_review_rate_difference_pp':a-b if a is not None and b is not None else None},score_sums
    expected,scores=metrics(selected.values())
    assert q2['summary']['orders_in_filter']==len(selected)
    for key,value in expected.items(): assert_value(q2['summary'][key],value,key)
    bystate=defaultdict(list)
    for row in selected.values(): bystate[row['state']].append(row)
    state_refs={k:metrics(rows)[0] for k,rows in bystate.items()}
    state_refs={k:v for k,v in state_refs.items() if v['total_delivered']}
    assert len(q2['states'])==len(state_refs)
    for row in q2['states']:
        for key,value in state_refs[row['customer_state']].items(): assert_value(row[key],value,f'state {key}')
    priority=sorted((k for k,v in state_refs.items() if k and v['review_comparison_evaluable']>=MIN_STATE_SAMPLE),
        key=lambda k:(-state_refs[k]['late_rate_pct'],-state_refs[k]['bad_review_rate_pct'],-state_refs[k]['review_comparison_evaluable'],k))
    assert [row['customer_state'] for row in q2['priority_states']]==priority
    for row in q2['comparison_groups']:
        late=row['is_late'];denom=expected['comparison_late_orders' if late else 'comparison_on_time_orders']
        assert row['review_order_count']==denom
        assert_value(row['mean_review_score'],scores[late]/denom if denom else None,'mean review score')
    return {'independent_reference_matches':True,'sales_orders':len(unique),'sales_items':nitems,
            'sales_value_cents':total,'q2_summary':expected,'priority_state_codes':priority}


def main():
    baseline=json.loads((ROOT/'reports/baseline.json').read_text())
    p4path=ROOT/'reports/join_audit.json';p4=json.loads(p4path.read_text())
    proof=json.loads((ROOT/'reports/integration_validation.json').read_text())
    assert proof['status']=='passed' and sha(p4path)==proof['join_audit_sha256']
    assert sha(ROOT/'reports/data_dictionary.json')==proof['data_dictionary_sha256']
    assert sha(ROOT/'reports/cleaning_audit.json')==p4['cleaning_audit_sha256']
    before=verify_inputs(baseline); assert before==p4['source_sha256']
    tables,audit=build_analysis_tables()
    for key in ['aggregation','joins','eligibility','reconciliation','coverage','contracts','payments_policy']:
        assert audit[key]==p4[key],f'P04 dependency changed: {key}'
    raw=raw_reference()
    scenarios={'default':{},'state_sp':{'states':['SP']},'small_rr_january':{'states':['RR'],'start':'2017-01-01','end_exclusive':'2017-02-01'},
               'partial_month':{'states':['SP','RJ'],'start':'2018-02-10','end_exclusive':'2018-03-06'},
               'empty_states':{'states':[]},'outside_period':{'start':'2018-09-01','end_exclusive':'2018-10-01'}}
    checks={};results={}
    for name,kwargs in scenarios.items():
        q1=serial(analyze_q1(tables['item_level'],**kwargs));q2=serial(analyze_q2(tables['order_level'],**kwargs))
        assert q1==serial(analyze_q1(tables['item_level'],**kwargs))
        assert q2==serial(analyze_q2(tables['order_level'],**kwargs))
        checks[name]=verify_reference(q1,q2,raw)
        results[name]={'filters':q1['filters'],'q1_summary':q1['summary'],'q2_summary':q2['summary']}
        if name=='default': default_q1,default_q2=q1,q2
    assert default_q1['summary']['sales_value_cents']==p4['reconciliation']['eligible_order_value_cents']
    assert default_q1['summary']['item_count']==p4['reconciliation']['eligible_sales_items']
    assert default_q2['summary']['delivery_evaluable']==p4['eligibility']['metrics']['eligible_delivery']['eligible_orders']
    assert default_q2['summary']['review_comparison_evaluable']==p4['eligibility']['metrics']['eligible_review_comparison']['eligible_orders']
    after=verify_inputs(baseline); assert before==after
    stamp=datetime.now(ZoneInfo('Asia/Jakarta')).isoformat(timespec='seconds')
    report={'phase':'P05','status':'completed','generated_at':stamp,'generator':'scripts/check_analytics.py',
            'runtime':{'python':platform.python_version(),'pandas':pd.__version__,'invocation_cwd':str(Path.cwd())},
            'currency':CURRENCY,'source_sha256':after,'join_audit_sha256':sha(p4path),
            'q1':default_q1,'q2':default_q2,'filter_scenario_summaries':results,
            'gate':{'passed':True,'source_hashes_unchanged':True,'p04_outputs_unchanged':True,
                    'deterministic_repeated_aggregations':True,'independent_reference_scenarios':list(checks)},
            'scope':'Agregasi Q1/Q2; visualisasi/narasi akhir P07, RFM/Q3 P06 belum dijalankan.'}
    path=ROOT/'reports/analytical_results.json'
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    validation={'phase':'P05','status':'passed','verified_at':stamp,'invocation_cwd':str(Path.cwd()),
                'analytical_results_sha256':sha(path),'join_audit_sha256':sha(p4path),
                'nine_source_hashes_unchanged':True,'template_hash_unchanged':True,
                'p04_outputs_unchanged':True,'deterministic_repeated_aggregations':True,'scenarios':checks}
    (ROOT/'reports/analytics_validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print('PASS P05: Q1/Q2, 6 filter scenarios, independent CSV reference; 9 source hashes unchanged.')
    print(json.dumps({'q1':default_q1['summary'],'top_categories':default_q1['top_categories'],
                      'q2':default_q2['summary'],'comparison':default_q2['comparison_groups'],
                      'priority_states':default_q2['priority_states'][:5]},ensure_ascii=False))


if __name__=='__main__': main()
