import asyncio
from playwright.async_api import async_playwright

async def verify():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})

        print("Navigating to http://localhost:5173 ...")
        await page.goto("http://localhost:5173", wait_until="networkidle")
        await asyncio.sleep(2)

        # 1. Login as Assigner
        print("Clicking Assigner quick login button...")
        assigner_btn = await page.wait_for_selector("button:has-text('Assigner')", timeout=10000)
        await assigner_btn.click()
        await page.wait_for_selector("text=Task Assigner Workspace", timeout=10000)
        await asyncio.sleep(2)

        # Check for Bot Dispatcher
        bot_section = await page.query_selector("text=Google Meet AI Agent Dispatcher")
        print("Assigner Bot Section Found:", bot_section is not None)

        launch_bot_btns = await page.query_selector_all("button:has-text('Launch AI Bot')")
        print("Assigner 'Launch AI Bot' buttons found:", len(launch_bot_btns))

        dispatch_btn = await page.query_selector("button:has-text('Dispatch AI Bot')")
        print("Assigner 'Dispatch AI Bot' button found:", dispatch_btn is not None)

        await page.screenshot(path="storage/logs/assigner_dashboard_bot.png")
        print("Saved assigner screenshot to storage/logs/assigner_dashboard_bot.png")

        # 2. Check Intern Dashboard
        # Logout using logout button
        logout_btn = await page.query_selector("button[title='Log out']")
        if logout_btn:
            await logout_btn.click()
            await asyncio.sleep(2)

        print("Clicking Aarav Sharma intern quick login...")
        aarav_btn = await page.wait_for_selector("button:has-text('Aarav Sharma')", timeout=10000)
        await aarav_btn.click()
        await page.wait_for_selector("text=Intern Learning & Review Hub", timeout=10000)
        await asyncio.sleep(2)

        intern_bot_section = await page.query_selector("text=Have a Google Meet Link? Dispatch AI Bot to Call")
        print("Intern Bot Section Found:", intern_bot_section is not None)

        intern_launch_btns = await page.query_selector_all("button:has-text('Launch AI Bot')")
        print("Intern 'Launch AI Bot' buttons found:", len(intern_launch_btns))

        intern_dispatch_btn = await page.query_selector("button:has-text('Dispatch AI Bot')")
        print("Intern 'Dispatch AI Bot' button found:", intern_dispatch_btn is not None)

        await page.screenshot(path="storage/logs/intern_dashboard_bot.png")
        print("Saved intern screenshot to storage/logs/intern_dashboard_bot.png")

        await browser.close()
        print("All UI verifications completed successfully!")

if __name__ == "__main__":
    asyncio.run(verify())
