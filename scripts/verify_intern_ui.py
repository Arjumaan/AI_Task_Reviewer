import asyncio
from playwright.async_api import async_playwright

async def verify_intern_ui():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("http://localhost:5173", timeout=20000)
        await asyncio.sleep(2)
        
        # Click Intern quick login button for Aarav Sharma
        print("Clicking Intern quick login...")
        btn = await page.query_selector('button:has-text("Aarav Sharma")')
        if not btn:
            btn = await page.query_selector('button:has-text("Intern")')
        if btn:
            await btn.click()
            await asyncio.sleep(3)

        # Select the task "AI Agentic Task Reviewer"
        task_card = await page.query_selector('h3:has-text("AI Agentic Task Reviewer")')
        if task_card:
            print("Clicking task card in intern view...")
            await task_card.click()
            await asyncio.sleep(1)

        await page.screenshot(path="poc/intern_dashboard_verified.png")
        print("Intern screenshot saved to poc/intern_dashboard_verified.png")
        
        content = await page.inner_text("body")
        print("Intern view has 'Scheduled Review & Briefing Sessions':", "Scheduled Review & Briefing Sessions" in content)
        print("Intern view has 'Join Google Meet':", "Join Google Meet" in content)
        print("Intern view has 'Deliver Task Submission':", "Deliver Task Submission" in content)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_intern_ui())
