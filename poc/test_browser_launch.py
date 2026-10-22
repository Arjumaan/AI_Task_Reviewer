"""
Playwright Browser & Google Meet UI Exploration Script.
Uses the system Google Chrome binary to test launching with WebRTC media permissions,
navigating to Google Meet, and checking selector behavior.
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

async def test_chrome_meet():
    print("=" * 60)
    print("PLAYWRIGHT & CHROME GOOGLE MEET AUTOMATION TEST")
    print("=" * 60)
    
    async with async_playwright() as p:
        print(f"Launching system Chrome from: {CHROME_PATH}")
        browser = await p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=[
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                "--autoplay-policy=no-user-gesture-required",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )
        
        context = await browser.new_context(
            permissions=["microphone", "camera"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        print("Navigating to https://meet.google.com/ ...")
        await page.goto("https://meet.google.com/", wait_until="networkidle", timeout=30000)
        
        title = await page.title()
        print(f"Google Meet Landing Page Title: {title}")
        
        # Test navigation to a mock/dry-run meeting room
        test_meeting_code = "abc-defg-hij"
        test_url = f"https://meet.google.com/{test_meeting_code}"
        print(f"Navigating to meeting room: {test_url} ...")
        await page.goto(test_url, wait_until="load", timeout=30000)
        await asyncio.sleep(4)
        
        room_title = await page.title()
        print(f"Meeting Room Title: {room_title}")
        
        # Check for Google Sign-in prompt or Guest Name input
        content = await page.content()
        has_signin = "accounts.google.com" in page.url or "Sign in" in content
        has_name_input = await page.query_selector("input[type='text']") is not None
        
        print(f"Current URL: {page.url}")
        print(f"Redirected to Google Sign-in: {has_signin}")
        print(f"Found Guest Name Input Field: {has_name_input}")
        
        # Save screenshot for audit
        out_screenshot = Path("poc") / "meet_exploration.png"
        out_screenshot.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(out_screenshot))
        print(f"Saved exploration screenshot to: {out_screenshot.resolve()}")
        
        await browser.close()
        print("[SUCCESS] Chrome launch and Google Meet page inspection completed!")
        return {
            "title": title,
            "room_title": room_title,
            "has_signin": has_signin,
            "has_name_input": has_name_input
        }

if __name__ == "__main__":
    asyncio.run(test_chrome_meet())
