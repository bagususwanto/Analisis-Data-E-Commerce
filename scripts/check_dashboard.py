"""Verifikasi P09 yang dapat diulang; inspeksi browser dicatat terpisah."""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import subprocess
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.dashboard_data import load_dashboard_data, baseline_analytics


def main():
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q'], cwd=ROOT,
                            capture_output=True, text=True)
    tables, metadata = load_dashboard_data()
    default_match = baseline_analytics(tables, metadata['rfm']) == metadata['baseline_analytics']
    baseline = json.loads((ROOT/'reports/baseline.json').read_text())
    source_hashes_match = all(hashlib.sha256((ROOT/f['path']).read_bytes()).hexdigest() == f['sha256']
                              for f in baseline['source_files'])
    files = ['dashboard/dashboard.py', 'tests/test_dashboard_app.py', 'src/analytics.py',
             'src/charts.py', 'src/dashboard_data.py', 'notebook.ipynb',
             'dashboard/data_metadata.json']
    report = dict(phase='P09', generated_at=datetime.now(ZoneInfo('Asia/Jakarta')).isoformat(),
        python=sys.version, command=f'{sys.executable} -m pytest -q',
        invocation_cwd=str(Path.cwd()), test_exit_code=result.returncode,
        test_output=result.stdout, test_stderr=result.stderr,
        default_matches_notebook_baseline=default_match, source_hashes_match=source_hashes_match, bundle_id=metadata['bundle_id'],
        hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files},
        browser_review={'status':'pending', 'note':'Periksa UI nyata setelah kode terakhir; hasil otomatis tidak menggantikan audit visual.'},
        passed=result.returncode == 0 and default_match and source_hashes_match)
    (ROOT/'reports/dashboard_validation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(result.stdout)
    print('Default sesuai baseline notebook:', default_match)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
