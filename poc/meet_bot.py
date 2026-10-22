"""
Standalone Google Meet Bot Proof of Concept (PoC).
Identifies clearly as an AI assistant ("Task Reviewer AI (Assistant)"),
handles lobby admission, announces recording and consent disclosure,
monitors participant speech, queries local Ollama LLM, and speaks responses.
"""
import asyncio
import os
import sys
import time
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
        
        # Play into Virtual Audio Cable if available
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

    async def run(self, max_duration_sec: int = 180):
        print("=" * 60)
        print(f"LAUNCHING TASK REVIEWER AI GOOGLE MEET BOT")
        print(f"Target URL: {self.meeting_url}")
        print(f"Bot Identity: {BOT_DISPLAY_NAME}")
        print("=" * 60)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                executable_path=CHROME_PATH,
                headless=self.headless,
                args=[
                    "--use-fake-ui-for-media-stream",
                    "--autoplay-policy=no-user-gesture-required",
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox"
                ]
            )
            
            context = await browser.new_context(
                permissions=["microphone", "camera"],
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            print(f"[NAVIGATE] Loading {self.meeting_url} ...")
            await page.goto(self.meeting_url, wait_until="networkidle", timeout=45000)
            await asyncio.sleep(2)
            
            # 1. Turn off camera in lobby to conserve bandwidth
            camera_btn = await page.query_selector("button[aria-label*='camera' i], button[aria-label*='video' i]")
            if camera_btn:
                try:
                    await camera_btn.click()
                    print("[LOBBY] Turned off camera preview.")
                except Exception:
                    pass

            # 2. Enter display name if input field exists
            name_input = await page.query_selector("input[type='text'], input[placeholder*='name' i]")
            if name_input:
                await name_input.fill(BOT_DISPLAY_NAME)
                print(f"[LOBBY] Set display name: '{BOT_DISPLAY_NAME}'")
                await asyncio.sleep(1)

            # 3. Click 'Ask to join' or 'Join now'
            join_btn = await page.query_selector("button:has-text('Ask to join'), button:has-text('Join now')")
            if join_btn:
                await join_btn.click()
                print("[LOBBY] Clicked 'Ask to join' / 'Join now'. Awaiting host admission...")
            else:
                print("[LOBBY WARNING] Join button not immediately found; checking page state...")

            # 4. Wait for in-call state (look for end-call button or participant panel)
            start_time = time.time()
            in_call = False
            
            while time.time() - start_time < 60:
                end_call_btn = await page.query_selector("button[aria-label*='leave' i], button[aria-label*='end' i]")
                if end_call_btn:
                    in_call = True
                    self.is_in_call = True
                    print("\n" + "=" * 60)
                    print("[IN-CALL] Bot successfully ADMITTED into the Google Meet session!")
                    print("=" * 60)
                    break
                await asyncio.sleep(3)
                print("[LOBBY] Waiting for host admission...")

            if not in_call:
                print("[TIMEOUT / BLOCKED] Bot was not admitted within 60 seconds.")
                screenshot_path = Path("poc") / "meet_lobby_timeout.png"
                await page.screenshot(path=str(screenshot_path))
                print(f"Saved diagnosis screenshot to: {screenshot_path.resolve()}")
                await browser.close()
                return False

            # 5. In-call: Turn on Closed Captions for real-time participant transcription
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

            # 8. Meeting loop: listen for captions/speech and process
            call_start = time.time()
            print("[IN-CALL] Active listening loop running...")
            
            while time.time() - call_start < max_duration_sec:
                # Check if meeting has ended
                end_call_btn = await page.query_selector("button[aria-label*='leave' i], button[aria-label*='end' i]")
                if not end_call_btn:
                    print("[IN-CALL] Meeting ended by host or call disconnected.")
                    break
                    
                # Inspect live captions
                caption_nodes = await page.query_selector_all(".iTTPOb, [aria-live='polite'] span")
                for node in caption_nodes:
                    text = (await node.inner_text()).strip()
                    if text and text not in self.transcripts:
                        self.transcripts.append(text)
                        print(f"\n[PARTICIPANT SPEECH]: {text}")
                        # If a question or statement is directed to the bot
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
                    
            await browser.close()
            print("[SUCCESS] Google Meet Bot session completed successfully!")
            return True

if __name__ == "__main__":
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://meet.google.com/abc-defg-hij"
    bot = GoogleMeetBot(meeting_url=test_url, headless=False)
    asyncio.run(bot.run(max_duration_sec=30))
