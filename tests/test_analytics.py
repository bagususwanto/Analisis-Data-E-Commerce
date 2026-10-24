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
