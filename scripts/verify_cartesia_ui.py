import time
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', '--no-sandbox']
        )
        context = browser.new_context(permissions=['microphone'])
        page = context.new_page()

        # 1. Login as Assigner
        print('1. Logging in as Assigner...')
        page.goto('http://localhost:5173', timeout=30000)
        page.wait_for_selector('input[type="email"]', timeout=10000)
        page.fill('input[type="email"]', 'assigner@internal.company')
        page.fill('input[type="password"]', 'SecretPass123!')
        page.click('button[type="submit"]')

        # Wait for dashboard
        page.wait_for_selector('text=Task Assigner Workspace', timeout=15000)
        print('   Assigner Dashboard loaded.')

        # 2. Open Voice Room
        voice_btn = page.wait_for_selector('button:has-text("Launch AI Voice Room")', timeout=15000)
        voice_btn.click()
        page.wait_for_selector('text=Mandatory AI Disclosure', timeout=8000)
        print('   Consent modal opened.')

        # 3. Open Voice Tuning Drawer to check Subha Cartesia badge
        page.click('button:has-text("Voice Tuning")')
        page.wait_for_selector('text=Active Neural Voice', timeout=5000)
        print('   Voice Tuning opened with Subha Cartesia Neural settings.')
        time.sleep(1)
        page.screenshot(path='storage/voice_room_cartesia_tuning.png')

        # 4. Consent and launch briefing
        page.click('button:has-text("Join Voice Briefing")')
        page.wait_for_selector('text=Subha (Cartesia Neural)', timeout=15000)
        print('   Subha (Cartesia Neural) voice active in header.')
        time.sleep(4)
        page.screenshot(path='storage/voice_room_cartesia_active.png')

        browser.close()
        print('>>> Cartesia Voice UI captured successfully!')

if __name__ == '__main__':
    run()
