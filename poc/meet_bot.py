"""
Standalone Google Meet Bot Proof of Concept (PoC).
Identifies clearly as an AI assistant ("Task Reviewer AI (Assistant)"),
handles lobby admission, announces recording and consent disclosure,
monitors participant speech, queries local Ollama LLM, and speaks responses.
Uses authentic Google Chrome with native-login capability to prevent 'browser not secure' blocks.
"""
import asyncio
import os
import sys
import time
import shutil
import tempfile
import sqlite3
import subprocess
from pathlib import Path
from typing import Optional
import httpx
from playwright.async_api import async_playwright, Page, BrowserContext
import pyttsx3
import sounddevice as sd
import soundfile as sf

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OLLAMA_API_URL = "http://127.0.0.1:11434/api/generate"
BOT_DISPLAY_NAME = "Task Reviewer AI (Assistant)"

DISCLOSURE_SPEECH = (
    "Hello everyone. I am the Task Reviewer AI assistant. "
    "This session is being recorded and transcribed for task briefing and review evaluation. "
    "Please confirm your consent, and we may begin."
)

def check_is_google_authenticated_sqlite() -> bool:
    """Checks if the persistent Chrome profile contains authenticated Google session cookies."""
    cookies_path = os.path.abspath("storage/bot_browser_profile/Default/Network/Cookies")
    if not os.path.exists(cookies_path):
        return False
    tmp_path = os.path.join(tempfile.gettempdir(), f"cookie_chk_{int(time.time()*1000)}.db")
    try:
        shutil.copy2(cookies_path, tmp_path)
        conn = sqlite3.connect(tmp_path)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM cookies WHERE name IN ('SID', 'SSID') AND host_key LIKE '%google.com%' LIMIT 1")
        row = cur.fetchone()
        conn.close()
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        return row is not None
    except PermissionError:
        # Chrome has exclusive lock on Cookies file while running on Windows
        return False
    except Exception:
        return False

async def async_interactive_google_login(continue_url: str = "https://meet.google.com") -> bool:
    """
    Opens an interactive Google Chrome window directly to Google Sign-In,
    monitoring live session tokens without hitting Windows file-locking issues.
    """
    profile_dir = Path("storage/bot_browser_profile").resolve()
    profile_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 65)
    print("[CHROME SIGN-IN] OPENING GOOGLE SIGN-IN WINDOW")
    print("=" * 65)
    print("Please enter your Google account email & password in the Chrome window.")
    print("Once authenticated, your session is saved permanently for all future meetings.")
    print("=" * 65 + "\n")

    chrome_exec = CHROME_PATH if os.path.exists(CHROME_PATH) else None

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            executable_path=chrome_exec,
            headless=False,
            viewport={"width": 1024, "height": 720},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ],
            ignore_default_args=["--enable-automation"]
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(f"https://accounts.google.com/signin/v2/identifier?continue={continue_url}", wait_until="domcontentloaded")
        
        print("[AUTH] Waiting for Google sign-in completion (timeout: 300s)...")
        start = time.time()
        while time.time() - start < 300:
            await asyncio.sleep(2)
            curr = page.url
            if ("myaccount.google.com" in curr or "meet.google.com" in curr) and "signin" not in curr:
                print("\n[AUTH SUCCESS] Detected Google Account login!")
                await asyncio.sleep(2)
                await context.close()
                return True
            cookies = await context.cookies()
            if any(c["name"] in ("SID", "SSID", "SAPISID") and "google.com" in c["domain"] for c in cookies):
                print("\n[AUTH SUCCESS] Google authentication cookies saved!")
                await asyncio.sleep(2)
                await context.close()
                return True

        print("[AUTH TIMEOUT] Sign-in not completed within 300 seconds.")
        await context.close()
        return False

def launch_native_chrome_login(continue_url: str = "https://meet.google.com") -> bool:
    return asyncio.run(async_interactive_google_login(continue_url=continue_url))

class GoogleMeetBot:
    def __init__(self, meeting_url: str, task_context: str = "", headless: bool = False):
        self.meeting_url = meeting_url
        self.task_context = task_context or "General task briefing and rubric review."
        self.headless = headless
        self.is_in_call = False
        self.transcripts = []
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 165)
        
    def speak_audio(self, text: str, output_device_name: str = "Virtual Audio Cable"):
        """Synthesizes text and plays it into the Virtual Audio Cable output (or default)."""
        print(f"[BOT TTS] Speaking: \"{text}\"")
        out_wav = Path("poc") / "temp_bot_speech.wav"
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        
        self.tts_engine.save_to_file(text, str(out_wav))
        self.tts_engine.runAndWait()
        
        try:
            data, sr = sf.read(str(out_wav))
            dev_idx = None
            for i, dev in enumerate(sd.query_devices()):
                if output_device_name.lower() in dev["name"].lower() and dev["max_output_channels"] > 0:
                    dev_idx = i
                    break
            
            if dev_idx is not None:
                print(f"[BOT AUDIO] Injecting audio into Virtual Output device [{dev_idx}]...")
                sd.play(data, sr, device=dev_idx)
                sd.wait()
            else:
                print("[BOT AUDIO] Playing to default audio output...")
                sd.play(data, sr)
                sd.wait()
        except Exception as e:
            print(f"[BOT AUDIO WARNING] Audio playback exception: {e}")

    async def query_local_llm(self, prompt: str) -> str:
        """Queries local Ollama instance for a context-aware answer."""
        system_prompt = (
            f"You are the Task Reviewer AI Assistant. Context: {self.task_context}. "
            "Respond concisely in 1-2 spoken sentences. Be professional, clear, and direct. "
            "Never pretend to be a human employee. State you are an AI task reviewer."
        )
        payload = {
            "model": "llama3.2:1b",
            "prompt": f"{system_prompt}\nParticipant said: {prompt}\nAI Response:",
            "stream": False
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(OLLAMA_API_URL, json=payload)
                if res.status_code == 200:
                    return res.json().get("response", "").strip()
        except Exception as err:
            print(f"[LLM WARNING] Ollama query failed ({err}). Using rule-based response.")
            
        return (
            "I noted your question. I am reviewing the deliverables against the approved acceptance criteria."
        )

    async def run(self, max_duration_sec: int = 300):
        # Normalize meeting URL
        clean_url = self.meeting_url.strip()
        if not clean_url.startswith("http"):
            if "meet.google.com" in clean_url:
                clean_url = "https://" + clean_url
            else:
                clean_url = f"https://meet.google.com/{clean_url}"
        self.meeting_url = clean_url

        print("=" * 60)
        print("LAUNCHING TASK REVIEWER AI GOOGLE MEET BOT")
        print(f"Target URL: {self.meeting_url}")
        print(f"Bot Identity: {BOT_DISPLAY_NAME}")
        print("=" * 60)
        
        # Check Google Account authentication state
        is_authed = check_is_google_authenticated_sqlite()
        if is_authed:
            print("[AUTH] Google Account session detected. Joining with authenticated identity.")
        else:
            print(f"[AUTH] Unauthenticated guest mode. Bot will join directly or knock as '{BOT_DISPLAY_NAME}'.")

        # Clean up any orphaned background processes on the bot profile
        ps_cmd = "Get-CimInstance Win32_Process -Filter \"name = 'chrome.exe'\" | Where-Object { $_.CommandLine -like '*bot_browser_profile*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
            time.sleep(1)
        except Exception:
            pass

        profile_dir = Path("storage/bot_browser_profile").resolve()
        profile_dir.mkdir(parents=True, exist_ok=True)

        async with async_playwright() as p:
            launch_args = [
                "--use-fake-ui-for-media-stream",
                "--autoplay-policy=no-user-gesture-required",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
            
            chrome_exec = CHROME_PATH if os.path.exists(CHROME_PATH) else None
            if chrome_exec:
                print(f"[BROWSER] Using authentic Google Chrome ({chrome_exec})...")
            else:
                print("[BROWSER] Chrome not found at default path, launching bundled Chromium...")

            print(f"[BROWSER] Launching persistent browser session ({profile_dir})...")
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                executable_path=chrome_exec,
                headless=self.headless,
                viewport={"width": 1280, "height": 720},
                permissions=["microphone", "camera"],
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                ignore_default_args=["--enable-automation"],
                args=launch_args
            )
            # Remove navigator.webdriver automation indicator
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            page = context.pages[0] if context.pages else await context.new_page()
            print(f"[NAVIGATE] Loading {self.meeting_url} ...")
            await page.goto(self.meeting_url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(4)

            # Check if blocked by Google Meet (requires Google Account sign-in)
            body_text = await page.evaluate("() => document.body.innerText")
            if "You can't join this video call" in body_text:
                print("\n" + "!" * 70)
                print("[GOOGLE MEET REQUIRES GOOGLE ACCOUNT AUTHENTICATION]")
                print("!" * 70)
                print("Google Meet blocked unauthenticated guest entry on this meeting link.")
                print("Google's security policy requires participants to be signed into Google.")
                print("")
                print("WHY YOU CANNOT SIGN IN INSIDE THIS AUTOMATED WINDOW:")
                print("Google actively detects automated browser sessions (Playwright/CDP) on")
                print("accounts.google.com and blocks sign-in with:")
                print("  'This browser or app may not be secure. Learn more. Try using a different browser.'")
                print("")
                print("👉 SOLUTION (Takes 30 seconds):")
                print("Authenticate your bot profile ONCE using our native Chrome launcher:")
                print("    .venv\\Scripts\\python poc/sign_in_google.py")
                print("")
                print("Once signed in, re-run this bot command and it will enter immediately!")
                print("!" * 70 + "\n")
                await page.screenshot(path="storage/logs/meet_restricted_block.png")
                await context.close()
                return False

            # Dismiss microphone/camera setup prompts if present
            for sel in [
                "button:has-text('Continue without microphone and camera')",
                "button:has-text('Continue without microphone')",
                "button:has-text('Continue without camera')",
                "button:has-text('Dismiss')",
                "button[aria-label*='dismiss' i]",
                "button[jsname='IbE0S']"
            ]:
                btn = await page.query_selector(sel)
                if btn:
                    try:
                        await btn.click()
                        print(f"[LOBBY] Dismissed media prompt ({sel}).")
                        await asyncio.sleep(1)
                    except Exception:
                        pass
            
            # 1. Turn off camera in lobby
            camera_btn = await page.query_selector("button[aria-label*='camera' i], button[aria-label*='video' i]")
            if camera_btn:
                try:
                    await camera_btn.click()
                    print("[LOBBY] Turned off camera preview.")
                except Exception:
                    pass

            # 2. Enter display name if input field exists
            name_input = await page.query_selector("input[type='text'], input[placeholder*='name' i], input[aria-label*='name' i]")
            if name_input and await name_input.is_visible():
                await name_input.fill(BOT_DISPLAY_NAME)
                print(f"[LOBBY] Set display name: '{BOT_DISPLAY_NAME}'")
                await asyncio.sleep(1)

            # 3. Detect "Join now" (Open call) vs "Ask to join" (Admission required)
            join_type = None # "DIRECT" or "KNOCK"
            
            candidate_buttons = await page.query_selector_all("button, div[role='button']")
            for btn in candidate_buttons:
                if not await btn.is_visible():
                    continue
                txt = (await btn.inner_text()).strip().lower()
                lines = [line.strip().lower() for line in txt.split("\n")]
                
                if "join now" in lines or txt == "join now":
                    print(f"[LOBBY] Open meeting detected! Clicking 'Join now' to enter directly...")
                    await btn.click()
                    join_type = "DIRECT"
                    break
                elif "ask to join" in lines or txt == "ask to join":
                    print(f"[LOBBY] Host admission required! Clicking 'Ask to join'...")
                    await btn.click()
                    join_type = "KNOCK"
                    break

            if not join_type:
                primary_btn = await page.query_selector("button[jsname='Qx7uuf'], button[data-idom-class*='q7vyEf']")
                if primary_btn and await primary_btn.is_visible():
                    btn_text = (await primary_btn.inner_text()).strip()
                    if "join now" in btn_text.lower():
                        print(f"[LOBBY] Primary button says '{btn_text}'. Joining directly...")
                        join_type = "DIRECT"
                        await primary_btn.click()
                    elif ("ask to join" in btn_text.lower() or "join" in btn_text.lower()) and "return" not in btn_text.lower() and "home" not in btn_text.lower():
                        print(f"[LOBBY] Primary button says '{btn_text}'. Knocking for admission...")
                        join_type = "KNOCK"
                        await primary_btn.click()

            if not join_type:
                print("[LOBBY WARNING] Pre-join button not found yet; checking if already inside call or waiting...")

            # 4. Wait for in-call state
            start_time = time.time()
            in_call = False
            max_wait_seconds = 20 if join_type == "DIRECT" else 180
            
            print(f"[LOBBY] Monitoring call state (max wait: {max_wait_seconds}s)...")
            while time.time() - start_time < max_wait_seconds:
                body = await page.evaluate("() => document.body.innerText")
                if "You can't join this video call" in body:
                    print("\n" + "!" * 70)
                    print("[LOBBY BLOCKED] Google Meet restricted access ('You can't join this video call').")
                    print("Google requires an authenticated Google Account for this call.")
                    print("Please run native Chrome sign-in once: .venv\\Scripts\\python poc/sign_in_google.py")
                    print("!" * 70 + "\n")
                    await page.screenshot(path="storage/logs/meet_restricted_block.png")
                    await context.close()
                    return False

                end_call_btn = await page.query_selector("button[aria-label*='leave' i], button[aria-label*='end' i], button[jsname='CQyBDb']")
                if end_call_btn and await end_call_btn.is_visible():
                    in_call = True
                    self.is_in_call = True
                    if join_type == "DIRECT":
                        print("\n" + "=" * 60)
                        print("[IN-CALL] DIRECT JOIN SUCCESSFUL! Bot is now inside the meeting.")
                        print("=" * 60)
                    else:
                        print("\n" + "=" * 60)
                        print("[IN-CALL] ADMISSION CONFIRMED! Host admitted the bot into the meeting.")
                        print("=" * 60)
                    break

                if not join_type:
                    candidate_buttons = await page.query_selector_all("button, div[role='button']")
                    for b in candidate_buttons:
                        if await b.is_visible():
                            txt = (await b.inner_text()).strip().lower()
                            if "join now" in txt:
                                join_type = "DIRECT"
                                print("[LOBBY] Found & clicked 'Join now' directly...")
                                await b.click()
                                break
                            elif "ask to join" in txt:
                                join_type = "KNOCK"
                                print("[LOBBY] Found & clicked 'Ask to join'. Waiting for host admission...")
                                await b.click()
                                break

                await asyncio.sleep(4)
                if join_type == "KNOCK":
                    print("[LOBBY] Waiting for host admission popup to be accepted by meeting host...")
                else:
                    print("[LOBBY] Connecting to meeting audio and video streams...")

            if not in_call:
                print(f"[TIMEOUT] Bot was not in-call within {max_wait_seconds} seconds.")
                screenshot_path = Path("poc") / "meet_lobby_timeout.png"
                await page.screenshot(path=str(screenshot_path))
                print(f"Saved diagnosis screenshot to: {screenshot_path.resolve()}")
                await context.close()
                return False

            # 5. In-call: Turn on Closed Captions
            try:
                caption_btn = await page.query_selector("button[aria-label*='caption' i]")
                if caption_btn:
                    await caption_btn.click()
                    print("[IN-CALL] Enabled Google Meet real-time Closed Captions.")
                else:
                    await page.keyboard.press("c")
                    print("[IN-CALL] Toggled captions via shortcut 'c'.")
            except Exception as e:
                print(f"[IN-CALL WARNING] Could not enable captions: {e}")

            # 6. Post in-chat disclosure
            try:
                chat_btn = await page.query_selector("button[aria-label*='chat' i]")
                if chat_btn:
                    await chat_btn.click()
                    await asyncio.sleep(1)
                    chat_input = await page.query_selector("textarea[aria-label*='message' i]")
                    if chat_input:
                        disclosure_msg = (
                            f"[AI NOTICE]: I am the {BOT_DISPLAY_NAME}. "
                            "This session is recorded and transcribed for evaluation purposes."
                        )
                        await chat_input.fill(disclosure_msg)
                        await page.keyboard.press("Enter")
                        print("[IN-CALL] Sent text disclosure message to meeting chat.")
            except Exception as e:
                print(f"[IN-CALL WARNING] Chat disclosure failed: {e}")

            # 7. Announce via voice
            self.speak_audio(DISCLOSURE_SPEECH)

            # 8. Active loop
            call_start = time.time()
            print("[IN-CALL] Active listening loop running...")
            
            while time.time() - call_start < max_duration_sec:
                end_call_btn = await page.query_selector("button[aria-label*='leave' i], button[aria-label*='end' i]")
                if not end_call_btn:
                    print("[IN-CALL] Meeting ended by host or call disconnected.")
                    break
                    
                caption_nodes = await page.query_selector_all(".iTTPOb, [aria-live='polite'] span")
                for node in caption_nodes:
                    text = (await node.inner_text()).strip()
                    if text and text not in self.transcripts:
                        self.transcripts.append(text)
                        print(f"\n[PARTICIPANT SPEECH]: {text}")
                        if any(w in text.lower() for w in ["ai", "reviewer", "explain", "deadline", "criteria", "task"]):
                            response = await self.query_local_llm(text)
                            self.speak_audio(response)
                            
                await asyncio.sleep(2)
                
            print("[IN-CALL] Meeting duration completed. Leaving meeting cleanly...")
            if end_call_btn:
                try:
                    await end_call_btn.click()
                except Exception:
                    pass
                    
            await context.close()
            print("[SUCCESS] Google Meet Bot session completed successfully!")
            return True

if __name__ == "__main__":
    if "--login" in sys.argv:
        from poc.sign_in_google import main as sign_in_main
        sign_in_main()
        sys.exit(0)

    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        test_url = sys.argv[1]
    else:
        print("\n" + "=" * 60)
        print("GOOGLE MEET AI AGENT LAUNCHER")
        print("=" * 60)
        user_input = input("Enter Google Meet link or code [default: rqp-ctfg-nri]: ").strip()
        test_url = user_input if user_input else "https://meet.google.com/rqp-ctfg-nri"

    bot = GoogleMeetBot(meeting_url=test_url, headless=False)
    asyncio.run(bot.run(max_duration_sec=300))
