#!/usr/bin/env python3
"""Create an offline, dependency-free, self-contained V2 evidence dashboard."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SCHEMA='codepurple.evidence_observatory.v2'

def render(snapshot: dict, template: str) -> str:
    if snapshot.get('schema')!=SCHEMA:
        raise ValueError('Refuse unsupported evidence schema')
    source=snapshot.get('main',{}).get('sha')
    if not isinstance(source,str) or len(source)!=40 or any(c not in '0123456789abcdef' for c in source):
        raise ValueError('Exact-main source SHA required')
    if template.count('__EVIDENCE_JSON__')!=1:
        raise ValueError('Template marker missing or repeated')
    data=json.dumps(snapshot,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    # Avoid embedding remote issue content as executable markup or JS.
    data=data.replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    return template.replace('__EVIDENCE_JSON__',data)

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--snapshot',type=Path,default=ROOT/'evidence.json')
    p.add_argument('--template',type=Path,default=ROOT/'index.template.html')
    p.add_argument('--output',type=Path,default=ROOT/'index.html')
    a=p.parse_args(argv)
    data=json.loads(a.snapshot.read_text(encoding='utf-8'))
    html=render(data,a.template.read_text(encoding='utf-8'))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(html,encoding='utf-8')
    print(f'CREATED {a.output} bytes={len(html.encode())} sha256={hashlib.sha256(html.encode()).hexdigest()}')

if __name__=='__main__':main()
