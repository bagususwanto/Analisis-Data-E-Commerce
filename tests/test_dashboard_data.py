"""P08: risiko serialisasi, metadata usang, dan bundle mandiri."""
import csv
import hashlib
import json

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from src import config
from src.analytics import build_rfm
from src.data_pipeline import build_analysis_tables
from src.dashboard_data import (
    DashboardDataError, NULL_TOKEN, EXPORT_COLUMNS, baseline_analytics, bundle_id,
    export_dashboard_data, load_dashboard_data, project_tables, read_dashboard_csv,
    write_dashboard_csv,
)
from test_pipeline import integration_sources,order,item,review


def bundle_tables():
    cleaned=integration_sources(
        order_records=[order(order_id='0001',customer_id='c1'),
                       order(order_id='0002',customer_id='c2',order_delivered_customer_date=pd.NA)],
        item_records=[item(order_id='0001',price='10.10'),item(order_id='0002',price='20.20')],
        review_records=[review(order_id='0001',review_score='5')],
        customer_records=[{'customer_id':'c1','customer_unique_id':'000001','customer_state':'NA'},
                          {'customer_id':'c2','customer_unique_id':'000002','customer_state':'SP'}])
    tables,_=build_analysis_tables(cleaned)
    tables['rfm_customers'],meta=build_rfm(tables['order_level'])
    return tables,meta


def provenance():
    return {'purpose':'synthetic fixture', 'source_csvs':[
        {'path':f'data/{name}.csv','sha256':hashlib.sha256(name.encode()).hexdigest(),
         'used_in_analysis':name in config.PRIMARY_SOURCES}
        for name in config.SOURCE_SCHEMAS]}


def write_bundle(tmp_path):
    tables,meta=bundle_tables();directory=tmp_path/'bundle'
    exported=export_dashboard_data(tables,meta,provenance=provenance(),output_dir=directory)
    return tables,meta,directory,exported


def rewrite_csv(path,change):
    with path.open(newline='') as stream:
        reader=csv.DictReader(stream);names=reader.fieldnames;rows=list(reader)
    change(rows)
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=names,lineterminator='\n');writer.writeheader();writer.writerows(rows)


def test_round_trip_preserves_leading_zero_ids_literal_NA_false_null_integer_and_money(tmp_path):
    original,rfm_meta,directory,meta=write_bundle(tmp_path)
    restored,loaded=load_dashboard_data(directory)
    for name,frame in project_tables(original).items():assert_frame_equal(frame,restored[name])
    o=restored['order_level']
    assert o.loc[0,'order_id']=='0001' and o.loc[0,'customer_unique_id']=='000001'
    assert o.loc[0,'customer_state']=='NA'
    assert o.loc[0,'is_late']==False and not pd.isna(o.loc[0,'is_late'])
    assert pd.isna(o.loc[1,'is_late']) and pd.isna(o.loc[1,'review_score'])
    assert o.loc[0,'days_late']==0 and pd.isna(o.loc[1,'days_late'])
    assert str(o['order_value_cents'].dtype)=='Int64' and str(o['review_score'].dtype)=='Int64'
    assert baseline_analytics(restored,loaded['rfm'])==meta['baseline_analytics']
    assert NULL_TOKEN in (directory/'order_level.csv').read_text()


def test_capital_False_token_is_parsed_false_not_truthy(tmp_path):
    tables,_,directory,_=write_bundle(tmp_path)
    path=directory/'order_level.csv'
    rewrite_csv(path,lambda rows:rows[0].update(is_late='False'))
    frame=read_dashboard_csv(path,'order_level')
    assert frame.loc[0,'is_late']==False and pd.isna(frame.loc[1,'is_late'])


@pytest.mark.parametrize('token',['0','yes','FALSE-ish'])
def test_invalid_boolean_is_rejected_instead_of_coerced(tmp_path,token):
    _,_,directory,_=write_bundle(tmp_path);path=directory/'order_level.csv'
    rewrite_csv(path,lambda rows:rows[0].update(is_late=token))
    with pytest.raises(DashboardDataError,match='boolean'):read_dashboard_csv(path,'order_level')


def test_large_integer_cents_and_nanosecond_timestamp_do_not_pass_through_float(tmp_path):
    tables,_=bundle_tables();frame=project_tables(tables)['order_level']
    frame.loc[0,'order_value_cents']=2**53+1
    frame.loc[0,'order_purchase_timestamp']=pd.Timestamp('2018-01-01T09:00:00.123456789')
    path=tmp_path/'orders.csv';write_dashboard_csv(frame,'order_level',path)
    restored=read_dashboard_csv(path,'order_level')
    assert restored.loc[0,'order_value_cents']==2**53+1
    assert restored.loc[0,'order_purchase_timestamp']==pd.Timestamp('2018-01-01T09:00:00.123456789')


def test_empty_string_and_NULL_token_have_distinct_meanings(tmp_path):
    tables,_=bundle_tables();frame=project_tables(tables)['order_level']
    frame.loc[0,'customer_state']='';frame.loc[1,'customer_state']=pd.NA
    path=tmp_path/'orders.csv';write_dashboard_csv(frame,'order_level',path)
    restored=read_dashboard_csv(path,'order_level')
    assert restored.loc[0,'customer_state']=='' and pd.isna(restored.loc[1,'customer_state'])
    frame.loc[0,'customer_state']=NULL_TOKEN
    with pytest.raises(DashboardDataError,match='token null'):write_dashboard_csv(frame,'order_level',path)


@pytest.mark.parametrize('token',['1.00','9007199254740993.0','9223372036854775808','-9223372036854775809'])
def test_float_like_or_overflow_integer_is_rejected(tmp_path,token):
    _,_,directory,_=write_bundle(tmp_path);path=directory/'order_level.csv'
    rewrite_csv(path,lambda rows:rows[0].update(order_value_cents=token))
    with pytest.raises(DashboardDataError,match='Int64'):read_dashboard_csv(path,'order_level')


@pytest.mark.parametrize('token',['2018-01-01','2018-01-01T09:00:00+02:00','2018-02-30T09:00:00'])
def test_invalid_or_ambiguous_timestamp_is_rejected(tmp_path,token):
    _,_,directory,_=write_bundle(tmp_path);path=directory/'order_level.csv'
    rewrite_csv(path,lambda rows:rows[0].update(order_purchase_timestamp=token))
    with pytest.raises(DashboardDataError,match='datetime'):read_dashboard_csv(path,'order_level')


def test_second_export_is_byte_stable_and_preserves_unrelated_app_file(tmp_path):
    tables,meta,directory,first=write_bundle(tmp_path)
    snapshot={name:(directory/(name+'.csv')).read_bytes() for name in EXPORT_COLUMNS}
    original={name:frame.copy(deep=True) for name,frame in tables.items()}
    marker=directory/'dashboard.py';marker.write_text('# user app\n')
    shuffled={name:frame.iloc[::-1] for name,frame in tables.items()}
    second=export_dashboard_data(shuffled,meta,provenance=provenance(),output_dir=directory)
    assert first['bundle_id']==second['bundle_id']
    assert {k:v for k,v in first.items() if k!='generated_at'}=={k:v for k,v in second.items() if k!='generated_at'}
    assert all(snapshot[name]==(directory/(name+'.csv')).read_bytes() for name in EXPORT_COLUMNS)
    assert marker.read_text()=='# user app\n'
    for name,frame in original.items():assert_frame_equal(frame,tables[name])


def test_unused_review_text_and_audit_columns_are_not_exported(tmp_path):
    tables,meta=bundle_tables();tables['order_level']['review_comment_message']='private review text'
    directory=tmp_path/'bundle';export_dashboard_data(tables,meta,provenance=provenance(),output_dir=directory)
    loaded,_=load_dashboard_data(directory)
    assert 'review_comment_message' not in loaded['order_level']
    assert 'private review text' not in (directory/'order_level.csv').read_text()
    assert 'order_approved_at' not in loaded['order_level'] and 'seller_id' not in loaded['item_level']


@pytest.mark.parametrize('kind',['version','parameters','rfm_period','checksum','metadata_digest','not_an_object','missing_csv','missing_metadata'])
def test_bad_bundle_fails_with_regeneration_instruction(tmp_path,kind):
    _,_,directory,metadata=write_bundle(tmp_path);mp=directory/'data_metadata.json'
    if kind=='version':metadata['schema_version']=99;metadata['bundle_id']=bundle_id(metadata)
    elif kind=='parameters':metadata['parameters']['currency']='USD';metadata['bundle_id']=bundle_id(metadata)
    elif kind=='rfm_period':
        metadata['rfm']['analysis_period']['start_inclusive']='2016-01-01'
        metadata['bundle_id']=bundle_id(metadata)
    elif kind=='checksum':
        with (directory/'item_level.csv').open('a') as stream:stream.write('\n')
    elif kind=='metadata_digest':metadata['notes'].append('changed')
    elif kind=='not_an_object':metadata=[]
    elif kind=='missing_csv':(directory/'order_level.csv').unlink()
    elif kind=='missing_metadata':mp.unlink()
    if kind not in ('missing_metadata','checksum','missing_csv'):mp.write_text(json.dumps(metadata))
    with pytest.raises(DashboardDataError,match='prepare_dashboard_data.py'):load_dashboard_data(directory)


def test_reader_bundle_does_not_require_source_csv_or_reports(tmp_path,monkeypatch):
    _,_,directory,_=write_bundle(tmp_path)
    # Pembaca menunjuk hanya ke bundle, bukan project root data/ atau laporan.
    monkeypatch.setattr(config,'PROJECT_ROOT',tmp_path/'no_source_project')
    loaded,_=load_dashboard_data(directory)
    assert len(loaded['order_level'])==2 and len(loaded['rfm_customers'])==2


def test_header_only_empty_bundle_retains_all_declared_dtypes(tmp_path):
    tables,_=bundle_tables()
    empty={name:frame.iloc[:0].copy() for name,frame in tables.items()}
    empty['rfm_customers'],meta=build_rfm(empty['order_level'])
    directory=tmp_path/'empty_bundle'
    export_dashboard_data(empty,meta,provenance=provenance(),output_dir=directory)
    restored,metadata=load_dashboard_data(directory)
    for name,frame in project_tables(empty).items():assert_frame_equal(frame,restored[name])
    assert metadata['baseline_analytics']['q1']['summary']['top_five_contribution_pct'] is None
    assert metadata['baseline_analytics']['q3']['summary']['repeat_customer_pct'] is None


def test_file_read_error_is_wrapped_with_repair_instruction(tmp_path,monkeypatch):
    import src.dashboard_data as data
    _,_,directory,_=write_bundle(tmp_path)
    def fail_read(path):raise OSError('simulated unreadable CSV')
    monkeypatch.setattr(data,'sha256_file',fail_read)
    with pytest.raises(DashboardDataError,match='prepare_dashboard_data.py'):load_dashboard_data(directory)
