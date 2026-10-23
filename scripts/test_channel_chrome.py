import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def test():
    profile_dir = Path("storage/test_profile").resolve()
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel="chrome",
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://accounts.google.com", wait_until="networkidle")
        print("Page URL:", page.url)
        print("Page Title:", await page.title())
        await page.fill('input[type="email"], #identifierId', "exampleuser123@gmail.com")
        await page.keyboard.press("Enter")
        await asyncio.sleep(4)
        print("After Enter URL:", page.url)
        print("After Enter Title:", await page.title())
        body = await page.evaluate("() => document.body.innerText")
        is_blocked = "This browser or app may not be secure" in body
        print("Is blocked with 'browser not secure':", is_blocked)
        await context.close()

if __name__ == "__main__":
    asyncio.run(test())
