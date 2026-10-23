import asyncio
from playwright.async_api import async_playwright

async def verify():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})

        print("1. Testing Intern Role (Aarav Sharma)...")
        await page.goto("http://localhost:5173", wait_until="networkidle")
        await page.click("button:has-text('Aarav Sharma')")
        await page.wait_for_selector("text=Intern Learning & Review Hub", timeout=10000)
        await asyncio.sleep(2)

        intern_signin_btn = await page.query_selector("button:has-text('Sign in Bot to Google')")
        print("Intern view has 'Sign in Bot to Google':", intern_signin_btn is not None)
        assert intern_signin_btn is None, "ERROR: Intern view should NOT have 'Sign in Bot to Google' button!"
        await page.screenshot(path="storage/logs/intern_no_google_btn.png")
        print("PASS: Intern view correctly DOES NOT have 'Sign in Bot to Google'.")

        # Logout
        await page.click("button[title='Log out']")
        await asyncio.sleep(2)

        print("\n2. Testing Assigner Role...")
        await page.click("button:has-text('Assigner')")
        await page.wait_for_selector("text=Task Assigner Workspace", timeout=10000)
        await asyncio.sleep(2)

        assigner_signin_btn = await page.query_selector("button:has-text('Sign in Bot to Google')")
        print("Assigner view has 'Sign in Bot to Google':", assigner_signin_btn is not None)
        assert assigner_signin_btn is not None, "ERROR: Assigner view MUST have 'Sign in Bot to Google' button!"
        await page.screenshot(path="storage/logs/assigner_has_google_btn.png")
        print("PASS: Assigner view correctly HAS 'Sign in Bot to Google'.")

        # Logout
        await page.click("button[title='Log out']")
        await asyncio.sleep(2)

        print("\n3. Testing Admin Role (System & Benchmarks)...")
        await page.click("button:has-text('Admin')")
        await page.wait_for_selector("text=Task Assigner Workspace", timeout=10000)
        await asyncio.sleep(1)
        # Click System & Benchmarks tab in navbar
        system_tab = await page.wait_for_selector("button:has-text('System')", timeout=10000)
        await system_tab.click()
        await page.wait_for_selector("text=Google Meet AI Bot Authentication", timeout=10000)
        await asyncio.sleep(2)

        admin_signin_btn = await page.query_selector("button:has-text('Sign in Bot to Google')")
        print("Admin view has 'Sign in Bot to Google':", admin_signin_btn is not None)
        assert admin_signin_btn is not None, "ERROR: Admin view MUST have 'Sign in Bot to Google' button!"
        await page.screenshot(path="storage/logs/admin_has_google_btn.png")
        print("PASS: Admin view correctly HAS 'Sign in Bot to Google'.")

        await browser.close()
        print("\nALL ROLE VISIBILITY CHECKS PASSED 100%!")

if __name__ == "__main__":
    asyncio.run(verify())
