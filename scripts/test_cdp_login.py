import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://accounts.google.com")
        await asyncio.sleep(2)
        print("Page title:", await page.title())
        email_inp = await page.query_selector('input[type="email"], #identifierId')
        if email_inp:
            await email_inp.fill("exampleuser123@gmail.com")
            await page.keyboard.press("Enter")
            await asyncio.sleep(4)
            print("URL after Enter:", page.url)
            body = await page.evaluate("() => document.body.innerText")
            if "This browser or app may not be secure" in body:
                print("Blocked: This browser or app may not be secure")
            else:
                print("SUCCESS! Not blocked!")
                print("Body snippet:", body[:200])

if __name__ == "__main__":
    asyncio.run(test())
