"""Jalankan assessment P02 dari direktori mana pun; sumber CSV hanya dibaca."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import platform
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
from src.config import ANALYSIS_START, ANALYSIS_END_EXCLUSIVE, PRIMARY_SOURCES
from src.data_assessment import assess_sources


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_inputs(baseline):
    hashes = {}
    for source in baseline['source_files']:
        path = ROOT / source['path']
        current = digest(path)
        if current != source['sha256'] or path.stat().st_size != source['size_bytes']:
            raise ValueError(f'Sumber berubah dari baseline P00: {source["path"]}')
        hashes[source['path']] = current
    template = baseline['template']
    if digest(ROOT / template['path']) != template['sha256']:
        raise ValueError('Templat berubah dari baseline P00')
    return hashes


def markdown(report):
    rows = [
        '# Assessment P02 — bahan notebook', '',
        'Dihasilkan oleh `scripts/assess_data.py` dari sumber mentah; tindakan berikut merupakan rencana P03/P04.', '',
        '## Gathering Data', '',
        '| Sumber | Peran | Baris | Kolom | Duplikasi persis tambahan |',
        '| --- | --- | ---: | ---: | ---: |',
    ]
    for name, p in report['profiles'].items():
        rows.append(f'| {name} | {p["scope"]} | {p["row_count"]:,} | {p["column_count"]} | {p["exact_duplicate_additional_rows"]:,} |')
    rows += ['', 'Semua kolom awal berupa string; parsing hanya dilakukan pada salinan untuk assessment. Sembilan hash sumber cocok dengan baseline sebelum dan setelah assessment.', '',
             '## Assessing Data', '',
             '| Issue | Sumber/kolom | Jenis | Jumlah | Arti bisnis |',
             '| --- | --- | --- | ---: | --- |']
    for i in report['issues']:
        rows.append(f'| {i["issue_id"]} | {i["source"]}: {", ".join(i["columns"])} | {i["kind"]} | {i["affected_count"]:,} {i["affected_unit"]} | {i["business_meaning"]} |')
    rows += ['', 'Jumlah antar-issue dapat tumpang tindih dan tidak boleh dijumlahkan menjadi total baris bermasalah.', '',
             '## Steps to Take', '', '| Issue | Tindakan | Metrik | Pemilik |', '| --- | --- | --- | --- |']
    for i in report['issues']:
        rows.append(f'| {i["issue_id"]} | {i["planned_action"]} | {", ".join(i["affected_metrics"])} | {i["owner_phase"]} |')
    rows += ['', '## Konteks dan pemeriksaan tanpa pelanggaran', '',
             '- Keunikan kunci wajib, missing per kolom/status, kegagalan parsing, domain skor, nilai negatif/nol, presisi sen, dan foreign key (termasuk hasil nol) tersedia di JSON.',
             '- Kode pos geolocation bukan kunci unik. Duplikasi geolocation belum dihapus karena sumber tersebut tidak dipakai untuk Q1–Q3.',
             '- Harga tinggi tidak dipangkas. Freight bernilai nol tetap valid; monetary berasal dari price item.',
             '- Periode utama mengikuti config. Hitungan per bulan hanya menunjukkan kepadatan pencatatan, bukan bukti kelengkapan bulan atau tren bisnis final.',
             '- Missing approval/carrier tidak otomatis membuktikan kesalahan pada semua status. Missing penerimaan pada delivered perlu dilaporkan sebagai keterbatasan evaluasi delivery.',
             '- Tidak ada imputasi, seleksi ulasan, filter transaksi, atau ekspor tabel analisis pada P02.', '']
    return '\n'.join(rows)


def main():
    baseline_path = ROOT / 'reports/baseline.json'
    baseline = json.loads(baseline_path.read_text())
    before = verify_inputs(baseline)
    profiles, facts, issues = assess_sources()
    for source in baseline['source_files']:
        name = Path(source['path']).stem
        if profiles[name]['row_count'] != source['row_count'] or profiles[name]['columns'] != source['columns']:
            raise ValueError(f'Baris/skema berbeda dari baseline: {name}')
    after = verify_inputs(baseline)
    if before != after:
        raise ValueError('Sumber berubah selama assessment')
    observed = baseline['initial_plan_comparison']['observed']
    comparisons = {
        'delivered_orders': facts['order_status_counts']['delivered'],
        'products_missing_category': facts['categories']['missing_products'],
        'orders_multiple_reviews': facts['reviews']['order_id']['duplicate_key_groups'],
        'additional_repeated_review_ids': facts['reviews']['review_id']['additional_duplicate_keys'],
        'orders_multiple_payments': facts['supporting']['orders_with_multiple_payments'],
        'delivered_missing_delivery_dates': facts['delivered_missing_dates']['order_delivered_customer_date']['all_periods'],
        'missing_review_titles': profiles['order_reviews_dataset']['missing_including_whitespace']['review_comment_title'],
        'missing_review_messages': profiles['order_reviews_dataset']['missing_including_whitespace']['review_comment_message'],
    }
    if any(observed[k] != value for k, value in comparisons.items()):
        raise ValueError('Hasil assessment berbeda dari profil P00; inspeksi sebelum memperbarui laporan')
    if len({i['kind'] for i in issues}) < 2 or not all(i['planned_action'] for i in issues):
        raise ValueError('Gate minimal masalah aktual dan kebijakan belum terpenuhi')
    stamp = datetime.now(ZoneInfo('Asia/Jakarta')).isoformat(timespec='seconds')
    report = {
        'phase': 'P02', 'status': 'completed', 'assessed_at': stamp,
        'generator': 'scripts/assess_data.py',
        'runtime': {'python': platform.python_version(), 'pandas': pd.__version__, 'invocation_cwd': str(Path.cwd())},
        'definitions': {
            'raw_dtype': 'StringDtype; loader menjaga representasi sumber',
            'missing': 'pd.NA atau teks hanya whitespace; empty_field_counts hanya pd.NA',
            'duplicate_additional_rows': 'duplicated(keep=first); all_rows memakai keep=False',
            'date_format': '%Y-%m-%d %H:%M:%S; parse failures mengecualikan field kosong',
            'numeric': 'Decimal dari teks asli; nilai nonfinite terpisah dari parse failure; presisi sen diuji tanpa pembulatan',
            'scope': 'Semua baris mentah kecuali fakta berlabel analysis_period; tidak ada filter/cleaning sumber',
            'chronology': 'Timestamp penuh untuk urutan lifecycle; calendar_date_affected_rows disertakan. Estimasi diuji sebagai tanggal kalender.',
            'analysis_period': {'start_inclusive': str(ANALYSIS_START), 'end_exclusive': str(ANALYSIS_END_EXCLUSIVE)},
            'counts_overlap': 'Issue dapat tumpang tindih; affected_unit dan denominator wajib diperhatikan',
            'foreign_key': 'missing_key_rows terpisah dari unmatched_nonmissing_rows; bukan hasil join tabel analisis',
        },
        'profiles': profiles, 'facts': facts, 'issues': issues,
        'gate': {'passed': True, 'primary_sources_loaded': list(PRIMARY_SOURCES),
                 'source_rows_and_schema_match_baseline': True, 'source_hashes_before_after_match': True,
                 'template_hash_matches': True, 'p00_profile_comparisons': comparisons,
                 'issue_count': len(issues), 'distinct_issue_kinds': len({i['kind'] for i in issues}),
                 'every_issue_has_action': True},
        'source_sha256': after,
    }
    # Tambahkan profil formal; pertahankan hash, identitas, dan riwayat P00.
    for source in baseline['source_files']:
        source['assessment_profile'] = profiles[Path(source['path']).stem]
    baseline['assessment'] = {'phase': 'P02', 'assessed_at': stamp, 'report': 'reports/data_quality.json',
                              'summary_for_notebook': 'reports/assessment_summary.md',
                              'source_hashes_match_p00': True}
    (ROOT / 'reports/data_quality.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    (ROOT / 'reports/assessment_summary.md').write_text(markdown(report))
    baseline_path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(f'PASS P02: {len(profiles)} sources, {len(issues)} issues with actions; 9 source hashes unchanged.')
    print(json.dumps({'facts': facts, 'issues': [{k:i[k] for k in ('issue_id','affected_count','affected_unit')} for i in issues]}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
