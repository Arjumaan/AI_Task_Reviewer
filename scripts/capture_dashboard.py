import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 800})
    page.goto('http://localhost:5173')
    page.wait_for_selector('input[type="email"]')
    page.fill('input[type="email"]', 'assigner@internal.company')
    page.fill('input[type="password"]', 'SecretPass123!')
    page.click('button[type="submit"]')
    page.wait_for_selector('text=Task Assigner Workspace')
    time.sleep(2)
    page.screenshot(path='storage/assigner_meeting_baas.png')
    print('Screenshot saved: storage/assigner_meeting_baas.png')
    browser.close()
