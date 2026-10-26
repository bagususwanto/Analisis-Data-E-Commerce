"""Gate P10 harus menolak output kosong, gagal, atau provenance yang usang."""
import hashlib
import json

import nbformat
import pytest

from scripts.validate_outputs import ValidationError, notebook_results, verify_provenance, verify_sources


def write_notebook(tmp_path, *, outputs=None, execution_count=1):
    cell = nbformat.v4.new_code_cell('result = 1', execution_count=execution_count, outputs=outputs or [])
    path = tmp_path/'notebook.ipynb'
    nbformat.write(nbformat.v4.new_notebook(cells=[cell]), path)
    return path


def snapshot(results=None):
    return nbformat.v4.new_output('display_data', data={'application/json':{
        'artifact':'ecommerce.analytics.v1', 'results':results if results is not None else {'q1':{},'q2':{},'q3':{}}}})


def test_notebook_reads_actual_executed_payload(tmp_path):
    expected = {'q1':{'summary':{'sales_value_cents':123}},'q2':{},'q3':{}}
    path = write_notebook(tmp_path, outputs=[snapshot(expected)])
    assert notebook_results(path) == expected


@pytest.mark.parametrize('outputs,count', [([],1), ([snapshot()],None),
    ([snapshot(), snapshot()],1), ([snapshot({'q1':{}})],1),
    ([snapshot(),nbformat.v4.new_output('error',ename='ValueError',evalue='bad',traceback=[])],1)])
def test_notebook_rejects_stale_or_failed_outputs(tmp_path, outputs, count):
    with pytest.raises(ValidationError):
        notebook_results(write_notebook(tmp_path,outputs=outputs,execution_count=count))


def test_provenance_rejects_changed_reference(tmp_path):
    file = tmp_path/'report.json'
    file.write_text('{}')
    metadata = {'provenance':{'references':{'report.json':hashlib.sha256(b'{}').hexdigest()},'source_csvs':[]}}
    verify_provenance(metadata, tmp_path)
    file.write_text('{"changed":true}')
    with pytest.raises(ValidationError, match='Provenance usang'):
        verify_provenance(metadata, tmp_path)


def test_source_hash_fails_when_file_changes(tmp_path):
    (tmp_path/'reports').mkdir()
    source = tmp_path/'source.csv'; source.write_bytes(b'id\n001\n')
    entry = {'path':'source.csv','sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
    (tmp_path/'reports/baseline.json').write_text(json.dumps({'source_files':[entry], 'template':entry}))
    verify_sources(tmp_path)
    source.write_bytes(b'id\n002\n')
    with pytest.raises(ValidationError, match='Sumber berubah'):
        verify_sources(tmp_path)
