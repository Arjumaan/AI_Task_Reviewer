import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def test_signin_page():
    async with async_playwright() as p:
        profile_dir = Path("storage/bot_browser_profile").resolve()
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://accounts.google.com", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        title = await page.title()
        print("Page Title:", title)
        inputs = await page.evaluate("() => Array.from(document.querySelectorAll('input')).map(i => ({id: i.id, name: i.name, type: i.type}))")
        print("Inputs:", inputs)
        await context.close()

if __name__ == "__main__":
    asyncio.run(test_signin_page())
