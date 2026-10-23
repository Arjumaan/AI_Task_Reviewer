import asyncio
from playwright.async_api import async_playwright

async def verify_ui():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Navigating to http://localhost:5173 ...")
        await page.goto("http://localhost:5173", timeout=20000)
        await asyncio.sleep(2)
        
        # Click Assigner quick login button
        print("Clicking Assigner quick login...")
        btn = await page.query_selector('button:has-text("Assigner")')
        if btn:
            await btn.click()
            await asyncio.sleep(3)
        else:
            print("Could not find Assigner button, current URL:", page.url)

        # Select the task "AI Agentic Task Reviewer"
        task_card = await page.query_selector('h3:has-text("AI Agentic Task Reviewer")')
        if task_card:
            print("Clicking task card...")
            await task_card.click()
            await asyncio.sleep(1)

        await page.screenshot(path="poc/dashboard_verified.png")
        print("Screenshot saved to poc/dashboard_verified.png")
        
        content = await page.inner_text("body")
        print("Has 'SCHEDULED MEETINGS':", "Scheduled Meetings" in content or "SCHEDULED MEETINGS" in content)
        print("Has 'Join Google Meet':", "Join Google Meet" in content)
        print("Has 'Assigned Intern':", "Assigned Intern" in content)
        print("Snippet of body:\n", content[:600])
        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_ui())
