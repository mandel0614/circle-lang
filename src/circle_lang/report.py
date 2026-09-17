"""Self-contained report: recorded states only, no second simulation in JS."""
from html import escape
from importlib.resources import files
import json


def render_report(report):
    template = files('circle_lang').joinpath('data','report.html').read_text(encoding='utf-8')
    payload = json.dumps(report,allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    return template.replace('__TITLE__',escape(report['program'])).replace('__PAYLOAD__',payload)
