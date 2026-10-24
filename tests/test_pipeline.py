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
