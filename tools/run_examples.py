"""Produce five profile demonstrations and the predefined cohesion control."""
import json
from importlib.resources import files
from pathlib import Path
from circle_lang import compile_source, run
from circle_lang.report import render_report

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'runs'
OUT.mkdir(exist_ok=True)
cases = [
    ('hello', '00_hello_cell.circle', {'signals':{'A':'HIGH','B':'LOW'}}, [0]),
    ('navigation', '01_navigation.circle', {}, list(range(5))),
    ('homeostasis', '02_homeostasis.circle', json.loads((ROOT/'examples/02_calibrated_runtime.json').read_text(encoding='utf-8')), list(range(5))),
    ('composition', '03_composition.circle', {}, list(range(5))),
    ('cohesion', '04_cohesion.circle', {}, [0]),
    ('control', '04_cohesion.circle', {'interaction':False}, [0]),
]
summaries = []
for name,source,config,seeds in cases:
    artifact = compile_source((ROOT/'examples'/source).read_text(encoding='utf-8'))
    report = run(artifact,config=config,seeds=seeds)
    (OUT/(name+'.bioir.json')).write_text(json.dumps(artifact,indent=2)+'\n')
    (OUT/(name+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    (OUT/(name+'.html')).write_text(render_report(report))
    summaries.append({'example':name,**report['summary']})
    print(name,report['summary'],flush=True)
(OUT/'example-summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
(OUT/'index.html').write_text(files('circle_lang').joinpath('data','gallery.html').read_text(encoding='utf-8'))
