#!/usr/bin/env python3
from pathlib import Path
import sys,yaml
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'triage'/'census'/'ABACUS.census.yaml'
REQ={'identity','locations','architecture','contracts','execution','pipeline','outward_products','automation','integration','governance'}
def main():
 d=yaml.safe_load(P.read_text(encoding='utf-8'))
 assert REQ <= set(d), f'missing {sorted(REQ-set(d))}'
 assert d['identity']['role']=='DOW_DERIVED_ANALYSIS'
 assert 'may not promote engineering facts' in d['governance']['promotion_rules']
 assert 'SHA256' in d['governance']['hashes']
 for method in ['PCA','DMAIC','dependency_analysis','graph_diagnostics']:
  assert method in d['pipeline']['analyze'], f'missing DOW method {method}'
 assert 'Analysis_Return_Bridge' in d['integration']['bridges']
 print('TRIAGE census PASS:',d['identity']['repo']); return 0
if __name__=='__main__': sys.exit(main())
