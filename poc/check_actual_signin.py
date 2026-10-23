import asyncio
from playwright.async_api import async_playwright

async def check_sign_in_screen():
    profile_dir = r"D:\My Projects\AI-Task_Reviewer\storage\bot_browser_profile"
    chrome_exec = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            executable_path=chrome_exec,
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ],
            ignore_default_args=["--enable-automation"]
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://accounts.google.com/signin/v2/identifier?continue=https://meet.google.com/sbk-bcoj-veq", wait_until="domcontentloaded")
        await asyncio.sleep(4)
        
        url = page.url
        print("Page URL:", url)
        body = await page.evaluate("() => document.body.innerText")
        print("Page text snippet:")
        for line in body.split("\n")[:15]:
            if line.strip():
                print("  ", line.strip())
                
        await page.screenshot(path="storage/logs/signin_screen_actual.png")
        print("Saved screenshot to storage/logs/signin_screen_actual.png")
        await context.close()

if __name__ == "__main__":
    asyncio.run(check_sign_in_screen())
