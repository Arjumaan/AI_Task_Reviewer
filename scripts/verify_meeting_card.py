import asyncio
from playwright.async_api import async_playwright

async def verify_meeting_card():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})

        await page.goto("http://localhost:5173", wait_until="networkidle")
        await asyncio.sleep(1)

        # Login as Assigner
        assigner_btn = await page.wait_for_selector("button:has-text('Assigner')", timeout=10000)
        await assigner_btn.click()
        await page.wait_for_selector("text=Task Assigner Workspace", timeout=10000)
        await asyncio.sleep(2)

        # Find the task that has the meeting
        tasks = await page.query_selector_all("div[class*='cursor-pointer']")
        for t in tasks:
            txt = await t.inner_text()
            if "FastAPI" in txt or "Distributed" in txt or "Task" in txt:
                await t.click()
                await asyncio.sleep(1)
                launch_btns = await page.query_selector_all("button:has-text('Launch AI Bot')")
                if len(launch_btns) > 0:
                    print(f"Found task with meeting! 'Launch AI Bot' buttons: {len(launch_btns)}")
                    await page.screenshot(path="storage/logs/task_with_meeting_bot.png")
                    print("Saved screenshot to storage/logs/task_with_meeting_bot.png")
                    break

        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_meeting_card())
