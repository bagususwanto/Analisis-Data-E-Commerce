"""Catat inspeksi enam PNG yang sudah dilakukan; tidak melakukan review otomatis."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.dashboard_data import sha256_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviewer', required=True)
    parser.add_argument('--notes', required=True)
    args = parser.parse_args()
    if not args.reviewer.strip() or not args.notes.strip():
        parser.error('Reviewer dan catatan pemeriksaan harus diisi')
    path = ROOT/'reports/notebook_validation.json'
    report = json.loads(path.read_text())
    if report['execution_status'] != 'passed' or len(report['figures']) != 6:
        raise SystemExit('Eksekusi notebook/enam figure belum lulus')
    for name, digest in [('notebook.ipynb',report['notebook_sha256']), ('reports/notebook.html',report['html_sha256'])]:
        if sha256_file(ROOT/name) != digest:
            raise SystemExit(f'{name} berubah setelah eksekusi; jalankan ulang checker')
    for entry in report['figures'].values():
        if sha256_file(ROOT/entry['path']) != entry['sha256']:
            raise SystemExit(f"Figure berubah setelah eksekusi: {entry['path']}")
    report['visual_review_status'] = 'passed'
    report['visual_review'] = {'reviewer':args.reviewer, 'notes':args.notes,
        'reviewed_at':datetime.now(ZoneInfo('Asia/Jakarta')).isoformat(timespec='seconds'),
        'figure_sha256':{name:entry['sha256'] for name,entry in report['figures'].items()}}
    report['gate'] = {'passed':True, 'scope':'Notebook analitis: eksekusi bersih dan enam render ditinjau; bukan deployment/paket final.'}
    report['note'] = 'Eksekusi dan pemeriksaan visual lulus; review berlaku untuk hash figure yang tercatat.'
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('PASS: catatan inspeksi visual enam figure tersimpan.')


if __name__ == '__main__':
    main()
