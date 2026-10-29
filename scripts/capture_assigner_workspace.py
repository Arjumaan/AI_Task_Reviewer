import os
import sys
from playwright.sync_api import sync_playwright

artifact_dir = r"C:\Users\Arjumaan.M\.gemini\antigravity\brain\b2a56d1d-a406-4c48-a0bf-9ad92410cfa3"

def capture():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        context = browser.new_context(viewport={"width": 1440, "height": 950})
        page = context.new_page()
        print("Logging in as Assigner...")
        page.goto("http://localhost:5173/login", wait_until="networkidle")
        page.fill('input[type="email"]', 'assigner@internal.company')
        page.fill('input[type="password"]', 'SecretPass123!')
        page.click('button[type="submit"]')
        page.wait_for_timeout(2500)

        # Click on Tasks Workspace button
        print("Navigating to Tasks Workspace...")
        page.click('text="Tasks Workspace"')
        page.wait_for_timeout(2500)

        workspace_png = os.path.join(artifact_dir, "assigner_tasks_workspace_intelligence.png")
        page.screenshot(path=workspace_png, full_page=True)
        print(f"Saved: {workspace_png}")

        browser.close()

if __name__ == "__main__":
    capture()
