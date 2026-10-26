"""Eksekusi notebook P07 pada kernel .venv baru, ekspor HTML dan audit output."""
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    with TemporaryDirectory(prefix='ecommerce-notebook-') as temp:
        temp=Path(temp)
        for name,folder in [('IPYTHONDIR','ipython'),('MPLCONFIGDIR','matplotlib'),('JUPYTER_RUNTIME_DIR','runtime')]:
            directory=temp/folder;directory.mkdir();os.environ[name]=str(directory)
        import hashlib
        import json
        from datetime import datetime
        from zoneinfo import ZoneInfo
        import nbformat
        from nbclient import NotebookClient
        from jupyter_client import KernelManager
        from nbconvert import HTMLExporter
        from scripts.assess_data import verify_inputs
        # Siapkan cache font di proses runner; jangan penuhi output notebook
        # dengan pesan pembangunan cache pada kernel yang baru.
        import matplotlib.font_manager

        baseline=json.loads((ROOT/'reports/baseline.json').read_text())
        before=verify_inputs(baseline)
        for report_name,validation_name in [('analytical_results','rfm_validation'),('join_audit','integration_validation')]:
            key='analytical_results_sha256' if report_name=='analytical_results' else 'join_audit_sha256'
            digest=hashlib.sha256((ROOT/f'reports/{report_name}.json').read_bytes()).hexdigest()
            assert digest==json.loads((ROOT/f'reports/{validation_name}.json').read_text())[key]
        path=ROOT/'notebook.ipynb';nb=nbformat.read(path,as_version=4)
        for cell in nb.cells:
            if cell.cell_type=='code':cell.outputs=[];cell.execution_count=None
        manager=KernelManager(kernel_name='python3')
        manager.kernel_spec.argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}']
        client=NotebookClient(nb,km=manager,timeout=300,allow_errors=False,
                             resources={'metadata':{'path':str(ROOT)}},record_timing=True)
        try:
            client.execute(cwd=str(ROOT))
        except Exception:
            nbformat.write(nb,ROOT/'reports/notebook_failed.ipynb')
            raise
        finally:
            if manager.has_kernel:manager.shutdown_kernel(now=True)
        nbformat.validate(nb)
        code=[c for c in nb.cells if c.cell_type=='code']
        assert [c.execution_count for c in code]==list(range(1,len(code)+1))
        errors=[o for c in code for o in c.outputs if o.output_type=='error']
        assert not errors
        snapshots=[o['data']['application/json'] for c in code for o in c.outputs
                   if o.output_type in ('display_data','execute_result')
                   and o.get('data',{}).get('application/json',{}).get('artifact')=='ecommerce.analytics.v1']
        assert len(snapshots)==1, 'Notebook harus mengeluarkan satu payload Q1–Q3 aktual'
        results=json.loads((ROOT/'reports/analytical_results.json').read_text())
        for question,result in snapshots[0]['results'].items():
            for key,value in result.items():
                assert value==results[question][key], f'Payload notebook berbeda: {question}.{key}'
        images=[o for c in code for o in c.outputs if o.output_type in ('display_data','execute_result') and 'image/png' in o.get('data',{})]
        assert len(images)==6, f'Jumlah output gambar tak sesuai: {len(images)}'
        indices=[c.metadata['template_index'] for c in nb.cells if 'template_index' in c.metadata]
        assert indices==list(range(baseline['template']['cell_count']))
        source='\n'.join(c.source for c in nb.cells)
        for placeholder in ['[Input Nama','[Input Email','xxx','### Explore ...','#### Load df ...']:
            assert placeholder not in source,placeholder
        for heading in ['## Menentukan Pertanyaan Bisnis','## Import Semua Packages/Library yang Digunakan','## Data Wrangling',
            '### Gathering Data','### Assessing Data','### Cleaning Data','## Exploratory Data Analysis (EDA)',
            '## Visualization & Explanatory Analysis','### Pertanyaan 1:','### Pertanyaan 2:',
            '## Analisis Lanjutan (Opsional)','## Conclusion & Recommendation']:
            assert heading in source,heading
        after=verify_inputs(baseline);assert before==after
        nbformat.write(nb,path)
        html,_=HTMLExporter(template_name='lab',embed_images=True).from_notebook_node(nb)
        html_path=ROOT/'reports/notebook.html';html_path.write_text(html)
        figures={}
        for file in sorted((ROOT/'reports/figures').glob('V0*.png')):
            from PIL import Image
            with Image.open(file) as pic:width,height=pic.size
            figures[file.name]={'path':str(file.relative_to(ROOT)),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
                                'width':width,'height':height,'size_bytes':file.stat().st_size}
        assert len(figures)==6
        report={'phase':'P07','execution_status':'passed','visual_review_status':'pending',
                'executed_at':datetime.now(ZoneInfo('Asia/Jakarta')).isoformat(timespec='seconds'),
                'kernel_executable':sys.executable,'invocation_cwd':str(Path.cwd()),'kernel_cwd':str(ROOT),
                'notebook_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'html_sha256':hashlib.sha256(html_path.read_bytes()).hexdigest(),
                'template_cells_preserved':len(indices),'total_cells':len(nb.cells),'executed_code_cells':len(code),
                'error_outputs':len(errors),'inline_png_outputs':len(images),'figures':figures,
                'analytics_payload_sha256':hashlib.sha256(json.dumps(snapshots[0],sort_keys=True,
                    ensure_ascii=False,allow_nan=False).encode()).hexdigest(),
                'source_sha256':after,'template_hash_unchanged':True,
                'note':'Eksekusi bersih lulus; phase baru completed setelah pemeriksaan render keenam figure dicatat.'}
        (ROOT/'reports/notebook_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(f'PASS notebook execution: {len(code)} code cells; 6 figures; 0 errors. Visual review pending.')


if __name__=='__main__':main()
