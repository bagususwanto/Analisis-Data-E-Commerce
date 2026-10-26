"""P10: sumber -> tabel -> notebook -> bundle -> UI; exit 1 jika ada drift.

Tidak meregenerasi keluaran. Jalankan setelah ekspor/eksekusi notebook untuk
mendeteksi hasil lama. Semua tahap gagal dicatat pada validation_results.json.
"""
from datetime import datetime
from importlib.metadata import distributions, version
import json
from pathlib import Path
import platform
import sys
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import nbformat
import matplotlib
matplotlib.use('Agg')
from pandas.testing import assert_frame_equal, assert_series_equal
from src.analytics import analyze_q1, analyze_q2, analyze_q3, build_rfm
from src.charts import brl, number
from src.dashboard_data import baseline_analytics, jsonable, load_dashboard_data, project_tables, sha256_file
from src.data_pipeline import build_analysis_tables


class ValidationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def verify_sources(root=ROOT):
    baseline = read_json(root/'reports/baseline.json')
    entries = [*baseline['source_files'], baseline['template']]
    for entry in entries:
        path = root/entry['path']
        require(path.is_file(), f"File sumber hilang: {entry['path']}")
        require(sha256_file(path) == entry['sha256'], f"Sumber berubah: {entry['path']}")
    return {entry['path']: entry['sha256'] for entry in entries}


def verify_provenance(metadata, root=ROOT):
    for path, digest in metadata['provenance']['references'].items():
        require(sha256_file(root/path) == digest, f'Provenance usang: {path}; regenerasi ekspor setelah notebook selesai ditinjau')
    for entry in metadata['provenance']['source_csvs']:
        require(sha256_file(root/entry['path']) == entry['sha256'], f"Provenance sumber berbeda: {entry['path']}")
    return {'references_checked': len(metadata['provenance']['references']), 'source_csvs_checked': 9}


def notebook_results(path):
    nb = nbformat.read(path, as_version=4)
    nbformat.validate(nb)
    code = [cell for cell in nb.cells if cell.cell_type == 'code']
    require(bool(code), 'Notebook tidak memiliki code cell')
    require([cell.execution_count for cell in code] == list(range(1, len(code)+1)), 'Notebook belum dieksekusi berurutan dari kernel bersih')
    require(not any(output.output_type == 'error' for cell in code for output in cell.outputs), 'Notebook memiliki output error')
    snapshots = [output['data']['application/json'] for cell in code for output in cell.outputs
        if output.output_type in ('display_data', 'execute_result')
        and isinstance(output.get('data', {}).get('application/json'), dict)
        and output['data']['application/json'].get('artifact') == 'ecommerce.analytics.v1']
    require(len(snapshots) == 1, 'Notebook harus memiliki tepat satu payload hasil Q1–Q3 aktual; jalankan ulang notebook')
    require(set(snapshots[0].get('results', {})) == {'q1', 'q2', 'q3'}, 'Payload notebook tidak lengkap')
    return snapshots[0]['results']


def expected_metrics(results):
    q1, q2, q3 = [results[q]['summary'] for q in ['q1', 'q2', 'q3']]
    return {'Nilai barang': brl(q1['sales_value_cents']), 'Pesanan delivered': number(q1['order_count']),
        'Item terjual': number(q1['item_count']), 'Tingkat keterlambatan': number(q2['late_rate_pct'], 2)+'%',
        'Pengiriman dapat dievaluasi': number(q2['delivery_evaluable']),
        'Pesanan dengan ulasan pembanding': number(q2['review_comparison_evaluable']),
        'Pelanggan': number(q3['customer_count']), 'Monetary / nilai barang': brl(q3['monetary_cents']),
        'Pelanggan berulang': number(q3['repeat_customer_pct'], 2)+'%'}


def verify_ui(results):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT/'dashboard/dashboard.py'), default_timeout=90).run()
    require(not at.exception, 'Dashboard menghasilkan exception: '+str([e.message for e in at.exception]))
    metrics = {m.label: m.value for m in at.metric}
    require(metrics == expected_metrics(results), 'KPI dashboard default berbeda dari hasil notebook/CSV')
    require([t.label for t in at.tabs] == ['Penjualan', 'Pengiriman & Ulasan', 'Pelanggan RFM'], 'Tab dashboard tidak lengkap')
    frames = [element.value for element in at.dataframe]
    def compare(question, key, names):
        matches = [df for df in frames if set(names.values()).issubset(df.columns)]
        require(len(matches) == 1, f'Tabel UI {question}.{key} tidak ditemukan atau ambigu')
        import pandas as pd
        expected = pd.DataFrame(results[question][key])
        actual = matches[0].reset_index(drop=True)
        for source, label in names.items():
            values = expected[source]
            if source.endswith('_cents'):
                values = values.astype('Float64') / 100
            assert_series_equal(actual[label], values, check_names=False, check_dtype=False)
    compare('q1', 'categories', {'category_code':'Kode kategori', 'sales_value_cents':'Nilai barang (BRL)',
        'item_count':'Item', 'order_count':'Pesanan', 'contribution_pct':'Kontribusi (%)'})
    compare('q2', 'comparison_groups', {'delivery_group':'Ketepatan pengiriman', 'review_order_count':'Sampel ulasan',
        'bad_review_count':'Ulasan buruk', 'bad_review_rate_pct':'Ulasan buruk (%)'})
    compare('q3', 'segments', {'segment':'Segmen', 'customer_count':'Pelanggan', 'monetary_cents':'Monetary (BRL)',
        'customer_contribution_pct':'Kontribusi pelanggan (%)', 'monetary_contribution_pct':'Kontribusi monetary (%)'})
    return {'metrics': metrics, 'category_rows':len(results['q1']['categories']),
            'review_group_rows':2, 'segment_rows':5, 'exceptions':0}


def main():
    checks = {}; context = {}
    def check(name, task):
        start = time.monotonic()
        try:
            detail = task()
            checks[name] = {'passed':True, 'detail':jsonable(detail)}
        except Exception as exc:
            checks[name] = {'passed':False, 'error':f'{type(exc).__name__}: {exc}'}
        checks[name]['elapsed_seconds'] = round(time.monotonic()-start, 3)
        print(('PASS ' if checks[name]['passed'] else 'FAIL ')+name, flush=True)
    def inputs():
        require(__debug__, 'Jangan gunakan python -O: pemeriksaan referensi memerlukan assert aktif')
        context['sources'] = verify_sources()
        return context['sources']
    def runtime():
        expected_python = (ROOT/'.python-version').read_text().strip()
        require(platform.python_version() == expected_python, 'Versi Python berbeda dari .python-version')
        require(sys.prefix != sys.base_prefix, 'Gunakan virtual environment proyek')
        pins = {}
        for name in ['requirements.txt', 'requirements-dev.txt']:
            for line in (ROOT/name).read_text().splitlines():
                line = line.strip()
                if not line or line.startswith(('#', '-r ')):
                    continue
                package, pinned = line.split('==')
                require(version(package) == pinned, f'Versi {package} berbeda dari {name}')
                pins[package] = pinned
        return {'python':expected_python, 'direct_pins':pins, 'isolated':True}
    def bundle():
        context['tables'], context['metadata'] = load_dashboard_data()
        context['results'] = baseline_analytics(context['tables'], context['metadata']['rfm'])
        require(context['results'] == context['metadata']['baseline_analytics'], 'Baseline metadata berbeda dari CSV')
        return {'bundle_id': context['metadata']['bundle_id'],
                'rows':{key:len(frame) for key,frame in context['tables'].items()}}
    def raw_rebuild():
        fresh, audit = build_analysis_tables()
        fresh['rfm_customers'], rfm_meta = build_rfm(fresh['order_level'])
        require(rfm_meta == context['metadata']['rfm'], 'Metadata RFM hasil sumber berbeda')
        for name, frame in project_tables(fresh).items():
            assert_frame_equal(frame, context['tables'][name])
        recorded = read_json(ROOT/'reports/join_audit.json')
        for key in ['aggregation','joins','eligibility','reconciliation','coverage','contracts','payments_policy']:
            require(audit[key] == recorded[key], 'Audit integrasi berubah: '+key)
        context['fresh'] = fresh
        return {'all_cells_and_dtypes_match':True, 'reconciliation':audit['reconciliation']}
    def independent():
        from scripts.check_integration import independent_reference
        from scripts.check_analytics import raw_reference, verify_reference
        from scripts.check_rfm import independent_customers, verify_summary
        order_item = independent_reference(context['fresh'])
        q1_q2 = verify_reference(context['results']['q1'], context['results']['q2'], raw_reference())
        refs, threshold, coverage = independent_customers()
        actual = jsonable(context['tables']['rfm_customers'])
        require(len(actual) == len(refs), 'Jumlah pelanggan oracle berbeda')
        for row in actual:
            for key, value in refs[row['customer_unique_id']].items():
                require(row[key] == value, f"Oracle RFM berbeda: {key}")
        require(threshold == context['metadata']['rfm']['high_value']['threshold_cents'], 'Ambang oracle berbeda')
        return {'order_item':order_item, 'q1_q2':q1_q2,
                'rfm':verify_summary(context['results']['q3'], refs), 'identity_coverage':coverage}
    def reference():
        recorded = read_json(ROOT/'reports/analytical_results.json')
        for question, result in context['results'].items():
            for key, value in result.items():
                require(value == recorded[question][key], f'Laporan analisis berbeda: {question}.{key}')
        from scripts.prepare_dashboard_data import verify_filter_scenarios
        return verify_filter_scenarios(context['tables'], context['metadata'], recorded)
    def notebook():
        results = notebook_results(ROOT/'notebook.ipynb')
        require(results == context['results'], 'Hasil aktual notebook berbeda dari bundle')
        proof = read_json(ROOT/'reports/notebook_validation.json')
        require(proof['execution_status']=='passed' and proof['visual_review_status']=='passed'
                and proof.get('gate',{}).get('passed'), 'Eksekusi/review visual notebook belum lulus')
        require(sha256_file(ROOT/'notebook.ipynb') == proof['notebook_sha256'], 'Notebook berubah setelah verifikasi')
        require(sha256_file(ROOT/'reports/notebook.html') == proof['html_sha256'], 'HTML notebook usang')
        for entry in proof['figures'].values():
            require(sha256_file(ROOT/entry['path']) == entry['sha256'], 'Figure notebook berubah')
        nb = nbformat.read(ROOT/'notebook.ipynb', as_version=4)
        baseline = read_json(ROOT/'reports/baseline.json')
        require([c.metadata['template_index'] for c in nb.cells if 'template_index' in c.metadata]
                == list(range(baseline['template']['cell_count'])), 'Urutan templat berubah')
        return {'code_cells':proof['executed_code_cells'], 'inline_png':proof['inline_png_outputs'],
                'errors':proof['error_outputs'], 'full_q1_q2_q3_payload_matches':True}
    def identity():
        baseline = read_json(ROOT/'reports/baseline.json')
        source = '\n'.join(cell.source for cell in nbformat.read(ROOT/'notebook.ipynb', as_version=4).cells)
        for key in ['full_name','email','dicoding_id']:
            field = baseline['identity'][key]
            require(field['status']=='provided_by_user' and field['value'] in source, 'Identitas belum lengkap: '+key)
        require(not any(word in source for word in ['[Input Nama','[Input Email','xxx','### Explore ...','#### Load df ...']), 'Placeholder notebook tersisa')
        return {'identity_complete':True, 'template_placeholders_absent':True}
    check('source_and_template_hashes', inputs)
    check('python_and_direct_dependency_pins', runtime)
    check('bundle_schema_keys_types_metadata', bundle)
    check('fresh_raw_pipeline_matches_every_exported_cell', raw_rebuild)
    check('independent_csv_decimal_reference', independent)
    check('analytical_reports_and_12_filter_scenarios', reference)
    check('executed_notebook_and_six_reviewed_figures', notebook)
    check('current_provenance', lambda: verify_provenance(context['metadata']))
    check('identity_and_placeholders', identity)
    check('dashboard_default_metrics_and_aggregates', lambda: verify_ui(context['results']))
    check('sources_still_unchanged', lambda: verify_sources())
    passed = all(item['passed'] for item in checks.values())
    files = ['requirements.txt','requirements-dev.txt','README.md','notebook.ipynb','dashboard/dashboard.py',
        'dashboard/data_metadata.json','scripts/validate_outputs.py','scripts/check_notebook.py',
        *[str(p.relative_to(ROOT)) for p in (ROOT/'src').glob('*.py')]]
    report = {'phase':'P10', 'status':'passed' if passed else 'failed',
        'verified_at':datetime.now(ZoneInfo('Asia/Jakarta')).isoformat(timespec='seconds'),
        'command':'python scripts/validate_outputs.py', 'runtime':{'python':platform.python_version(),
            'executable':sys.executable, 'invocation_cwd':str(Path.cwd()), 'optimized':not __debug__,
            'packages':{d.metadata['Name']:d.version for d in distributions()}},
        'checks':checks, 'artifact_sha256':{path:sha256_file(ROOT/path) if (ROOT/path).is_file() else None for path in files},
        'scope':'Integritas lokal P10; clean install/tes/UI nyata dicatat terpisah. Bukan bukti deployment/ZIP.'}
    path = ROOT/'reports/validation_results.json'
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    print(f'{report["status"].upper()}: {sum(c["passed"] for c in checks.values())}/{len(checks)} pemeriksaan; reports/validation_results.json')
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
