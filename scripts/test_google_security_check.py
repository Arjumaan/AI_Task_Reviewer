import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def test_google_login():
    profile_dir = Path("storage/bot_browser_profile").resolve()
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://accounts.google.com", wait_until="networkidle")
        print("Initial URL:", page.url)
        print("Initial Title:", await page.title())
        
        email_input = await page.query_selector('input[type="email"], #identifierId')
        if email_input:
            print("Found email input. Submitting test identifier...")
            await email_input.fill("exampleuser123@gmail.com")
            await page.keyboard.press("Enter")
            await asyncio.sleep(4)
            print("After Enter URL:", page.url)
            print("After Enter Title:", await page.title())
            body = await page.evaluate("() => document.body.innerText")
            for line in body.split("\n"):
                if any(w in line.lower() for w in ["secure", "browser", "couldn't", "can't", "device"]):
                    print("SECURITY FLAG IN BODY:", line)
            await page.screenshot(path="storage/logs/google_signin_security.png")
            print("Saved screenshot to storage/logs/google_signin_security.png")
        await context.close()

if __name__ == "__main__":
    asyncio.run(test_google_login())
