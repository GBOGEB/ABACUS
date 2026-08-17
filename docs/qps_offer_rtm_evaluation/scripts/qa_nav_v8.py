import asyncio, sys
from playwright.async_api import async_playwright

async def main():
    errors = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        page = await browser.new_page(viewport={'width':1440,'height':900})
        page.on('console', lambda msg: errors.append(f'console:{msg.type}:{msg.text}') if msg.type == 'error' else None)
        page.on('pageerror', lambda exc: errors.append(f'pageerror:{exc}'))
        await page.goto(f'file://{sys.argv[1]}')
        await page.wait_for_timeout(800)

        # overflow check on load
        ow = await page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        print("initial horizontal overflow px:", ow)

        # find and click the Document Outline tab
        tabs = await page.query_selector_all("nav button, .tab, [role=tab]")
        clicked = False
        for t in tabs:
            txt = (await t.inner_text()).strip()
            if 'Outline' in txt or 'outline' in txt.lower():
                await t.click()
                clicked = True
                print("clicked tab:", txt)
                break
        if not clicked:
            # try generic nav links
            links = await page.query_selector_all("a, button")
            for t in links:
                txt = (await t.inner_text()).strip()
                if txt == 'Document Outline' or 'Document Outline' in txt:
                    await t.click(); clicked=True; print("clicked link:", txt); break
        await page.wait_for_timeout(500)

        # find measure select near "Top-level section volume"
        selects = await page.query_selector_all("select")
        print("select count on page:", len(selects))
        target_select = None
        for s in selects:
            # find nearby heading text
            html_ctx = await s.evaluate("(el) => { let p = el.closest('section, div'); return p ? p.innerText.slice(0,120) : ''; }")
            if 'Pareto' in html_ctx or 'section volume' in html_ctx.lower():
                target_select = s
                print("found candidate select, context:", html_ctx[:100])
                break
        if target_select:
            options = await target_select.eval_on_selector("select", "el => Array.from(el.options).map(o=>o.value+':'+o.text)") if False else None
            opts = await target_select.evaluate("el => Array.from(el.options).map(o=>({value:o.value,text:o.text}))")
            print("options:", opts)
            avg_val = None
            for o in opts:
                if 'avg' in o['value'].lower() or 'Average' in o['text']:
                    avg_val = o['value']; break
            if avg_val:
                await target_select.select_option(avg_val)
                await page.wait_for_timeout(400)
                await page.screenshot(path='/home/claude/work/qa_outline_avg.png', full_page=False)
                # check the container text for our explanatory note
                body_text = await page.evaluate("document.body.innerText")
                has_note = 'not additive' in body_text or "isn't additive" in body_text or 'not a real' in body_text.lower()
                print("explanatory note present:", has_note)
                # switch back to count/sum to confirm dot still shows
                for o in opts:
                    if 'sum' in o['value'].lower() or 'Sum' in o['text']:
                        await target_select.select_option(o['value'])
                        break
                await page.wait_for_timeout(400)
                await page.screenshot(path='/home/claude/work/qa_outline_sum.png', full_page=False)
        else:
            print("WARNING: could not locate the Outline Pareto measure select")

        ow2 = await page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        print("post-interaction horizontal overflow px:", ow2)

        await browser.close()
    print("ERRORS:", errors if errors else "none")

asyncio.run(main())
