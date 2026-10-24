"""Oracle kecil Q1/Q2: denominator, filter, kalender, peringkat, unavailable."""
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from src.analytics import analyze_q1, analyze_q2, filter_sales


def sales_items(records):
    defaults={'order_id':'o1','order_item_id':'1','order_purchase_timestamp':'2017-01-15',
              'purchase_month':'2017-01','customer_state':'SP','in_analysis_period':True,'eligible_sales':True,
              'category_code':'a','category_name':'Alpha','category_missing':False,'price_cents':100}
    frame=pd.DataFrame([defaults|r for r in records])
    frame['order_purchase_timestamp']=pd.to_datetime(frame['order_purchase_timestamp'])
    for c in ['price_cents']: frame[c]=frame[c].astype('Int64')
    for c in ['category_code','category_name','order_id','order_item_id','customer_state','purchase_month']: frame[c]=frame[c].astype('string')
    for c in ['category_missing','in_analysis_period','eligible_sales']: frame[c]=frame[c].astype('boolean')
    return frame


def order_rows(records):
    defaults={'order_id':'o1','order_purchase_timestamp':'2017-01-15','customer_state':'SP',
              'order_status':'delivered','in_analysis_period':True,'eligible_delivery':True,
              'eligible_review_comparison':True,'is_late':False,'review_score':5}
    frame=pd.DataFrame([defaults|r for r in records])
    frame['order_purchase_timestamp']=pd.to_datetime(frame['order_purchase_timestamp'])
    for c in ['order_id','customer_state','order_status']: frame[c]=frame[c].astype('string')
    for c in ['in_analysis_period','eligible_delivery','eligible_review_comparison','is_late']: frame[c]=frame[c].astype('boolean')
    frame['review_score']=frame['review_score'].astype('Int64')
    return frame


def test_q1_unknown_remains_in_denominator_and_multi_category_order_is_unique_globally():
    items=sales_items([{}, {'order_item_id':'2','category_code':'b','category_name':'Beta','price_cents':200},
                       {'order_id':'o2','category_code':pd.NA,'category_name':'Tidak diketahui','category_missing':True,'price_cents':100}])
    before=items.copy(deep=True); result=analyze_q1(items)
    assert result['summary']['sales_value_cents']==400 and result['summary']['order_count']==2
    assert result['categories']['order_count'].sum()==3
    assert result['summary']['unknown_category_contribution_pct']==25
    assert result['top_categories']['category_code'].tolist()==['b','a']
    assert result['categories']['contribution_pct'].sum()==100
    assert_frame_equal(items,before)


def test_q1_top_five_ties_follow_code_and_do_not_change_each_month():
    records=[]
    for code in ['f','e','d','c','b','a']:
        records.append({'order_id':code,'category_code':code,'category_name':code,
                        'order_purchase_timestamp':'2017-01-20' if code=='f' else '2017-02-02',
                        'purchase_month':'2017-01' if code=='f' else '2017-02'})
    result=analyze_q1(sales_items(records),end_exclusive='2017-03-01')
    assert result['top_categories']['category_code'].tolist()==['a','b','c','d','e']
    series=result['monthly_top_categories']
    assert set(series['category_code'])==set('abcde') and len(series)==10
    assert series.loc[series['month'].eq('2017-01'),'sales_value_cents'].sum()==0
    assert result['summary']['top_five_contribution_pct']==pytest.approx(500/6)


def test_q1_month_grid_covers_selected_calendar_and_marks_partial_months():
    result=analyze_q1(sales_items([{'order_purchase_timestamp':'2017-01-21'}]),
                      start='2017-01-20',end_exclusive='2017-03-05')
    cal=result['monthly_calendar']
    assert cal['month'].tolist()==['2017-01','2017-02','2017-03']
    assert cal['is_partial_month'].tolist()==[True,False,True]
    assert cal.loc[0,'window_start']=='2017-01-20' and cal.loc[2,'window_end_exclusive']=='2017-03-05'
    assert result['monthly_top_categories']['sales_value_cents'].tolist()==[100,0,0]


def test_q1_active_filter_reselects_top_once_for_that_filter():
    items=sales_items([{}, {'order_id':'o2','category_code':'b','category_name':'Beta','price_cents':300,'customer_state':'RJ'}])
    assert analyze_q1(items)['top_categories'].loc[0,'category_code']=='b'
    result=analyze_q1(items,states=['SP'])
    assert result['summary']['sales_value_cents']==100 and result['top_categories']['category_code'].tolist()==['a']


def test_q1_zero_total_keeps_valid_zero_items_but_shares_unavailable():
    result=analyze_q1(sales_items([{'price_cents':0}]))
    assert result['summary']['item_count']==1 and result['summary']['sales_value_cents']==0
    assert result['summary']['top_five_contribution_pct'] is None
    assert result['categories']['contribution_pct'].isna().all()


@pytest.mark.parametrize('states', [[],['XX']])
def test_q1_empty_filter_has_no_sales_and_unavailable_share(states):
    result=analyze_q1(sales_items([{}]),states=states)
    assert result['summary']['item_count']==0 and result['summary']['order_count']==0
    assert result['summary']['unknown_category_contribution_pct'] is None
    assert result['top_categories'].empty and result['monthly_top_categories'].empty
    assert len(result['monthly_calendar'])==20


def test_filter_intersects_main_period_and_does_not_zero_fill_outside_it():
    items=sales_items([{}])
    r=analyze_q1(items,start='2016-01-01',end_exclusive='2017-03-01')
    assert r['monthly_calendar']['month'].tolist()==['2017-01','2017-02']
    assert r['filters']['range_clipped_to_analysis_period']
    outside=analyze_q1(items,start='2018-09-01',end_exclusive='2018-10-01')
    assert outside['monthly_calendar'].empty and outside['summary']['sales_value_cents']==0


def test_end_exclusive_and_ineligible_sales_are_excluded():
    items=sales_items([{}, {'order_id':'o2','order_purchase_timestamp':'2017-02-01','purchase_month':'2017-02'},
                       {'order_id':'o3','eligible_sales':False}])
    assert len(filter_sales(items,end_exclusive='2017-02-01'))==1


def test_q1_rejects_duplicate_item_keys():
    items=sales_items([{},{}])
    with pytest.raises(ValueError,match='unik'): analyze_q1(items)


def test_q2_denominators_coverage_and_difference_are_percentage_points():
    orders=order_rows([
        {'order_id':'l1','is_late':True,'review_score':1},
        {'order_id':'l2','is_late':True,'review_score':5},
        {'order_id':'l3','is_late':True,'review_score':pd.NA,'eligible_review_comparison':False},
        {'order_id':'t1','review_score':2}, {'order_id':'t2'}, {'order_id':'t3'}, {'order_id':'t4'},
        {'order_id':'missing','eligible_delivery':False,'eligible_review_comparison':False,'is_late':pd.NA,'review_score':pd.NA},
        {'order_id':'canceled','order_status':'canceled','eligible_delivery':False,'eligible_review_comparison':False,'is_late':pd.NA},
    ])
    before=orders.copy(deep=True); result=analyze_q2(orders); s=result['summary']
    assert s['orders_in_filter']==9 and s['total_delivered']==8 and s['delivery_evaluable']==7
    assert s['delivery_unavailable']==1 and s['review_unavailable_among_delivery']==1
    assert s['late_rate_pct']==pytest.approx(300/7)
    assert s['bad_review_rate_late_pct']==50 and s['bad_review_rate_on_time_pct']==25
    assert s['bad_review_rate_difference_pp']==25
    g=result['comparison_groups'].iloc[0]
    assert g['delivery_order_count']==3 and g['review_order_count']==2 and g['mean_review_score']==3
    assert_frame_equal(orders,before)


def test_q2_missing_group_makes_delta_unavailable_not_zero():
    result=analyze_q2(order_rows([{'review_score':1}]))
    assert result['summary']['bad_review_rate_on_time_pct']==100
    assert result['summary']['bad_review_rate_late_pct'] is None
    assert result['summary']['bad_review_rate_difference_pp'] is None
    assert pd.isna(result['comparison_groups'].iloc[0]['bad_review_rate_pct'])


def test_q2_no_reviews_keeps_delivery_rate_but_review_rates_unavailable():
    result=analyze_q2(order_rows([{'is_late':True,'review_score':pd.NA,'eligible_review_comparison':False}]))
    assert result['summary']['late_rate_pct']==100
    assert result['summary']['bad_review_rate_pct'] is None
    assert result['summary']['review_unavailable_among_delivery']==1
    assert result['priority_states'].empty and len(result['states'])==1


@pytest.mark.parametrize('states', [[],['XX']])
def test_q2_empty_filter_rates_unavailable_and_zero_counts(states):
    result=analyze_q2(order_rows([{}]),states=states)
    assert result['summary']['total_delivered']==0 and result['summary']['late_rate_pct'] is None
    assert result['summary']['bad_review_rate_difference_pp'] is None
    assert result['states'].empty and result['priority_states'].empty
    assert result['comparison_groups']['review_order_count'].tolist()==[0,0]


def test_state_priority_sample_boundary_and_sort_policy():
    records=[]
    # RR below threshold despite 100% late. BA/SP tie all rates: sample size then code.
    for state,n,late,bad in [('RR',49,49,49),('BA',50,10,20),('SP',100,20,40),('AC',50,10,20),('RJ',50,10,10),('AM',50,20,0)]:
        for k in range(n): records.append({'order_id':f'{state}{k}','customer_state':state,'is_late':k<late,'review_score':1 if k<bad else 5})
    result=analyze_q2(order_rows(records))
    assert result['priority_states']['customer_state'].tolist()==['AM','SP','AC','BA','RJ']
    rr=result['states'].set_index('customer_state').loc['RR']
    assert not rr['rank_eligible'] and pd.isna(rr['priority_rank']) and rr['review_comparison_evaluable']==49
    assert len(result['states'])==6


def test_state_sample_threshold_uses_review_comparison_not_delivery_count():
    records=[{'order_id':str(k),'eligible_review_comparison':k<49,'review_score':5 if k<49 else pd.NA} for k in range(80)]
    r=analyze_q2(order_rows(records))
    assert r['states'].iloc[0]['delivery_evaluable']==80 and r['priority_states'].empty


def test_missing_state_is_preserved_in_coverage_and_not_ranked():
    r=analyze_q2(order_rows([{'order_id':str(k),'customer_state':pd.NA} for k in range(50)]))
    assert r['summary']['total_delivered']==50 and r['states'].iloc[0]['total_delivered']==50
    assert r['priority_states'].empty and r['states'].iloc[0]['rank_exclusion_reason']=='unknown_state'


def test_q2_rejects_item_grain_duplicate_order():
    with pytest.raises(ValueError,match='satu baris'): analyze_q2(order_rows([{},{}]))


@pytest.mark.parametrize('kwargs', [{'start':'2018-02-01','end_exclusive':'2018-01-01'},
                                   {'start':'2018-01-01 12:00:00'},{'states':[None]}])
def test_invalid_filters_fail_clearly(kwargs):
    with pytest.raises(ValueError): analyze_q1(sales_items([{}]),**kwargs)


# P06 — RFM
from src.analytics import build_rfm, segment_rfm, filter_rfm, analyze_q3
from src.config import RFM_REFERENCE_DATE, RFM_SEGMENTS


def rfm_orders(records):
    defaults={'order_id':'o1','customer_id':'c1','customer_unique_id':'u1','customer_state':'SP',
              'order_purchase_timestamp':'2018-08-01 23:59:00','order_value_cents':100,
              'eligible_sales':True,'eligible_rfm':True,'customer_identity_valid':True}
    frame=pd.DataFrame([defaults|row for row in records])
    frame['order_purchase_timestamp']=pd.to_datetime(frame['order_purchase_timestamp'],format='ISO8601')
    for col in ['order_id','customer_id','customer_unique_id','customer_state']: frame[col]=frame[col].astype('string')
    for col in ['eligible_sales','eligible_rfm','customer_identity_valid']: frame[col]=frame[col].astype('boolean')
    frame['order_value_cents']=frame['order_value_cents'].astype('Int64')
    return frame


@pytest.mark.parametrize('recency,frequency,label',[(30,1,0),(31,1,1),(90,1,1),(91,1,2),
                                                   (30,2,3),(31,2,3),(90,2,3),(91,2,4)])
def test_rfm_segment_boundaries_are_calendar_days(recency,frequency,label):
    purchase=(pd.Timestamp(RFM_REFERENCE_DATE)-pd.Timedelta(days=recency)).strftime('%Y-%m-%d')+' 23:59:00'
    records=[{'order_id':str(k),'order_purchase_timestamp':purchase} for k in range(frequency)]
    rfm,meta=build_rfm(rfm_orders(records))
    assert rfm.loc[0,'recency_days']==recency
    assert rfm.loc[0,'frequency']==frequency and rfm.loc[0,'segment']==RFM_SEGMENTS[label]
    assert meta['reconciliation']['rfm_frequency_sum']==frequency


def test_two_customer_ids_same_unique_customer_with_multiple_items_counts_two_orders():
    from test_pipeline import integration_sources, order, item, review
    from src.data_pipeline import build_analysis_tables
    cleaned=integration_sources(
        order_records=[order(order_id='o1',customer_id='c1'),
                       order(order_id='o2',customer_id='c2',order_purchase_timestamp='2018-02-01 12:00:00')],
        item_records=[item(order_id='o1',price='10.00'),item(order_id='o1',order_item_id='2',price='20.00'),
                      item(order_id='o2',price='30.00'),item(order_id='o2',order_item_id='2',price='40.00')],
        customer_records=[{'customer_id':'c1','customer_unique_id':'u1','customer_state':'SP'},
                          {'customer_id':'c2','customer_unique_id':'u1','customer_state':'RJ'}],
        review_records=[review()])
    tables,_=build_analysis_tables(cleaned)
    rfm,_=build_rfm(tables['order_level'])
    assert len(rfm)==1 and rfm.loc[0,'frequency']==2 and rfm.loc[0,'monetary_cents']==10000
    assert rfm.loc[0,'last_order_state']=='RJ' and rfm.loc[0,'last_order_id']=='o2'


def test_last_order_tie_break_uses_timestamp_then_lexical_order_id_and_ignores_input_order():
    orders=rfm_orders([{'order_id':'z','customer_state':'RJ'}, {'order_id':'a','customer_state':'SP'},
                      {'order_id':'zz','customer_state':'AM','order_purchase_timestamp':'2018-07-01 00:00:00'}])
    first,_=build_rfm(orders);second,_=build_rfm(orders.iloc[::-1])
    assert_frame_equal(first,second)
    assert first.loc[0,'last_order_id']=='z' and first.loc[0,'last_order_state']=='RJ'


def test_last_order_missing_state_does_not_fall_back_to_old_state():
    orders=rfm_orders([{'order_id':'o1'}, {'order_id':'o2','order_purchase_timestamp':'2018-08-02','customer_state':pd.NA}])
    rfm,meta=build_rfm(orders)
    assert pd.isna(rfm.loc[0,'last_order_state']) and filter_rfm(rfm,states=['SP']).empty
    assert analyze_q3(rfm,meta)['summary']['customer_count']==1


def test_region_filter_keeps_all_customer_orders_and_global_high_value_threshold():
    orders=rfm_orders([
        {'order_id':'a','order_value_cents':100,'order_purchase_timestamp':'2018-07-01','customer_state':'SP'},
        {'order_id':'b','order_value_cents':100,'customer_state':'RJ'},
        {'order_id':'c','customer_unique_id':'u2','order_value_cents':1000},
        {'order_id':'d','customer_unique_id':'u3','order_value_cents':2000},
        {'order_id':'e','customer_unique_id':'u4','order_value_cents':3000},
    ])
    original=orders.copy(deep=True);rfm,meta=build_rfm(orders)
    selected=filter_rfm(rfm,states=['RJ']);q3=analyze_q3(rfm,meta,states=['RJ'])
    assert len(selected)==1 and selected.iloc[0]['frequency']==2 and selected.iloc[0]['monetary_cents']==200
    assert q3['high_value']['threshold_cents']==2250
    assert q3['summary']['high_value_customers']==0  # local one-customer P75 would falsely label it high.
    assert q3['summary']['order_count']==2 and q3['summary']['monetary_cents']==200
    assert_frame_equal(orders,original)


def test_fractional_cent_quantile_is_not_rounded_and_comparison_is_inclusive():
    rfm,meta=build_rfm(rfm_orders([{'order_id':str(k),'customer_unique_id':str(k),'order_value_cents':v}
                                  for k,v in enumerate([100,101,102,103])]))
    assert meta['high_value']['threshold_cents']==102.25
    assert meta['high_value']['threshold_cents_exact']=={'numerator':409,'denominator':4}
    assert rfm['is_high_value'].tolist()==[False,False,False,True]
    ties,meta=build_rfm(rfm_orders([{'order_id':str(k),'customer_unique_id':str(k),'order_value_cents':200} for k in range(4)]))
    assert ties['is_high_value'].all() and meta['high_value']['customers_at_threshold']==4
    assert analyze_q3(ties,meta)['summary']['high_value_customer_pct']==100


def test_high_value_comparison_does_not_lose_fraction_beyond_float_integer_precision():
    rfm,_=build_rfm(rfm_orders([{'order_id':str(k),'customer_unique_id':str(k),'order_value_cents':2**53+k} for k in range(4)]))
    assert rfm['is_high_value'].tolist()==[False,False,False,True]


def test_empty_rfm_population_is_typed_and_summary_percentages_unavailable():
    rfm,meta=build_rfm(rfm_orders([{'eligible_sales':False,'eligible_rfm':False}]))
    q3=analyze_q3(rfm,meta)
    assert rfm.empty and meta['high_value']['threshold_cents'] is None
    assert q3['summary']['repeat_customer_pct'] is None and len(q3['segments'])==5
    assert q3['segments']['median_recency_days'].isna().all()
    assert q3['segments']['customer_contribution_pct'].isna().all()
    assert q3['frequency_distribution'].empty


def test_empty_region_filter_retains_global_threshold_and_empty_segment_medians():
    rfm,meta=build_rfm(rfm_orders([{}]))
    q3=analyze_q3(rfm,meta,states=[])
    assert q3['summary']['customer_count']==0 and q3['high_value']==meta['high_value']
    assert q3['segments']['median_monetary_cents'].isna().all()


def test_zero_monetary_has_unavailable_value_shares_but_valid_customer_shares():
    rfm,meta=build_rfm(rfm_orders([{'order_value_cents':0}]))
    q3=analyze_q3(rfm,meta)
    assert q3['summary']['monetary_cents']==0 and rfm.loc[0,'is_high_value']
    assert q3['segments']['monetary_contribution_pct'].isna().all()
    assert q3['segments']['customer_contribution_pct'].sum()==100


def test_identity_exclusions_explain_rfm_sales_difference_without_dropping_global_sales():
    rfm,meta=build_rfm(rfm_orders([{}, {'order_id':'o2','customer_unique_id':pd.NA,'customer_identity_valid':False,'eligible_rfm':False,'order_value_cents':500}]))
    assert len(rfm)==1 and meta['reconciliation']['excluded_identity_orders']==1
    assert meta['reconciliation']['excluded_identity_value_cents']==500
    assert meta['reconciliation']['eligible_sales_value_cents']==600 and meta['reconciliation']['rfm_monetary_sum_cents']==100


@pytest.mark.parametrize('r,f',[(-1,1),(30,0),(30.5,1),(30,1.5)])
def test_invalid_rfm_dimensions_are_rejected(r,f):
    with pytest.raises(ValueError): segment_rfm(pd.DataFrame({'recency_days':[r],'frequency':[f]}))


def test_duplicate_order_grain_and_invalid_eligible_dates_are_rejected():
    with pytest.raises(ValueError,match='satu baris'):build_rfm(rfm_orders([{},{}]))
    with pytest.raises(ValueError,match='periode acuan'):build_rfm(rfm_orders([{'order_purchase_timestamp':'2018-09-02'}]))


def test_rfm_monetary_overflow_is_rejected():
    with pytest.raises(ValueError,match='Int64'):build_rfm(rfm_orders([{'order_id':'a','order_value_cents':2**63-1},
                                                                    {'order_id':'b','order_value_cents':2**63-1}]))


def test_latest_ineligible_order_does_not_change_rfm_or_last_state():
    rfm,_=build_rfm(rfm_orders([{}, {'order_id':'o2','eligible_sales':False,'eligible_rfm':False,
                                    'order_purchase_timestamp':'2018-08-02','customer_state':'RJ','order_value_cents':999}]))
    assert rfm.loc[0,'last_order_id']=='o1' and rfm.loc[0,'last_order_state']=='SP'
    assert rfm.loc[0,'frequency']==1 and rfm.loc[0,'monetary_cents']==100
