import asyncio
from playwright.async_api import async_playwright

async def test_email_next():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ],
            ignore_default_args=["--enable-automation"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.goto("https://accounts.google.com/signin/v2/identifier?continue=https://meet.google.com", wait_until="networkidle")

        email_input = await page.wait_for_selector("input[type='email'], input#identifierId", timeout=10000)
        print("Email input found:", email_input is not None)
        if email_input:
            await email_input.fill("testrevieweraibot999@gmail.com")
            next_btn = await page.query_selector("button:has-text('Next'), #identifierNext")
            if next_btn:
                await next_btn.click()
                print("Clicked Next...")
                await asyncio.sleep(4)
                
                body_text = await page.evaluate("() => document.body.innerText")
                print("Current page text snippet:")
                for line in body_text.split("\n")[:10]:
                    if line.strip():
                        print("  ", line.strip())

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_email_next())
