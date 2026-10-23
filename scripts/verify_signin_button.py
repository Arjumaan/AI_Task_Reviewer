import asyncio
from playwright.async_api import async_playwright

async def verify():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        page = await b.new_page(viewport={"width": 1400, "height": 900})
        await page.goto("http://localhost:5173", wait_until="networkidle")
        await page.click("button:has-text('Assigner')")
        await page.wait_for_selector("text=Task Assigner Workspace", timeout=10000)
        await asyncio.sleep(2)
        btn = await page.query_selector("button:has-text('Sign in Bot to Google')")
        print("Assigner 'Sign in Bot to Google' button found:", btn is not None)
        await page.screenshot(path="storage/logs/assigner_signin_button.png")
        print("Saved screenshot to storage/logs/assigner_signin_button.png")
        await b.close()

if __name__ == "__main__":
    asyncio.run(verify())
