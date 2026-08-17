import asyncio, sys
from playwright.async_api import async_playwright

async def main():
    errors = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        page = await browser.new_page(viewport={'width':1440,'height':1000})
        page.on('console', lambda msg: errors.append(f'console:{msg.type}:{msg.text}') if msg.type == 'error' else None)
        page.on('pageerror', lambda exc: errors.append(f'pageerror:{exc}'))
        await page.goto(f'file://{sys.argv[1]}')
        await page.wait_for_timeout(500)

        tabs = await page.query_selector_all("nav button, .tab, [role=tab]")
        for t in tabs:
            txt = (await t.inner_text()).strip()
            if 'Outline' in txt:
                await t.click(); break
        await page.wait_for_timeout(400)

        # dump text near each select on the page
        selects = await page.query_selector_all("select")
        for i, s in enumerate(selects):
            ctx = await s.evaluate("""(el) => {
                let cur = el;
                for (let up=0; up<4 && cur; up++){ cur = cur.parentElement; }
                return cur ? cur.innerText.slice(0,150).replace(/\\n/g,' | ') : '';
            }""")
            print(i, '::', ctx)
        await browser.close()
    print("ERRORS:", errors if errors else "none")

asyncio.run(main())
