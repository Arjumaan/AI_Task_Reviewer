import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def is_google_authenticated() -> bool:
    profile_dir = Path("storage/bot_browser_profile").resolve()
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        cookies = await context.cookies("https://google.com")
        cookie_names = [c["name"] for c in cookies]
        is_logged_in = any(c in cookie_names for c in ["SID", "SSID", "SAPISID", "HSID"])
        print(f"Cookie check - Logged in to Google: {is_logged_in}")
        await context.close()
        return is_logged_in

if __name__ == "__main__":
    asyncio.run(is_google_authenticated())
