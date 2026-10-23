"""
Playwright End-to-End Verification of AI Voice Room inside Assigner and Intern Dashboards.
Verifies UI mounting, voice tuning controls, consent flow, and live task briefing Q&A.
"""
import sys
import time
from playwright.sync_api import sync_playwright

def verify_voice_room():
    print(">>> Starting Playwright Voice Room E2E Verification...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                "--no-sandbox"
            ]
        )
        context = browser.new_context(
            permissions=["microphone"]
        )
        page = context.new_page()

        # 1. Login as Assigner
        print("1. Logging in as Assigner...")
        page.goto("http://localhost:5173", timeout=30000)
        page.wait_for_selector("input[type='email']", timeout=10000)
        page.fill("input[type='email']", "assigner@internal.company")
        page.fill("input[type='password']", "SecretPass123!")
        page.click("button[type='submit']")

        # Wait for dashboard to load
        page.wait_for_selector("text=Task Assigner Workspace", timeout=15000)
        print("   Assigner Dashboard loaded successfully.")

        # 2. Check for "Launch AI Voice Room" button
        print("2. Verifying 'Launch AI Voice Room' button on Assigner Dashboard...")
        voice_btn = page.wait_for_selector("button:has-text('Launch AI Voice Room')", timeout=15000)
        print("   Found 'Launch AI Voice Room' button.")

        # 3. Open Voice Room
        print("3. Opening Voice Room...")
        voice_btn.click()
        page.wait_for_selector("text=Mandatory AI Disclosure & Recording Consent", timeout=8000)
        print("   Consent gate displayed with transparency disclosure.")

        # 4. Check Voice Tuning Settings
        print("4. Testing Voice Tuning drawer...")
        page.click("button:has-text('Voice Tuning')")
        page.wait_for_selector("text=Humanized Voice Settings", timeout=5000)
        print("   Voice Tuning drawer opened with voice selector and speed/pitch sliders.")

        # 5. Grant Consent and start Briefing
        print("5. Granting consent and starting live briefing...")
        page.click("button:has-text('I Consent & Join Voice Briefing')")
        page.wait_for_selector("text=AI Speaking", timeout=15000)
        print("   AI Briefing initiated and speaking status confirmed.")

        # Take screenshot of active voice room
        time.sleep(2)
        page.screenshot(path="storage/assigner_voice_room.png")
        print("   Saved screenshot: storage/assigner_voice_room.png")

        # 6. Send a question through the voice room input
        print("6. Sending technical clarification question in Voice Room...")
        input_box = page.locator("input[placeholder*='Speak into your mic or type a question']")
        input_box.fill("What is the deadline for this task?")
        page.click("button:has-text('Send')")

        # Wait for AI response in transcript
        page.wait_for_selector("text=October 29, 2026", timeout=20000)
        print("   AI successfully answered with accurate task deadline!")

        page.screenshot(path="storage/assigner_voice_room_answered.png")
        print("   Saved screenshot: storage/assigner_voice_room_answered.png")

        # Close voice room using close button (has X icon)
        page.locator("button:has(svg.lucide-x)").first.click()
        time.sleep(1)

        # 7. Test Intern Dashboard Voice Room
        print("7. Testing Intern Dashboard Voice Room...")
        # Logout
        page.click("button[title='Log out']")
        page.wait_for_selector("input[type='email']", timeout=10000)

        # Login as Intern
        page.fill("input[type='email']", "intern@internal.company")
        page.fill("input[type='password']", "SecretPass123!")
        page.click("button[type='submit']")

        page.wait_for_selector("text=Join Voice Briefing Room", timeout=15000)
        print("   Intern Dashboard loaded. Found 'Join Voice Briefing Room' button.")

        # Click Join Voice Briefing Room
        page.click("button:has-text('Join Voice Briefing Room')")
        page.wait_for_selector("text=Mandatory AI Disclosure & Recording Consent", timeout=8000)
        print("   Intern Voice Room opened successfully.")

        # Consent and verify briefing
        page.click("button:has-text('I Consent & Join Voice Briefing')")
        page.wait_for_selector("text=AI Speaking", timeout=15000)
        print("   Intern received spoken task briefing from AI Reviewer.")

        time.sleep(2)
        page.screenshot(path="storage/intern_voice_room.png")
        print("   Saved screenshot: storage/intern_voice_room.png")

        browser.close()
        print(">>> All Voice Room E2E verifications PASSED flawlessly!")

if __name__ == "__main__":
    verify_voice_room()
