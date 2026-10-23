import asyncio
from playwright.async_api import async_playwright

async def inspect_google_signin():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        print("Navigating to accounts.google.com ...")
        await page.goto("https://accounts.google.com/signin/v2/identifier?continue=https://meet.google.com", wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(4)

        title = await page.title()
        print(f"Page Title: {title}")
        url = page.url
        print(f"Current URL: {url}")

        body_text = await page.evaluate("() => document.body.innerText")
        lines = [line.strip() for line in body_text.split("\n") if line.strip()]
        print(f"Visible text snippet ({len(lines)} lines):")
        for line in lines[:15]:
            print(f"  {line}")

        await page.screenshot(path="storage/logs/google_signin_test.png")
        print("Saved screenshot to storage/logs/google_signin_test.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_google_signin())
