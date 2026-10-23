import asyncio
from playwright.async_api import async_playwright

async def inspect_meet_lobby(meet_url: str):
    async with async_playwright() as p:
        # Launch Chrome directly with audio/video disabled
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--use-fake-ui-for-media-stream",
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
        print(f"Navigating to {meet_url} ...")
        await page.goto(meet_url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(4)

        title = await page.title()
        print(f"Page Title: {title}")
        url = page.url
        print(f"Current URL: {url}")

        # Check body text
        body_text = await page.evaluate("() => document.body.innerText")
        lines = [line.strip() for line in body_text.split("\n") if line.strip()]
        print(f"Visible text snippet ({len(lines)} lines):")
        for line in lines[:15]:
            print(f"  {line}")

        # Check for name input field
        name_inputs = await page.query_selector_all("input[type='text'], input[placeholder*='name' i], input[aria-label*='name' i]")
        print(f"Name inputs found: {len(name_inputs)}")

        # Check for Join / Ask to join buttons
        join_btns = await page.query_selector_all("button:has-text('Join now'), button:has-text('Ask to join')")
        print(f"Join / Ask to join buttons found: {len(join_btns)}")
        for b in join_btns:
            print(f"  Button text: {await b.inner_text()}")

        # Take screenshot
        await page.screenshot(path="storage/logs/guest_lobby_test.png")
        print("Saved screenshot to storage/logs/guest_lobby_test.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_meet_lobby("https://meet.google.com/rqp-ctfg-nri"))
