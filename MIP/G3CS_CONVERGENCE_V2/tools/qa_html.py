#!/usr/bin/env python3
"""Offline three-viewport browser QA with source and screenshot hashes."""
import hashlib
import json
import os
import re
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

from converge import digest

root=Path(__file__).resolve().parents[1]
pagefile=(root/'output/G3CS_CONVERGENCE_DASHBOARD.html').resolve()
sourcefile=root/'source/G3CS_CONVERGENCE_INPUT.json'
qadir=root/'qa'
qadir.mkdir(parents=True,exist_ok=True)
source=json.loads(sourcefile.read_text(encoding='utf-8'))
html_bytes=pagefile.read_bytes()
html_text=html_bytes.decode('utf-8')
meta=re.search(r'<meta name="source-sha256" content="([a-f0-9]{64})"',html_text)
assert meta is not None and meta.group(1)==digest(source),'HTML source digest is stale'
report={'schema':'codepurple.g3cs.html-browser-qa.v2','tested_file':pagefile.name,
        'source_sha256':meta.group(1),'html_sha256':hashlib.sha256(html_bytes).hexdigest(),
        'viewports':{},'errors':[]}
with sync_playwright() as p:
    executable=os.environ.get('G3CS_BROWSER_PATH') or shutil.which('chromium') or shutil.which('msedge')
    kwargs={'executable_path':executable} if executable else {}
    browser=p.chromium.launch(headless=True,**kwargs)
    for name,w,h in [('desktop',1440,1000),('laptop',1280,800),('mobile',390,844)]:
        tab=browser.new_page(viewport={'width':w,'height':h},device_scale_factor=1)
        errors=[];tab.on('pageerror',lambda err: errors.append('pageerror '+str(err)))
        tab.on('console',lambda msg: errors.append('console.error '+msg.text) if msg.type=='error' else None)
        tab.set_content(html_text,wait_until='load')
        dim=tab.evaluate('''() => ({scroll: document.documentElement.scrollWidth,inner:window.innerWidth,
          body:document.body.scrollWidth,title:document.title, visible:document.querySelectorAll('.atom:not([hidden])').length,
          images:[...document.images].map(i=>({ok:i.complete&&i.naturalWidth>0,src:i.getAttribute('src')}))})''')
        assert dim['scroll']<=dim['inner'],f'{name} horizontal overflow {dim}'
        assert dim['body']<=dim['inner'],f'{name} body overflow {dim}'
        assert dim['visible']>=20 and all(x['ok'] for x in dim['images']),f'{name} visual loading {dim}'
        tab.locator('#type-filter').select_option('AUTHORITY')
        authority=tab.locator('.atom:not([hidden])').count()
        assert 1<=authority<dim['visible'],f'{name} type filter ineffective'
        tab.locator('#node-search').fill('approval')
        search=tab.locator('.atom:not([hidden])').count()
        assert search<authority,f'{name} search ineffective: {search} >= {authority}'
        tab.locator('#node-search').fill('')
        tab.locator('#type-filter').select_option('all')
        shot=qadir/f'g3cs_{name}.png'
        tab.screenshot(path=str(shot),full_page=True)
        report['viewports'][name]={'width':w,'height':h,'horizontal_overflow_px':max(0,dim['scroll']-dim['inner']),
            'atom_count':dim['visible'],'authority_filter_count':authority,'compound_search_count':search,
            'images_ok':len(dim['images']),'errors':errors,'screenshot':f'qa/g3cs_{name}.png',
            'screenshot_sha256':hashlib.sha256(shot.read_bytes()).hexdigest()}
        if errors:report['errors'].extend([name+': '+x for x in errors])
        tab.close()
    browser.close()
assert not report['errors'],report['errors']
(qadir/'browser_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
