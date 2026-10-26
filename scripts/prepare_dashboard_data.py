"""P08: satu perintah untuk sumber lokal -> CSV dashboard + metadata terverifikasi."""
from datetime import datetime
from importlib.metadata import version
import json
from pathlib import Path
import platform
import sys
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from pandas.testing import assert_frame_equal
from scripts.assess_data import verify_inputs
from src import config
from src.analytics import analyze_q1,analyze_q2,analyze_q3,build_rfm
from src.data_pipeline import build_analysis_tables
from src.dashboard_data import (
    EXPORT_COLUMNS,baseline_analytics,export_dashboard_data,jsonable,
    load_dashboard_data,project_tables,sha256_file,
)


def verify_dependencies():
    baseline=json.loads((ROOT/'reports/baseline.json').read_text())
    before=verify_inputs(baseline)
    analysis_path=ROOT/'reports/analytical_results.json'
    results=json.loads(analysis_path.read_text())
    proofs={name:json.loads((ROOT/f'reports/{name}.json').read_text())
            for name in ['rfm_validation','notebook_validation','integration_validation']}
    assert sha256_file(analysis_path)==proofs['rfm_validation']['analytical_results_sha256']
    assert sha256_file(ROOT/'reports/join_audit.json')==proofs['integration_validation']['join_audit_sha256']
    notebook=proofs['notebook_validation']
    assert notebook['execution_status']=='passed' and notebook['visual_review_status']=='passed' and notebook['gate']['passed']
    assert sha256_file(ROOT/'notebook.ipynb')==notebook['notebook_sha256']
    assert sha256_file(ROOT/'reports/notebook.html')==notebook['html_sha256']
    for figure in notebook['figures'].values():assert sha256_file(ROOT/figure['path'])==figure['sha256']
    assert before==results['source_sha256']==notebook['source_sha256']
    return baseline,results,before


def verify_analytics(actual,reference):
    for question,value in actual.items():
        for key,item in value.items():assert item==reference[question][key],f'{question}.{key} berbeda dari notebook/laporan'


def verify_filter_scenarios(tables,metadata,reference):
    checks={}
    for name,scenario in reference['filter_scenario_summaries'].items():
        f=scenario['filters']
        kwargs={'start':f['requested_start'],'end_exclusive':f['requested_end_exclusive'],'states':f['states']}
        q1=jsonable(analyze_q1(tables['item_level'],**kwargs));q2=jsonable(analyze_q2(tables['order_level'],**kwargs))
        assert q1['summary']==scenario['q1_summary'] and q2['summary']==scenario['q2_summary']
        checks['q1_q2_'+name]={'passed':True,'sales_orders':q1['summary']['order_count'],
                             'comparison_orders':q2['summary']['review_comparison_evaluable']}
    for name,scenario in reference['q3']['filter_scenario_summaries'].items():
        q3=jsonable(analyze_q3(tables['rfm_customers'],metadata['rfm'],states=scenario['filters']['states']))
        assert q3['summary']==scenario['summary']
        assert q3['high_value']==metadata['rfm']['high_value']
        checks['q3_'+name]={'passed':True,'customers':q3['summary']['customer_count']}
    return checks


def main():
    baseline,reference,before=verify_dependencies()
    tables,audit=build_analysis_tables()
    p4=json.loads((ROOT/'reports/join_audit.json').read_text())
    for key in ['aggregation','joins','eligibility','reconciliation','coverage','contracts','payments_policy']:
        assert audit[key]==p4[key],f'Dependency P04 berubah: {key}'
    tables['rfm_customers'],rfm_metadata=build_rfm(tables['order_level'])
    assert rfm_metadata==reference['q3']['rfm_metadata']
    projected=project_tables(tables)
    expected=baseline_analytics(projected,rfm_metadata)
    verify_analytics(expected,reference)
    references=['reports/data_quality.json','reports/join_audit.json','reports/analytical_results.json',
                'reports/rfm_validation.json','reports/notebook_validation.json','notebook.ipynb']
    provenance={
        'source_csvs':[{'path':entry['path'],'sha256':entry['sha256'],'size_bytes':entry['size_bytes'],
                       'row_count':entry['row_count'],'role':entry['role'],
                       'used_in_analysis':Path(entry['path']).stem in config.PRIMARY_SOURCES}
                      for entry in baseline['source_files']],
        'references':{name:sha256_file(ROOT/name) for name in references},
        'runtime':{'python':platform.python_version(),'pandas':version('pandas'),'numpy':version('numpy')},
        'pipeline':'src.data_pipeline.build_analysis_tables -> src.analytics.build_rfm -> project/CSV round-trip',
    }
    # Buat dua bundle penuh terpisah dari input sama dengan urutan baris diacak.
    # Keduanya harus byte-identik; waktu metadata dikecualikan dari bundle_id.
    with TemporaryDirectory(prefix='ecommerce-p08-repeat-') as temp:
        repeat=export_dashboard_data({name:frame.sample(frac=1,random_state=42) for name,frame in tables.items()},
            rfm_metadata,provenance=provenance,output_dir=Path(temp)/'bundle')
        metadata=export_dashboard_data(tables,rfm_metadata,provenance=provenance)
        assert metadata['bundle_id']==repeat['bundle_id']
        assert {k:v for k,v in metadata.items() if k!='generated_at'}=={k:v for k,v in repeat.items() if k!='generated_at'}
        for name in EXPORT_COLUMNS:
            assert sha256_file(ROOT/'dashboard'/f'{name}.csv')==sha256_file(Path(temp)/'bundle'/f'{name}.csv')
    restored,loaded=load_dashboard_data()
    for name,frame in projected.items():assert_frame_equal(frame,restored[name])
    verify_analytics(baseline_analytics(restored,loaded['rfm']),reference)
    rebuilt,rebuilt_meta=build_rfm(restored['order_level'])
    assert_frame_equal(rebuilt,restored['rfm_customers'])
    assert rebuilt_meta==loaded['rfm']
    scenarios=verify_filter_scenarios(restored,loaded,reference)
    order=restored['order_level'];item=restored['item_level'];rfm=restored['rfm_customers']
    unavailable=~order['delivery_dates_valid']
    assert order.loc[unavailable,'is_late'].isna().all() and order.loc[unavailable,'days_late'].isna().all()
    assert (order['is_late'].eq(False)&order['is_late'].notna()).any()
    sales=order.loc[order['eligible_sales']];sales_items=item.loc[item['eligible_sales']]
    order_value=sum(int(v) for v in sales['order_value_cents']);item_value=sum(int(v) for v in sales_items['price_cents'])
    assert order_value==item_value==reference['q1']['summary']['sales_value_cents']
    assert int(rfm['frequency'].sum())==int(order['eligible_rfm'].sum())
    assert sum(int(v) for v in rfm['monetary_cents'])==reference['q3']['summary']['monetary_cents']
    after=verify_inputs(baseline);assert before==after
    stamp=datetime.now(ZoneInfo('Asia/Jakarta')).isoformat(timespec='seconds')
    validation={
        'phase':'P08','status':'passed','verified_at':stamp,'command':'python scripts/prepare_dashboard_data.py',
        'runtime':{'python':platform.python_version(),'pandas':version('pandas'),'invocation_cwd':str(Path.cwd())},
        'bundle_id':metadata['bundle_id'],'metadata_sha256':sha256_file(ROOT/'dashboard/data_metadata.json'),
        'table_files':{name:{'sha256':spec['sha256'],'size_bytes':spec['size_bytes'],
                             'rows':spec['profile']['row_count'],'columns':len(spec['contract']['fields'])}
                       for name,spec in metadata['tables'].items()},
        'checks':{'second_export_byte_identical':True,'shuffled_input_rows_do_not_change_output':True,
                  'metadata_stable_except_generated_at':True,'all_round_trip_cells_and_dtypes_match':True,
                  'default_analytics_match_notebook_Q1_Q2_Q3':True,'rfm_rebuilt_from_exported_orders_matches':True,
                  'null_lateness_not_false':True,'nine_source_hashes_unchanged':True,'template_hash_unchanged':True},
        'reconciliation':{'eligible_sales_orders':len(sales),'eligible_sales_items':len(sales_items),
                          'order_value_cents':order_value,'item_price_cents':item_value,
                          'rfm_customers':len(rfm),'rfm_frequency_sum':int(rfm['frequency'].sum()),
                          'rfm_monetary_cents':sum(int(v) for v in rfm['monetary_cents'])},
        'filter_scenarios':scenarios,'source_sha256':after,
        'scope':'Ekspor dan pembacaan terverifikasi; aplikasi Streamlit P09 belum dibuat.'}
    (ROOT/'reports/export_validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print('PASS P08: 3 CSV + metadata, deterministic export, explicit dtype round-trip, 12 filter scenarios; source hashes unchanged.')
    print(json.dumps(validation['table_files'],ensure_ascii=False))
    print(json.dumps(validation['reconciliation'],ensure_ascii=False))


if __name__=='__main__':main()
