import asyncio
from playwright.async_api import async_playwright

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

async def inspect_meet_elements():
    async with async_playwright() as p:
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
        await page.goto("https://meet.google.com/meet/abc-defg-hij", wait_until="networkidle", timeout=30000)
        
        # Check text on page
        body_text = await page.inner_text("body")
        print("Page Inner Text Summary:")
        for line in body_text.splitlines()[:20]:
            if line.strip():
                print(" >", line.strip())
                
        buttons = await page.query_selector_all("button")
        print(f"\nButtons found: {len(buttons)}")
        for b in buttons:
            txt = (await b.inner_text()).strip()
            aria = await b.get_attribute("aria-label")
            print(f" - Button: text='{txt}', aria='{aria}'")
            
        inputs = await page.query_selector_all("input")
        print(f"\nInputs found: {len(inputs)}")
        for inp in inputs:
            p_holder = await inp.get_attribute("placeholder")
            aria = await inp.get_attribute("aria-label")
            inp_type = await inp.get_attribute("type")
            print(f" - Input: type='{inp_type}', placeholder='{p_holder}', aria='{aria}'")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_meet_elements())
