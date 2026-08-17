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

        selects = await page.query_selector_all("select")
        avg_select = None
        for i, s in enumerate(selects):
            info = await s.evaluate("el => ({id: el.id, opts: Array.from(el.options).map(o=>o.text)})")
            if any('Average' in o for o in info['opts']):
                print(i, info)
                # check if visible
                visible = await s.is_visible()
                if visible:
                    avg_select = s
        if avg_select:
            opts = await avg_select.evaluate("el => Array.from(el.options).map(o=>o.value)")
            print("using select, values:", opts)
            for v in opts:
                if 'avg' in v.lower():
                    await avg_select.select_option(v); break
            await page.wait_for_timeout(400)
            body_text = await page.evaluate("document.body.innerText")
            print("has explanatory phrase:", "not additive" in body_text or "isn't additive" in body_text)
            await page.screenshot(path='/home/claude/work/qa_outline_avg.png')
            # switch to sum
            for v in opts:
                if 'sum' in v.lower():
                    await avg_select.select_option(v); break
            await page.wait_for_timeout(400)
            await page.screenshot(path='/home/claude/work/qa_outline_sum.png')
            body_text2 = await page.evaluate("document.body.innerText")
            print("sum view still has purple dot legend text:", "cumulative %" in body_text2)
        else:
            print("no visible avg select found")
        await browser.close()
    print("ERRORS:", errors if errors else "none")

asyncio.run(main())
