import asyncio
from playwright.async_api import async_playwright

async def check():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        page = await b.new_page(viewport={"width": 1400, "height": 900})
        page.on("pageerror", lambda err: print("[BROWSER ERROR]:", err))
        page.on("console", lambda msg: print("[BROWSER CONSOLE]:", msg.text))
        
        await page.goto("http://localhost:5173")
        await page.click("button:has-text('Admin')")
        await page.wait_for_selector("text=Task Assigner Workspace")
        print("Logged in as Admin.")
        
        await page.click("button:has-text('System')")
        await asyncio.sleep(2)
        await b.close()

if __name__ == "__main__":
    asyncio.run(check())
