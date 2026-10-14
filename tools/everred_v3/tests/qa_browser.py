import asyncio, pathlib, subprocess, time
from playwright.async_api import async_playwright
P=pathlib.Path(__file__).resolve().parents[1]
async def run():
 server=subprocess.Popen(['python','-m','http.server','8765','--bind','127.0.0.1','--directory',str(P/'dashboard')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 await asyncio.sleep(0.5)
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
  errors=[]; page.on('pageerror',lambda e: errors.append(str(e)))
  await page.goto('http://127.0.0.1:8765/index.html');await page.wait_for_timeout(700)
  assert await page.locator('h1').inner_text()=='EVERRED 3.0'
  assert await page.get_by_text('12,731',exact=False).count() >= 1
  assert await page.locator('#rootRows tr').count()==2
  assert await page.locator('#diagramViewer svg').count()==1
  assert 'UNTRUSTED' not in (await page.locator('#trust').inner_text())
  await page.screenshot(path=str(P/'dashboard/qa-desktop.png'),full_page=True)
  await page.locator('[data-tab="1"]').click()
  assert await page.locator('#diagramViewer svg').count()==1
  await page.locator('[data-tab="2"]').click()
  assert await page.locator('#diagramViewer svg').count()==1
  await page.locator('[data-tab="3"]').click()
  assert await page.locator('#diagramViewer svg').count()==1
  await page.locator('#rootSearch').fill('SAFETY');assert await page.locator('#rootRows tr').count()==1
  await page.locator('#rootSearch').fill('');assert await page.locator('#rootRows tr').count()==2
  await page.locator('#fileInputBottom').set_input_files({'name':'invalid.json','mimeType':'application/json','buffer':b'{"schema":"bad"}'})
  assert 'Import rejected' in (await page.locator('#notices').inner_text())
  await page.set_viewport_size({'width':390,'height':844}); await page.reload(); await page.wait_for_timeout(400)
  assert await page.locator('#diagramViewer svg').count()==1
  await page.screenshot(path=str(P/'dashboard/qa-mobile.png'),full_page=True)
  assert not errors,errors
  print('BROWSER QA PASS: desktop/mobile, 4 SVG tabs, root filter, bad import rejection, no JS errors')
  await browser.close()
 server.terminate();server.wait(timeout=3)
asyncio.run(run())
