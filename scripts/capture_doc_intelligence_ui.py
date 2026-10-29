import os
import sys
from playwright.sync_api import sync_playwright

artifact_dir = r"C:\Users\Arjumaan.M\.gemini\antigravity\brain\b2a56d1d-a406-4c48-a0bf-9ad92410cfa3"

def capture():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. Assigner
        context1 = browser.new_context(viewport={"width": 1440, "height": 950})
        page1 = context1.new_page()
        print("Logging in as Assigner...")
        page1.goto("http://localhost:5173/login", wait_until="networkidle")
        page1.fill('input[type="email"]', 'assigner@internal.company')
        page1.fill('input[type="password"]', 'SecretPass123!')
        page1.click('button[type="submit"]')
        page1.wait_for_timeout(3000)

        assigner_png = os.path.join(artifact_dir, "assigner_document_intelligence.png")
        page1.screenshot(path=assigner_png, full_page=True)
        print(f"Saved: {assigner_png}")
        context1.close()

        # 2. Intern
        context2 = browser.new_context(viewport={"width": 1440, "height": 950})
        page2 = context2.new_page()
        print("Logging in as Intern...")
        page2.goto("http://localhost:5173/login", wait_until="networkidle")
        page2.fill('input[type="email"]', 'intern@internal.company')
        page2.fill('input[type="password"]', 'SecretPass123!')
        page2.click('button[type="submit"]')
        page2.wait_for_timeout(3000)

        intern_png = os.path.join(artifact_dir, "intern_document_intelligence.png")
        page2.screenshot(path=intern_png, full_page=True)
        print(f"Saved: {intern_png}")
        context2.close()

        browser.close()

if __name__ == "__main__":
    capture()
