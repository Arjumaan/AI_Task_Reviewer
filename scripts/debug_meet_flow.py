import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def inspect():
    async with async_playwright() as p:
        profile_dir = Path("storage/bot_browser_profile").resolve()
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        page = context.pages[0] if context.pages else await context.new_page()
        print("Navigating to https://meet.google.com/rqp-ctfg-nri ...")
        await page.goto("https://meet.google.com/rqp-ctfg-nri", wait_until="domcontentloaded")
        for i in range(1, 10):
            await asyncio.sleep(1)
            print(f"[{i}s] URL: {page.url}")
            title = await page.title()
            print(f"[{i}s] Title: {title}")
            body_text = await page.evaluate("() => document.body.innerText")
            if "You can't join" in body_text:
                print(f"[{i}s] BLOCKED DETECTED: 'You can\\'t join this video call'")
            if "Sign in" in body_text or "sign in" in body_text.lower():
                print(f"[{i}s] SIGN IN text found")
            buttons = await page.evaluate("() => Array.from(document.querySelectorAll('button, a, [role=\"button\"]')).map(el => (el.innerText || '').trim()).filter(Boolean)")
            print(f"[{i}s] Buttons/Links: {buttons[:10]}")
            if "Join now" in buttons:
                print(f"[{i}s] 'Join now' button is IN DOM!")
            if "Ask to join" in buttons:
                print(f"[{i}s] 'Ask to join' button is IN DOM!")
        await context.close()

if __name__ == "__main__":
    asyncio.run(inspect())
