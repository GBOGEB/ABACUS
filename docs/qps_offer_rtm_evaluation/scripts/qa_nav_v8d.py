import asyncio, sys
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        page = await browser.new_page(viewport={'width':1440,'height':1000})
        await page.goto(f'file://{sys.argv[1]}')
        await page.wait_for_timeout(500)
        tabs = await page.query_selector_all("nav button, .tab, [role=tab]")
        for t in tabs:
            if 'Outline' in (await t.inner_text()).strip():
                await t.click(); break
        await page.wait_for_timeout(400)
        selects = await page.query_selector_all("select")
        target = None
        for s in selects:
            info = await s.evaluate("el => Array.from(el.options).map(o=>o.text)")
            if any('Average' in o for o in info) and await s.is_visible():
                target = s; break
        await target.scroll_into_view_if_needed()
        opts = await target.evaluate("el => Array.from(el.options).map(o=>o.value)")
        for v in opts:
            if 'avg' in v.lower():
                await target.select_option(v); break
        await page.wait_for_timeout(300)
        await page.screenshot(path='/home/claude/work/qa_outline_avg2.png')
        for v in opts:
            if 'sum' in v.lower():
                await target.select_option(v); break
        await page.wait_for_timeout(300)
        await page.screenshot(path='/home/claude/work/qa_outline_sum2.png')
        await browser.close()

asyncio.run(main())
