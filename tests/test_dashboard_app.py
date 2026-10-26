"""Widget tests memeriksa hasil filter UI terhadap API analisis bersama."""
from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from src.analytics import analyze_q1, analyze_q2, analyze_q3, filter_rfm
from src.charts import brl, number
from src.dashboard_data import load_dashboard_data, baseline_analytics

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def bundle():
    return load_dashboard_data()


@pytest.fixture(scope='module')
def app():
    result = AppTest.from_file(str(ROOT/'dashboard/dashboard.py'), default_timeout=90).run()
    assert not result.exception
    return result


def metrics(app):
    assert not app.exception
    return {m.label: m.value for m in app.metric}


def test_default_matches_notebook(app, bundle):
    tables, metadata = bundle
    assert baseline_analytics(tables, metadata['rfm']) == metadata['baseline_analytics']
    m = metrics(app)
    assert m['Nilai barang'] == brl(metadata['baseline_analytics']['q1']['summary']['sales_value_cents'])
    assert m['Pesanan delivered'] == '96.211'
    assert m['Pelanggan'] == '93.104'
    assert [t.label for t in app.tabs] == ['Penjualan', 'Pengiriman & Ulasan', 'Pelanggan RFM']


def test_inclusive_single_day_and_state(app, bundle):
    tables, _ = bundle
    app.date_input[0].set_value((date(2018, 2, 1),)).run()
    app.multiselect[0].set_value(['SP']).run()
    q1 = analyze_q1(tables['item_level'], start='2018-02-01', end_exclusive='2018-02-02', states=['SP'])
    q2 = analyze_q2(tables['order_level'], start='2018-02-01', end_exclusive='2018-02-02', states=['SP'])
    m = metrics(app)
    assert m['Nilai barang'] == brl(q1['summary']['sales_value_cents'])
    assert m['Pengiriman dapat dievaluasi'] == number(q2['summary']['delivery_evaluable'])
    assert m['Pelanggan'] == '93.104'


def test_empty_transactions_do_not_filter_rfm(app):
    app.multiselect[0].set_value([]).run()
    m = metrics(app)
    assert m['Pesanan delivered'] == '0'
    assert m['Tingkat keterlambatan'] == 'Tidak tersedia'
    assert m['Pelanggan'] == '93.104'
    assert any('kedua kelompok' in i.value for i in app.info)


def test_small_state_and_fewer_categories(app):
    app.multiselect[0].set_value(['RR']).run()
    metrics(app)
    assert any('minimum 50' in i.value for i in app.info)


def test_rfm_region_segment_and_empty(app, bundle):
    tables, metadata = bundle
    region = app.multiselect[1]
    region.set_value(['RJ']).run()
    segment = 'Pelanggan berulang aktif'
    app.multiselect[2].set_value([segment]).run()
    selected = filter_rfm(tables['rfm_customers'], states=['RJ'])
    selected = selected.loc[selected['segment'].eq(segment)]
    q3 = analyze_q3(selected, metadata['rfm'])
    m = metrics(app)
    assert m['Pelanggan'] == number(q3['summary']['customer_count'])
    assert m['Monetary / nilai barang'] == brl(q3['summary']['monetary_cents'])
    app.multiselect[2].set_value([]).run()
    assert metrics(app)['Pelanggan'] == '0'
    assert any('Tidak ada pelanggan' in w.value for w in app.warning)


def test_missing_bundle_shows_repair():
    source = (ROOT/'dashboard/dashboard.py').read_text().replace(
        'ROOT = Path(__file__).resolve().parents[1]', f'ROOT = Path({str(ROOT)!r})')
    source = source.replace('return load_dashboard_data(DATA_DIR)', "raise DashboardDataError('Fixture: metadata hilang')")
    at = AppTest.from_string(source, default_timeout=90).run()
    assert not at.exception
    assert 'Data dashboard belum siap' in at.error[0].value
    assert 'python scripts/prepare_dashboard_data.py' in at.code[0].value
    assert not at.metric


def test_no_reviews_keeps_delivery_denominator():
    source = (ROOT/'dashboard/dashboard.py').read_text().replace(
        'ROOT = Path(__file__).resolve().parents[1]', f'ROOT = Path({str(ROOT)!r})')
    source = source.replace('return load_dashboard_data(DATA_DIR)',
        "tables, metadata = load_dashboard_data(ROOT/'dashboard')\n    tables['order_level']['eligible_review_comparison'] = False\n    return tables, metadata")
    at = AppTest.from_string(source, default_timeout=90).run()
    m = metrics(at)
    assert m['Pengiriman dapat dievaluasi'] == '96.203'
    assert m['Pesanan dengan ulasan pembanding'] == '0'
    assert m['Tingkat keterlambatan'] == '6,79%'
    assert any('Selisih ulasan buruk tidak tersedia' in i.value for i in at.info)
