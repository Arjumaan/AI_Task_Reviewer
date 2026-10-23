import asyncio
import os
from playwright.async_api import async_playwright

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

async def test_chrome_meet():
    async with async_playwright() as p:
        user_data = os.path.abspath("storage/bot_browser_profile")
        print(f"Launching Real Chrome ({CHROME_PATH}) with profile ({user_data})...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data,
            executable_path=CHROME_PATH,
            headless=False,
            viewport={"width": 1280, "height": 720},
            permissions=["microphone", "camera"],
            args=[
                "--use-fake-ui-for-media-stream",
                "--autoplay-policy=no-user-gesture-required",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )
        page = context.pages[0] if context.pages else await context.new_page()
        test_url = "https://meet.google.com/rqp-ctfg-nri"
        print(f"Navigating to {test_url} ...")
        await page.goto(test_url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(4)
        
        print("Current URL:", page.url)
        print("Page Title:", await page.title())
        
        # Check for pre-call prompts
        for sel in [
            "button:has-text('Continue without microphone and camera')",
            "button:has-text('Continue without microphone')",
            "button:has-text('Continue without camera')",
            "button:has-text('Dismiss')",
            "button[aria-label*='dismiss' i]",
            "button[jsname='IbE0S']"
        ]:
            b = await page.query_selector(sel)
            if b:
                try:
                    await b.click()
                    print(f"Dismissed prompt via: {sel}")
                    await asyncio.sleep(1)
                except Exception:
                    pass

        # Look for buttons
        buttons = await page.query_selector_all("button, div[role='button']")
        for btn in buttons:
            txt = (await btn.inner_text()).strip()
            aria = await btn.get_attribute("aria-label") or ""
            if "join" in txt.lower() or "join" in aria.lower() or "ask" in txt.lower():
                print(f"Found Join/Ask button: Text={repr(txt)} | Aria={repr(aria)}")

        await asyncio.sleep(5)
        await context.close()

if __name__ == "__main__":
    asyncio.run(test_chrome_meet())
