"""Kasus risiko P03: ekspektasi ditetapkan dari contoh kecil, bukan rumus kode."""
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from src.config import SOURCE_SCHEMAS
from src.data_pipeline import (
    DataQualityError, MoneyPrecisionError, clean_customers, clean_order_items,
    clean_orders, clean_products, clean_reviews, clean_translation,
)


def source(name, records):
    return pd.DataFrame([{**dict.fromkeys(SOURCE_SCHEMAS[name], pd.NA), **row}
                         for row in records], columns=SOURCE_SCHEMAS[name], dtype='string')


def order(**overrides):
    return dict(order_id='o1', customer_id='c1', order_status='delivered',
                order_purchase_timestamp='2018-01-01 09:00:00',
                order_approved_at='2018-01-01 10:00:00',
                order_delivered_carrier_date='2018-01-02 10:00:00',
                order_delivered_customer_date='2018-01-03 23:59:00',
                order_estimated_delivery_date='2018-01-03 00:00:00') | overrides


def orders(*records):
    return clean_orders(source('orders_dataset', records or [order()]))[0]


def review(**overrides):
    return dict(review_id='r1', order_id='o1', review_score='5',
                review_comment_title=pd.NA, review_comment_message=pd.NA,
                review_creation_date='2018-01-04 00:00:00',
                review_answer_timestamp='2018-01-05 10:00:00') | overrides


def item(**overrides):
    return dict(order_id='o1', order_item_id='1', product_id='p1', seller_id='s1',
                shipping_limit_date='2018-01-02 12:00:00', price='10.10', freight_value='0.00') | overrides


def test_same_estimated_calendar_day_is_on_time_and_early_delivery_is_zero():
    frame = orders(order(), order(order_id='o2', order_delivered_customer_date='2018-01-02 14:00:00'))
    assert frame['is_late'].tolist() == [False, False]
    assert frame['days_late'].tolist() == [0, 0]
    assert str(frame['is_late'].dtype) == 'boolean'
    assert str(frame['days_late'].dtype) == 'Int64'


def test_late_delivery_counts_calendar_days():
    frame = orders(order(order_delivered_customer_date='2018-01-05 00:01:00'))
    assert frame.loc[0, 'is_late']
    assert frame.loc[0, 'days_late'] == 2


@pytest.mark.parametrize('column', ['order_delivered_customer_date', 'order_estimated_delivery_date', 'order_purchase_timestamp'])
def test_missing_required_date_keeps_lateness_unknown(column):
    frame = orders(order(**{column: pd.NA}))
    assert pd.isna(frame.loc[0, 'is_late']) and pd.isna(frame.loc[0, 'days_late'])
    assert not frame.loc[0, 'delivery_dates_valid']


def test_parse_failure_differs_from_missing_date():
    frame, audit = clean_orders(source('orders_dataset', [order(order_delivered_customer_date='not-a-date')]))
    assert frame.loc[0, 'order_delivered_customer_date_parse_failed']
    assert not frame.loc[0, 'order_delivered_customer_date_missing']
    assert audit['dates']['order_delivered_customer_date']['parse_failures'] == 1
    assert pd.isna(frame.loc[0, 'is_late'])


def test_receipt_before_purchase_is_invalid_but_carrier_inversion_keeps_delivery_pair():
    frame = orders(
        order(order_delivered_customer_date='2017-12-31 12:00:00'),
        order(order_id='o2', order_delivered_carrier_date='2017-12-31 12:00:00'),
    )
    assert frame['has_lifecycle_chronology_issue'].tolist() == [True, True]
    assert pd.isna(frame.loc[0, 'is_late'])
    assert frame.loc[1, 'delivery_dates_valid'] and not frame.loc[1, 'is_late']


def test_estimate_before_purchase_is_flagged_and_not_treated_as_late():
    frame = orders(order(order_estimated_delivery_date='2017-12-31 00:00:00'))
    assert frame.loc[0, 'estimated_date_before_purchase']
    assert pd.isna(frame.loc[0, 'is_late'])


@pytest.mark.parametrize('invalid_score', ['2.5', '6', 'oops', pd.NA])
def test_latest_review_wins_even_when_score_invalid(invalid_score):
    raw = source('order_reviews_dataset', [review(), review(review_id='r2', review_creation_date='2018-01-06 00:00:00', review_score=invalid_score)])
    frame, audit = clean_reviews(raw, orders())
    assert len(frame) == 1 and frame.loc[0, 'review_id'] == 'r2'
    assert pd.isna(frame.loc[0, 'review_score']) and not frame.loc[0, 'review_score_valid']
    if pd.isna(invalid_score):
        assert pd.isna(frame.loc[0, 'review_score_raw'])
    else:
        assert frame.loc[0, 'review_score_raw'] == invalid_score
    assert frame.loc[0, 'review_selection_reason'] == 'latest_creation_date'
    assert audit['review_selection']['selected_invalid_scores'] == 1
    assert [r['selected'] for r in audit['selection_trace']] == [False, True]


@pytest.mark.parametrize('overrides', [
    {'review_answer_timestamp': '2018-01-06 10:00:00'},
    {'review_id': 'z'},
    {'review_score': '1'},
])
def test_review_ties_use_answer_then_lexical_id_then_source_row(overrides):
    raw = source('order_reviews_dataset', [review(), review(**overrides)])
    frame, _ = clean_reviews(raw, orders())
    assert frame.loc[0, 'source_row_number'] == 2
    expected = ('latest_answer_timestamp' if 'review_answer_timestamp' in overrides
                else 'lexical_review_id' if 'review_id' in overrides else 'source_row_number')
    assert frame.loc[0, 'review_selection_reason'] == expected


def test_valid_creation_beats_missing_and_null_answer_does_not_override_creation():
    raw = source('order_reviews_dataset', [
        review(review_id='z', review_creation_date=pd.NA, review_answer_timestamp='2018-02-01 00:00:00'),
        review(review_id='a', review_answer_timestamp=pd.NA),
    ])
    frame, _ = clean_reviews(raw, orders())
    assert frame.loc[0, 'review_id'] == 'a'


def test_repeated_review_id_on_different_orders_is_retained():
    raw = source('order_reviews_dataset', [review(), review(order_id='o2')])
    frame, _ = clean_reviews(raw, orders(order(), order(order_id='o2')))
    assert len(frame) == 2 and frame['review_id'].tolist() == ['r1', 'r1']
    assert frame['order_id'].is_unique


def test_review_metadata_anomaly_keeps_valid_score_and_optional_text_nullable():
    raw = source('order_reviews_dataset', [review(review_creation_date='2017-12-31 00:00:00', review_comment_title='  ')])
    frame, _ = clean_reviews(raw, orders())
    assert frame.loc[0, 'review_created_before_purchase']
    assert frame.loc[0, 'review_score'] == 5
    assert pd.isna(frame.loc[0, 'review_comment_title'])
    assert frame.loc[0, 'review_comment_title_raw'] == '  '


def test_exact_duplicate_rows_removed_before_required_key_check_without_mutation():
    raw = source('orders_dataset', [order(), order()])
    before = raw.copy(deep=True)
    frame, audit = clean_orders(raw)
    assert_frame_equal(raw, before)
    assert len(frame) == 1 and audit['exact_duplicate_rows_removed'] == 1
    assert audit['exact_duplicate_source_rows_removed'] == [2]


def test_conflicting_key_stops_join_instead_of_choosing_arbitrary_row():
    raw = source('orders_dataset', [order(), order(order_status='canceled')])
    with pytest.raises(DataQualityError, match='konflik kunci'):
        clean_orders(raw)


def test_missing_required_key_stops_join():
    with pytest.raises(DataQualityError, match='kunci kosong'):
        clean_orders(source('orders_dataset', [order(order_id=' ')]))


def test_money_uses_exact_cents_and_retains_zero_and_large_price():
    raw = source('order_items_dataset', [item(price='0.00'), item(order_item_id='2', price='6735.00'), item(order_item_id='3', price='1.230')])
    before = raw.copy(deep=True)
    frame, _ = clean_order_items(raw, orders())
    assert frame['price_cents'].tolist() == [0, 673500, 123]
    assert frame['freight_cents'].tolist() == [0, 0, 0]
    assert frame['price_valid'].all()
    assert_frame_equal(raw, before)


@pytest.mark.parametrize('price, reason', [('-1.00','negative'), ('bad','parse_failed'), ('NaN','nonfinite'), (pd.NA,'missing')])
def test_invalid_price_stays_nullable_with_reason(price, reason):
    frame, _ = clean_order_items(source('order_items_dataset', [item(price=price)]), orders())
    assert pd.isna(frame.loc[0, 'price_cents'])
    assert not frame.loc[0, 'price_valid'] and frame.loc[0, 'price_quality'] == reason


@pytest.mark.parametrize('price', ['1.234', '1.00000000000000000000000000001'])
def test_extra_money_precision_stops_before_rounding(price):
    with pytest.raises(MoneyPrecisionError) as exc:
        clean_order_items(source('order_items_dataset', [item(price=price)]), orders())
    assert exc.value.affected_count == 1 and exc.value.column == 'price'


def test_item_alias_collision_detected_after_numeric_validation():
    with pytest.raises(DataQualityError, match='bentrok'):
        clean_order_items(source('order_items_dataset', [item(), item(order_item_id='01')]), orders())


def test_missing_category_differs_from_untranslated_and_translated_categories():
    tr, _ = clean_translation(source('product_category_name_translation', [
        {'product_category_name':'known', 'product_category_name_english':'Known category'}]))
    raw = source('products_dataset', [
        {'product_id':'p1','product_category_name':'  '},
        {'product_id':'p2','product_category_name':'pc_gamer','product_weight_g':'0'},
        {'product_id':'p3','product_category_name':'known'},
    ])
    frame, _ = clean_products(raw, tr)
    assert frame['category_name'].tolist() == ['Tidak diketahui','pc_gamer','Known category']
    assert frame['category_missing'].tolist() == [True,False,False]
    assert frame['category_translation_missing'].tolist() == [False,True,False]
    assert pd.isna(frame.loc[0,'category_code'])
    assert frame.loc[1,'product_weight_zero'] and frame.loc[1,'product_weight_g'] == 0
    assert pd.isna(frame.loc[0,'product_weight_g'])


def test_customer_unique_id_missing_flag_preserves_customer_row_and_leading_zero():
    raw = source('customers_dataset', [{'customer_id':'0001','customer_unique_id':' ', 'customer_zip_code_prefix':'00123'}])
    frame, _ = clean_customers(raw)
    assert len(frame) == 1 and not frame.loc[0,'customer_unique_id_valid']
    assert frame.loc[0,'customer_id'] == '0001' and frame.loc[0,'customer_zip_code_prefix'] == '00123'


# P04: kasus kecil sengaja memisahkan cakupan sales, delivery, review, dan RFM.
from src.data_pipeline import aggregate_order_items, build_analysis_tables
from src.data_contracts import TABLE_CONTRACTS


def integration_sources(*, order_records=None, item_records=None, review_records=None,
                        customer_records=None, product_records=None, translation_records=None):
    o = orders(*(order_records if order_records is not None else [order()]))
    tr, _ = clean_translation(source('product_category_name_translation', translation_records if translation_records is not None else [
        {'product_category_name':'known','product_category_name_english':'Known category'}]))
    c, _ = clean_customers(source('customers_dataset', customer_records if customer_records is not None else [
        {'customer_id':'c1','customer_unique_id':'u1','customer_state':'SP'}]))
    p, _ = clean_products(source('products_dataset', product_records if product_records is not None else [
        {'product_id':'p1','product_category_name':'known'}]), tr)
    i, _ = clean_order_items(source('order_items_dataset', item_records if item_records is not None else [item()]), o)
    r, _ = clean_reviews(source('order_reviews_dataset', review_records if review_records is not None else [review()]), o)
    return {'orders_dataset':o, 'customers_dataset':c,'products_dataset':p,
            'order_items_dataset':i,'order_reviews_dataset':r,'product_category_name_translation':tr}


def test_multiple_items_and_reviews_do_not_multiply_order_value():
    cleaned = integration_sources(item_records=[item(price='10.10'),item(order_item_id='2',price='20.20')],
        review_records=[review(),review(review_id='latest',review_score='1',review_creation_date='2018-01-06 00:00:00')])
    original = {name:frame.copy(deep=True) for name,frame in cleaned.items()}
    tables, audit = build_analysis_tables(cleaned)
    o = tables['order_level']; i=tables['item_level']
    assert len(o)==1 and len(i)==2
    assert o.loc[0,'order_value_cents']==3030 and o.loc[0,'item_count']==2
    assert o.loc[0,'review_id']=='latest' and o.loc[0,'review_score']==1
    assert i['price_cents'].sum()==3030 and i['eligible_sales'].all()
    assert all(o.loc[0,c] for c in ('eligible_sales','eligible_delivery','eligible_review_comparison','eligible_rfm'))
    assert len(audit['joins'])==6 and all(j['left_rows_orders_and_money_preserved'] for j in audit['joins'])
    for name, frame in original.items():
        assert_frame_equal(cleaned[name],frame)


def test_no_items_keeps_null_value_and_independent_delivery_eligibility():
    tables, audit = build_analysis_tables(integration_sources(item_records=[]))
    o=tables['order_level'].iloc[0]
    assert o['item_count']==0 and pd.isna(o['order_value_cents'])
    assert not o['eligible_sales'] and not o['eligible_rfm']
    assert o['eligible_delivery'] and o['eligible_review_comparison']
    assert len(tables['item_level'])==0
    assert audit['coverage']['orders_without_items']==1


def test_invalid_price_drops_whole_order_from_sales_but_preserves_review_comparison():
    tables, audit = build_analysis_tables(integration_sources(item_records=[item(price='10.00'),item(order_item_id='2',price='bad')]))
    o=tables['order_level'].iloc[0]
    assert pd.isna(o['order_value_cents']) and o['item_count']==2
    assert o['valid_price_item_count']==1 and o['invalid_price_item_count']==1
    assert not o['eligible_sales'] and not tables['item_level']['eligible_sales'].any()
    assert o['eligible_delivery'] and o['eligible_review_comparison']
    assert audit['aggregation']['suppressed_known_price_cents_on_incomplete_orders']==1000


def test_invalid_freight_does_not_remove_valid_sales():
    tables,_=build_analysis_tables(integration_sources(item_records=[item(freight_value='bad')]))
    assert tables['order_level'].loc[0,'eligible_sales']
    assert pd.isna(tables['item_level'].loc[0,'freight_cents'])


def test_no_review_does_not_remove_sales_or_delivery():
    tables,_=build_analysis_tables(integration_sources(review_records=[]))
    o=tables['order_level'].iloc[0]
    assert o['eligible_sales'] and o['eligible_rfm'] and o['eligible_delivery']
    assert not o['eligible_review_comparison'] and not o['review_matched']
    assert pd.isna(o['review_score']) and not o['review_score_valid'] and o['review_candidate_count']==0


def test_missing_delivery_keeps_sales_but_null_lateness():
    tables,_=build_analysis_tables(integration_sources(order_records=[order(order_delivered_customer_date=pd.NA)]))
    o=tables['order_level'].iloc[0]
    assert o['eligible_sales'] and o['eligible_rfm'] and not o['eligible_delivery']
    assert not o['eligible_review_comparison'] and pd.isna(o['is_late']) and pd.isna(o['days_late'])


def test_unmatched_customer_only_excludes_rfm_and_retains_global_sales():
    tables,audit=build_analysis_tables(integration_sources(customer_records=[
        {'customer_id':'c9','customer_unique_id':'u9','customer_state':'RJ'}]))
    o=tables['order_level'].iloc[0]
    assert o['eligible_sales'] and o['eligible_delivery'] and o['eligible_review_comparison']
    assert not o['eligible_rfm'] and not o['customer_matched']
    assert pd.isna(o['customer_unique_id']) and pd.isna(o['customer_state'])
    assert audit['eligibility']['coverage_differences']['sales_without_rfm_identity']==1
    assert audit['eligibility']['coverage_differences']['sales_value_cents']==1010
    assert audit['eligibility']['coverage_differences']['rfm_value_cents']==0


def test_matched_customer_with_blank_unique_identity_stays_out_of_rfm():
    tables,_=build_analysis_tables(integration_sources(customer_records=[
        {'customer_id':'c1','customer_unique_id':' ','customer_state':'SP'}]))
    o=tables['order_level'].iloc[0]
    assert o['customer_matched'] and o['eligible_sales'] and not o['eligible_rfm']


def test_unmatched_product_keeps_sales_and_unknown_category_denominator():
    tables,audit=build_analysis_tables(integration_sources(item_records=[item(product_id='missing')]))
    i=tables['item_level'].iloc[0]
    assert i['eligible_sales'] and i['price_cents']==1010 and not i['product_matched']
    assert i['category_missing'] and i['category_name']=='Tidak diketahui'
    assert not i['category_translation_missing']
    assert audit['coverage']['items_without_product']==1


def test_join_distinguishes_unknown_and_untranslated_categories_without_losing_items():
    tables,_=build_analysis_tables(integration_sources(
        item_records=[item(),item(order_item_id='2',product_id='p2'),item(order_item_id='3',product_id='p3')],
        product_records=[{'product_id':'p1','product_category_name':'known'},
                         {'product_id':'p2','product_category_name':pd.NA},
                         {'product_id':'p3','product_category_name':'pc_gamer'}]))
    i=tables['item_level']
    assert i['category_name'].tolist()==['Known category','Tidak diketahui','pc_gamer']
    assert i['category_missing'].tolist()==[False,True,False]
    assert i['category_translation_missing'].tolist()==[False,False,True]
    assert len(i)==3 and i['price_cents'].sum()==3030


def test_orphan_item_is_retained_reported_and_excluded_from_sales():
    tables,audit=build_analysis_tables(integration_sources(item_records=[item(),item(order_id='orphan')]))
    i=tables['item_level'].set_index('order_id')
    assert len(i)==2 and not i.loc['orphan','order_matched'] and not i.loc['orphan','eligible_sales']
    assert not i.loc['orphan','in_analysis_period'] and pd.isna(i.loc['orphan','purchase_month'])
    assert audit['coverage']['items_without_order']==1
    j=next(j for j in audit['joins'] if j['join']=='orders_item_aggregate')
    assert j['unused_right_rows']==1 and j['unused_right_money']['order_value_cents']['known_total_cents']==1010
    assert audit['reconciliation']['eligible_item_price_cents']==1010


def test_unmatched_review_is_audited_without_creating_an_order():
    tables,audit=build_analysis_tables(integration_sources(review_records=[review(order_id='orphan')]))
    assert len(tables['order_level'])==1
    j=next(j for j in audit['joins'] if j['join']=='orders_selected_reviews')
    assert j['unused_right_rows']==1 and j['unmatched_left_rows']==1


@pytest.mark.parametrize('name', ['products_dataset','order_reviews_dataset','customers_dataset','product_category_name_translation'])
def test_duplicate_dimension_or_selected_review_blocks_join(name):
    cleaned=integration_sources()
    cleaned[name]=pd.concat([cleaned[name],cleaned[name]],ignore_index=True)
    with pytest.raises(DataQualityError,match='konflik kunci'):
        build_analysis_tables(cleaned)


def test_purchase_period_boundaries_use_shared_config():
    records=[order(order_id=f'o{n}',order_purchase_timestamp=timestamp,
                   order_delivered_customer_date='2018-09-05 12:00:00',order_estimated_delivery_date='2018-09-06 00:00:00')
             for n,timestamp in enumerate(['2016-12-31 23:59:59','2017-01-01 00:00:00','2018-08-31 23:59:59','2018-09-01 00:00:00'])]
    tables,_=build_analysis_tables(integration_sources(order_records=records,
        item_records=[item(order_id=o['order_id']) for o in records],review_records=[]))
    o=tables['order_level']
    assert o['in_analysis_period'].tolist()==[False,True,True,False]
    assert o['eligible_sales'].tolist()==[False,True,True,False]
    assert o['purchase_month'].tolist()==['2016-12','2017-01','2018-08','2018-09']
    assert o.loc[2,'purchase_date']==pd.Timestamp('2018-08-31')


def test_nondelivered_status_remains_in_output_and_is_not_eligible():
    tables,_=build_analysis_tables(integration_sources(order_records=[order(order_status='canceled')]))
    o=tables['order_level'].iloc[0]
    assert o['order_status']=='canceled' and o['order_value_cents']==1010
    assert all(not o[c] for c in ('eligible_sales','eligible_delivery','eligible_review_comparison','eligible_rfm'))


def test_output_contracts_cover_types_units_nulls_and_origins():
    tables,_=build_analysis_tables(integration_sources())
    for name, frame in tables.items():
        fields=TABLE_CONTRACTS[name]['fields']
        assert list(frame)==list(fields)
        for col,spec in fields.items():
            assert str(frame[col].dtype)==spec['dtype']
            assert spec['source'] and spec['unit'] and spec['null_meaning']
            if not spec['nullable']:
                assert frame[col].notna().all()


def test_aggregate_overflow_stops_before_silent_integer_wrap():
    items=pd.DataFrame({'order_id':['o1','o1'],'order_item_id':['1','2'],
                        'price_cents':pd.array([2**63-1,2**63-1],dtype='Int64'),
                        'price_valid':pd.array([True,True],dtype='boolean')})
    with pytest.raises(DataQualityError,match='Int64'):
        aggregate_order_items(items)
