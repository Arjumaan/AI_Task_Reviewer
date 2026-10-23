import asyncio
from playwright.async_api import async_playwright

async def test_nav():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        test_url = 'https://meet.google.com/rqp-ctfg-nri'
        print('Navigating to', test_url)
        try:
            await page.goto(test_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(4)
            print('Page Body text before dismiss:\n', (await page.inner_text('body'))[:500])
            
            # Click continue without mic/cam
            cont_btn = await page.query_selector("button:has-text('Continue without microphone and camera'), button[jsname='IbE0S']")
            if cont_btn:
                print('Found Continue button, clicking it...')
                await cont_btn.click()
                await asyncio.sleep(3)
            
            print('Page Body text after dismiss:\n', (await page.inner_text('body'))[:600])
            buttons = await page.query_selector_all('button, div[role="button"], input')
            print(f'Found {len(buttons)} interactable elements after dismiss:')
            for b in buttons:
                txt = (await b.inner_text()).strip()
                aria = await b.get_attribute('aria-label') or ''
                jsname = await b.get_attribute('jsname') or ''
                if txt or aria:
                    print(f'  Elem: Text={repr(txt[:40])} | Aria={repr(aria[:40])} | jsname={jsname}')
            
            await page.screenshot(path='poc/after_dismiss.png')
            print('Screenshot saved to poc/after_dismiss.png')
        except Exception as e:
            print('Exception:', e)
        finally:
            await browser.close()

if __name__ == '__main__':
    asyncio.run(test_nav())
