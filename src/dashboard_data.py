"""Bundle CSV dashboard P08: schema eksplisit, I/O deterministik, round-trip aman.

Reader hanya memerlukan tiga CSV + metadata dan kode src, tanpa data mentah,
notebook, laporan validasi, atau menjalankan pipeline.
"""
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from . import config
from .data_contracts import TABLE_CONTRACTS, RFM_CUSTOMER_CONTRACT

SCHEMA_VERSION=1
BUNDLE_FORMAT='ecommerce-dashboard-csv'
NULL_TOKEN='\\N'
DEFAULT_DATA_DIR=config.PROJECT_ROOT/'dashboard'
EXPORT_COLUMNS={
    'order_level':('order_id','customer_id','customer_unique_id','customer_state','order_status',
        'order_purchase_timestamp','purchase_date','purchase_month','order_value_cents','item_count',
        'has_items','items_value_complete','customer_identity_valid','review_score','review_score_valid',
        'review_matched','delivery_dates_valid','is_late','days_late','in_analysis_period',
        'eligible_sales','eligible_delivery','eligible_review_comparison','eligible_rfm'),
    'item_level':('order_id','order_item_id','product_id','category_code','category_name','category_missing',
        'category_translation_missing','price_cents','price_valid','order_status','order_purchase_timestamp',
        'purchase_date','purchase_month','customer_state','in_analysis_period','eligible_sales'),
    'rfm_customers':tuple(RFM_CUSTOMER_CONTRACT['fields']),
}
BASE_CONTRACTS={**TABLE_CONTRACTS,'rfm_customers':RFM_CUSTOMER_CONTRACT}
BOOLEAN_TOKENS={'true':True,'false':False,'True':True,'False':False}


class DashboardDataError(ValueError):
    """Error yang dapat ditampilkan aplikasi disertai langkah regenerasi."""
    def __init__(self,message):
        super().__init__(f'{message}. Regenerasi dari root proyek: python scripts/prepare_dashboard_data.py')


def jsonable(value):
    if isinstance(value,pd.DataFrame):return jsonable(value.to_dict('records'))
    if isinstance(value,dict):return {str(k):jsonable(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [jsonable(v) for v in value]
    if value is None or value is pd.NA:return None
    if isinstance(value,np.generic):return jsonable(value.item())
    if isinstance(value,float) and math.isnan(value):return None
    if isinstance(value,pd.Timestamp):return value.isoformat()
    return value


def sha256_file(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def parameters():
    return {'analysis_start':str(config.ANALYSIS_START),'analysis_end_exclusive':str(config.ANALYSIS_END_EXCLUSIVE),
        'rfm_reference_date':str(config.RFM_REFERENCE_DATE),'sales_order_status':config.SALES_ORDER_STATUS,
        'currency':config.CURRENCY,'money_scale':config.MONEY_SCALE,'minimum_state_sample':config.MIN_STATE_SAMPLE,
        'recency_new_days':config.RECENCY_NEW_DAYS,'recency_active_days':config.RECENCY_ACTIVE_DAYS,
        'rfm_segments':list(config.RFM_SEGMENTS),'high_value_quantile':config.HIGH_VALUE_QUANTILE,
        'high_value_interpolation':config.HIGH_VALUE_INTERPOLATION,'bad_review_scores':list(config.BAD_REVIEW_SCORES),
        'valid_review_scores':list(config.VALID_REVIEW_SCORES),'unknown_category_label':config.UNKNOWN_CATEGORY_LABEL}


def _directory(directory):
    path=DEFAULT_DATA_DIR if directory is None else Path(directory)
    return path if path.is_absolute() else config.PROJECT_ROOT/path


def _contract(name):
    if name not in EXPORT_COLUMNS:raise DashboardDataError(f'Tabel tidak dikenal: {name}')
    original=BASE_CONTRACTS[name]
    return {'grain':original['grain'],'primary_key':original['primary_key'],
            'fields':{c:original['fields'][c] for c in EXPORT_COLUMNS[name]}}


def _validate_frame(frame,name):
    contract=_contract(name)
    if list(frame)!=list(EXPORT_COLUMNS[name]):raise DashboardDataError(f'{name}: kolom atau urutan schema tidak cocok')
    for col,spec in contract['fields'].items():
        if str(frame[col].dtype)!=spec['dtype']:raise DashboardDataError(f'{name}.{col}: tipe harus {spec["dtype"]}')
        if not spec['nullable'] and frame[col].isna().any():raise DashboardDataError(f'{name}.{col}: null tidak diizinkan')
        if spec['dtype']=='string' and frame[col].eq(NULL_TOKEN).fillna(False).any():
            raise DashboardDataError(f'{name}.{col}: nilai teks berbenturan dengan token null')
    keys=contract['primary_key']
    if any((frame[k].isna()|frame[k].str.strip().eq('').fillna(False)).any() for k in keys):
        raise DashboardDataError(f'{name}: kunci kosong')
    if frame.duplicated(keys).any():raise DashboardDataError(f'{name}: kunci duplikat')
    if not frame.reset_index(drop=True).equals(frame.sort_values(keys,kind='stable').reset_index(drop=True)):
        raise DashboardDataError(f'{name}: urutan primary key tidak deterministik')


def project_tables(tables):
    result={}
    for name,columns in EXPORT_COLUMNS.items():
        if name not in tables or set(columns)-set(tables[name]):raise DashboardDataError(f'{name}: input/kolom ekspor belum lengkap')
        frame=tables[name][list(columns)].copy()
        frame=frame.sort_values(_contract(name)['primary_key'],kind='stable').reset_index(drop=True)
        _validate_frame(frame,name);result[name]=frame
    return result


def write_dashboard_csv(frame,name,path):
    """Null = literal \\N, boolean lower-case, timestamp ISO dengan presisi utuh."""
    _validate_frame(frame,name)
    encoded=frame.copy()
    for col,spec in _contract(name)['fields'].items():
        if spec['dtype']=='boolean':
            encoded[col]=frame[col].map({True:'true',False:'false'}).astype('string')
        elif spec['dtype'].startswith('datetime64'):
            encoded[col]=pd.array([pd.NA if pd.isna(v) else v.isoformat() for v in frame[col]],dtype='string')
    encoded.to_csv(path,index=False,encoding='utf-8',lineterminator='\n',na_rep=NULL_TOKEN)


def read_dashboard_csv(path,name):
    """Parsing string dahulu: tidak memakai inferensi ID/uang atau astype(bool)."""
    try:
        frame=pd.read_csv(path,dtype='string',encoding='utf-8',keep_default_na=False,na_values=[NULL_TOKEN])
    except (OSError,ValueError,pd.errors.ParserError) as exc:
        raise DashboardDataError(f'{name}: CSV tidak dapat dibaca ({exc})') from exc
    if list(frame)!=list(EXPORT_COLUMNS.get(name,())):raise DashboardDataError(f'{name}: header CSV tidak cocok')
    for col,spec in _contract(name)['fields'].items():
        raw=frame[col];nonnull=raw.dropna();dtype=spec['dtype']
        try:
            if dtype=='boolean':
                if not nonnull.isin(BOOLEAN_TOKENS).all():raise ValueError('token boolean harus true/false (atau True/False)')
                frame[col]=raw.map(BOOLEAN_TOKENS).astype('boolean')
            elif dtype=='Int64':
                if not nonnull.str.fullmatch(r'[+-]?\d+').all():raise ValueError('integer tidak boleh berbentuk float/desimal')
                integers=[pd.NA if pd.isna(v) else int(v) for v in raw]
                if any(not -(2**63)<=v<=2**63-1 for v in integers if v is not pd.NA):
                    raise OverflowError('nilai melampaui batas Int64')
                frame[col]=pd.array(integers,dtype='Int64')
            elif dtype.startswith('datetime64'):
                if not nonnull.str.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?').all():
                    raise ValueError('timestamp harus ISO tanpa timezone')
                frame[col]=pd.to_datetime(raw,format='ISO8601',errors='raise').astype(dtype)
            else:frame[col]=raw.astype(dtype)
        except (ValueError,TypeError,OverflowError) as exc:
            raise DashboardDataError(f'{name}.{col}: gagal parsing {dtype} ({exc})') from exc
    _validate_frame(frame,name)
    return frame


def _profile(frame):
    return {'row_count':len(frame),'null_counts':{c:int(frame[c].isna().sum()) for c in frame},
            'money_totals_cents':{c:sum(int(v) for v in frame[c].dropna()) for c in frame if c.endswith('_cents')},
            'eligibility_counts':{c:int(frame[c].sum()) for c in frame if c.startswith('eligible_')},
            'date_ranges':{c:{'min':frame[c].min().isoformat() if frame[c].notna().any() else None,
                              'max':frame[c].max().isoformat() if frame[c].notna().any() else None}
                           for c in frame if str(frame[c].dtype).startswith('datetime64')}}


def bundle_id(metadata):
    stable={k:v for k,v in metadata.items() if k not in ('generated_at','bundle_id')}
    return hashlib.sha256(json.dumps(stable,ensure_ascii=False,sort_keys=True,allow_nan=False).encode()).hexdigest()


def baseline_analytics(tables,rfm_metadata):
    from .analytics import analyze_q1,analyze_q2,analyze_q3
    return jsonable({'q1':analyze_q1(tables['item_level']),'q2':analyze_q2(tables['order_level']),
                     'q3':analyze_q3(tables['rfm_customers'],rfm_metadata)})


def _validate_metadata(metadata):
    if type(metadata.get('schema_version')) is not int or metadata['schema_version']!=SCHEMA_VERSION or metadata.get('bundle_format')!=BUNDLE_FORMAT:
        raise DashboardDataError('Versi/schema metadata tidak didukung')
    if metadata.get('parameters')!=parameters():raise DashboardDataError('Parameter metadata tidak cocok dengan konfigurasi kode')
    if metadata.get('bundle_id')!=bundle_id(metadata):raise DashboardDataError('Digest metadata tidak cocok')
    if set(metadata.get('tables',{}))!=set(EXPORT_COLUMNS):raise DashboardDataError('Daftar tabel metadata tidak lengkap')
    if metadata.get('csv_format')!={'encoding':'utf-8','null_token':NULL_TOKEN,'boolean_emit':['true','false'],
        'boolean_accept':list(BOOLEAN_TOKENS),'timestamp':'ISO 8601, timezone-naive; preserve up to nanoseconds',
        'line_terminator':'LF','id_sort':'lexicographic, preserve original spelling'}:
        raise DashboardDataError('Format CSV metadata tidak cocok')
    sources=metadata.get('provenance',{}).get('source_csvs',[])
    used={Path(s.get('path','')).stem for s in sources if s.get('used_in_analysis')}
    if used!=set(config.PRIMARY_SOURCES):raise DashboardDataError('Provenance enam sumber utama tidak lengkap')
    if any(not re.fullmatch('[0-9a-f]{64}',s.get('sha256','')) for s in sources):raise DashboardDataError('SHA-256 sumber tidak valid')
    for name,spec in metadata['tables'].items():
        if spec.get('filename')!=name+'.csv' or spec.get('contract')!=_contract(name):
            raise DashboardDataError(f'{name}: kontrak/file metadata tidak cocok')
        if spec.get('sort_by')!=_contract(name)['primary_key']:raise DashboardDataError(f'{name}: urutan metadata tidak cocok')


def _validate_rfm(tables,metadata):
    from .analytics import _high_value_flags
    rfm=tables['rfm_customers'];rfm_meta=metadata['rfm']
    expected_period={'start_inclusive':str(config.ANALYSIS_START),'end_exclusive':str(config.ANALYSIS_END_EXCLUSIVE)}
    expected_rules={'new_days_inclusive':config.RECENCY_NEW_DAYS,'active_days_inclusive':config.RECENCY_ACTIVE_DAYS,
                    'labels':list(config.RFM_SEGMENTS)}
    if rfm_meta['analysis_period']!=expected_period or rfm_meta['segment_rules']!=expected_rules:
        raise DashboardDataError('Periode/aturan segmen RFM metadata tidak cocok')
    if rfm_meta['reference_date']!=str(config.RFM_REFERENCE_DATE) or rfm_meta['high_value']['population_customer_count']!=len(rfm):
        raise DashboardDataError('Populasi/acuan RFM metadata tidak cocok')
    if rfm_meta['high_value']['quantile']!=config.HIGH_VALUE_QUANTILE or rfm_meta['high_value']['interpolation']!=config.HIGH_VALUE_INTERPOLATION:
        raise DashboardDataError('Aturan ambang monetary tidak cocok')
    exact=rfm_meta['high_value']['threshold_cents_exact']
    if len(rfm):
        if not isinstance(exact,dict) or type(exact.get('numerator')) is not int or type(exact.get('denominator')) is not int or exact['denominator']<=0 or exact['numerator']<0:
            raise DashboardDataError('Rasio cutoff monetary tidak valid')
    elif exact is not None:raise DashboardDataError('Populasi RFM kosong harus memiliki cutoff unavailable')
    if not rfm['is_high_value'].equals(_high_value_flags(rfm['monetary_cents'],rfm_meta['high_value'])):
        raise DashboardDataError('Label nilai tinggi tidak cocok dengan cutoff global')
    if int(rfm['is_high_value'].sum())!=rfm_meta['high_value']['high_value_customers']:
        raise DashboardDataError('Jumlah label nilai tinggi metadata tidak cocok')
    if rfm['recency_days'].lt(0).any() or rfm['frequency'].lt(1).any() or not rfm['segment'].isin(config.RFM_SEGMENTS).all():
        raise DashboardDataError('Dimensi/segmen RFM melanggar domain')
    expected=rfm_meta['reconciliation']
    if int(rfm['frequency'].sum())!=expected['rfm_frequency_sum'] or sum(int(v) for v in rfm['monetary_cents'])!=expected['rfm_monetary_sum_cents']:
        raise DashboardDataError('Rekonsiliasi RFM metadata tidak cocok')


def load_dashboard_data(data_dir=None):
    """Baca hanya bundle; fail closed pada schema/hash/tipe/parameter yang usang."""
    directory=_directory(data_dir)
    try:metadata=json.loads((directory/'data_metadata.json').read_text(encoding='utf-8'))
    except (OSError,ValueError) as exc:raise DashboardDataError(f'Metadata dashboard tidak dapat dibaca ({exc})') from exc
    if not isinstance(metadata,dict):raise DashboardDataError('Metadata harus berupa object JSON')
    try:
        _validate_metadata(metadata)
        tables={}
        for name,spec in metadata['tables'].items():
            path=directory/spec['filename']
            if not path.is_file() or sha256_file(path)!=spec['sha256'] or path.stat().st_size!=spec['size_bytes']:
                raise DashboardDataError(f'{name}: CSV hilang atau checksum/ukuran tidak cocok')
            frame=read_dashboard_csv(path,name)
            if _profile(frame)!=spec['profile']:raise DashboardDataError(f'{name}: profil baris/null/uang/coverage tidak cocok')
            tables[name]=frame
        _validate_rfm(tables,metadata)
    except DashboardDataError:raise
    except (KeyError,TypeError,ValueError,OverflowError,AttributeError,OSError) as exc:raise DashboardDataError(f'Metadata/isi bundle tidak lengkap atau tidak valid ({exc})') from exc
    return tables,metadata


def export_dashboard_data(tables,rfm_metadata,*,provenance,output_dir=None):
    """Stage -> round-trip -> publikasi CSV; metadata diganti terakhir.

    Pembaca selama pergantian menolak bundle campuran lewat checksum. File lain
    dalam dashboard/ (mis. dashboard.py pada P09) tidak dihapus/ditimpa.
    """
    directory=_directory(output_dir);directory.parent.mkdir(parents=True,exist_ok=True)
    projected=project_tables(tables)
    analytics=baseline_analytics(projected,rfm_metadata)
    with TemporaryDirectory(prefix='.ecommerce-export-',dir=directory.parent) as temp:
        stage=Path(temp);descriptions={}
        for name,frame in projected.items():
            path=stage/(name+'.csv');write_dashboard_csv(frame,name,path)
            descriptions[name]={'filename':path.name,'sha256':sha256_file(path),'size_bytes':path.stat().st_size,
                                'sort_by':_contract(name)['primary_key'],'contract':_contract(name),'profile':_profile(frame)}
        metadata={'schema_version':SCHEMA_VERSION,'bundle_format':BUNDLE_FORMAT,
            'generated_at':datetime.now(ZoneInfo('Asia/Jakarta')).isoformat(timespec='seconds'),
            'generator':'scripts/prepare_dashboard_data.py','parameters':parameters(),'provenance':jsonable(provenance),
            'csv_format':{'encoding':'utf-8','null_token':NULL_TOKEN,'boolean_emit':['true','false'],
                'boolean_accept':list(BOOLEAN_TOKENS),'timestamp':'ISO 8601, timezone-naive; preserve up to nanoseconds',
                'line_terminator':'LF','id_sort':'lexicographic, preserve original spelling'},
            'tables':descriptions,'rfm':jsonable(rfm_metadata),'baseline_analytics':analytics,
            'projection':{name:{'exported_columns':list(EXPORT_COLUMNS[name]),
                                'omitted_columns':sorted(set(tables[name])-set(EXPORT_COLUMNS[name]))} for name in projected},
            'notes':['Judul/pesan review dan kolom audit yang tidak dipakai Q1–Q3 tidak diekspor.',
                     'Null adalah literal backslash-N; empty string dan NA literal dipertahankan sebagai teks.',
                     'Null/False/0 berbeda. Timestamp dan ID tidak memakai inferensi otomatis.',
                     'Cutoff RFM global tidak dihitung ulang saat membaca atau memfilter dashboard.']}
        metadata['bundle_id']=bundle_id(metadata)
        (stage/'data_metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        restored,decoded=load_dashboard_data(stage)
        for name,frame in projected.items():assert_frame_equal(frame,restored[name])
        if baseline_analytics(restored,decoded['rfm'])!=analytics:raise DashboardDataError('Agregasi berubah setelah round-trip CSV')
        directory.mkdir(parents=True,exist_ok=True)
        for name in EXPORT_COLUMNS:os.replace(stage/(name+'.csv'),directory/(name+'.csv'))
        os.replace(stage/'data_metadata.json',directory/'data_metadata.json')
    return metadata
