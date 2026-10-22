"""
Local Web Voice Room Fallback Server.
Provides an interactive, zero-cloud browser voice room for task briefing and review
when external Google Meet sessions are unavailable or blocked by domain policies.
Includes AI identification, recording consent gate, real-time audio interaction,
and live transcript display.
"""
import asyncio
import json
import os
import time
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import pyttsx3
import uvicorn
import httpx

app = FastAPI(title="Task Reviewer Local Voice Room")

VOICE_ROOM_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Task Reviewer AI — Interactive Voice Room</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .pulse-active { animation: pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: .5; } }
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col items-center justify-center p-4">
    <div class="max-w-3xl w-full bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl">
        <!-- Header -->
        <div class="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center font-bold text-lg">AI</div>
                <div>
                    <h1 class="text-xl font-bold text-white">Task Reviewer AI — Voice Room</h1>
                    <p class="text-xs text-slate-400">Identified as: <span class="text-indigo-400 font-semibold">Autonomous Task Reviewer AI</span> (Internal Tool)</p>
                </div>
            </div>
            <div id="connectionStatus" class="px-3 py-1 text-xs rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">Connecting...</div>
        </div>

        <!-- Consent Gate Banner -->
        <div id="consentBanner" class="bg-amber-950/40 border border-amber-800/60 rounded-xl p-4 mb-6">
            <div class="flex items-start gap-3">
                <span class="text-xl">⚠️</span>
                <div>
                    <h3 class="text-sm font-semibold text-amber-300">Mandatory AI & Recording Disclosure</h3>
                    <p class="text-xs text-amber-200/80 mt-1">
                        You are interacting with an autonomous AI Reviewer. This session will be recorded and transcribed for evaluation against approved criteria. No human impersonation is performed.
                    </p>
                    <button id="consentBtn" class="mt-3 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow transition">
                        I Understand & Consent to Recording
                    </button>
                </div>
            </div>
        </div>

        <!-- Room Controls & Audio Visualizer -->
        <div id="roomControls" class="hidden space-y-6">
            <div class="bg-slate-950 border border-slate-800 rounded-xl p-4 flex flex-col items-center">
                <div class="text-xs font-medium text-slate-400 mb-2" id="speakingIndicator">AI Reviewer is Ready</div>
                <div class="w-full h-16 bg-slate-900 rounded-lg flex items-center justify-center gap-1 px-4 overflow-hidden" id="visualizer">
                    <!-- Audio bars -->
                    <div class="w-1.5 h-4 bg-indigo-500 rounded-full transition-all duration-75"></div>
                    <div class="w-1.5 h-8 bg-indigo-500 rounded-full transition-all duration-75"></div>
                    <div class="w-1.5 h-12 bg-indigo-500 rounded-full transition-all duration-75"></div>
                    <div class="w-1.5 h-6 bg-indigo-500 rounded-full transition-all duration-75"></div>
                    <div class="w-1.5 h-10 bg-indigo-500 rounded-full transition-all duration-75"></div>
                </div>
                
                <div class="flex items-center gap-4 mt-4">
                    <button id="micBtn" class="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-sm font-medium flex items-center gap-2 border border-slate-700 transition">
                        <span id="micIcon">🎙️</span> <span id="micText">Hold / Click to Speak</span>
                    </button>
                    <button id="briefingBtn" class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition shadow">
                        Request Task Briefing
                    </button>
                </div>
            </div>

            <!-- Live Transcript Log -->
            <div>
                <h3 class="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Live Transcript Stream</h3>
                <div id="transcriptBox" class="h-64 bg-slate-950 border border-slate-800 rounded-xl p-4 overflow-y-auto space-y-3 font-mono text-xs">
                    <div class="text-slate-500 italic">[Session initialized. Waiting for participant consent...]</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let ws;
        let isConsented = false;
        let isListening = false;
        let recognition;

        const consentBanner = document.getElementById('consentBanner');
        const consentBtn = document.getElementById('consentBtn');
        const roomControls = document.getElementById('roomControls');
        const transcriptBox = document.getElementById('transcriptBox');
        const connectionStatus = document.getElementById('connectionStatus');
        const micBtn = document.getElementById('micBtn');
        const micText = document.getElementById('micText');
        const briefingBtn = document.getElementById('briefingBtn');
        const speakingIndicator = document.getElementById('speakingIndicator');

        function connectWS() {
            const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${proto}//${location.host}/ws/voice`);
            
            ws.onopen = () => {
                connectionStatus.className = 'px-3 py-1 text-xs rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
                connectionStatus.innerText = 'Connected';
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'transcript') {
                    appendTranscript(data.sender, data.text);
                } else if (data.type === 'speaking_state') {
                    speakingIndicator.innerText = data.text;
                } else if (data.type === 'audio_playback') {
                    playAudioBase64(data.audio);
                }
            };

            ws.onclose = () => {
                connectionStatus.className = 'px-3 py-1 text-xs rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20';
                connectionStatus.innerText = 'Disconnected';
                setTimeout(connectWS, 2000);
            };
        }

        consentBtn.onclick = () => {
            isConsented = true;
            consentBanner.classList.add('hidden');
            roomControls.classList.remove('hidden');
            ws.send(JSON.stringify({ type: 'consent_granted' }));
            initSpeechRecognition();
        };

        briefingBtn.onclick = () => {
            ws.send(JSON.stringify({ type: 'start_briefing' }));
        };

        function appendTranscript(sender, text) {
            const row = document.createElement('div');
            const isAI = sender.includes('AI');
            row.className = isAI ? 'text-indigo-400' : 'text-emerald-400';
            row.innerHTML = `<span class="font-bold opacity-75">[${new Date().toLocaleTimeString()}] ${sender}:</span> ${text}`;
            transcriptBox.appendChild(row);
            transcriptBox.scrollTop = transcriptBox.scrollHeight;
        }

        function playAudioBase64(b64) {
            const audio = new Audio("data:audio/wav;base64," + b64);
            audio.play();
        }

        function initSpeechRecognition() {
            const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRec) {
                appendTranscript('System', 'Browser Speech Recognition API not supported in this browser. You can type or use virtual audio.');
                return;
            }
            recognition = new SpeechRec();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-IN'; // Indian-English locale

            recognition.onresult = (e) => {
                const text = e.results[0][0].transcript;
                appendTranscript('Intern (Spoken)', text);
                ws.send(JSON.stringify({ type: 'user_speech', text: text }));
            };

            recognition.onend = () => {
                isListening = false;
                micText.innerText = 'Hold / Click to Speak';
                micBtn.classList.remove('bg-rose-600', 'hover:bg-rose-500');
            };

            micBtn.onclick = () => {
                if (!isListening) {
                    try {
                        recognition.start();
                        isListening = true;
                        micText.innerText = 'Listening... Speak now';
                        micBtn.classList.add('bg-rose-600', 'hover:bg-rose-500');
                    } catch(err) {
                        console.error(err);
                    }
                } else {
                    recognition.stop();
                }
            };
        }

        connectWS();
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get_voice_room():
    return VOICE_ROOM_HTML

@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()
    tts_engine = pyttsx3.init()
    tts_engine.setProperty('rate', 165)
    
    # Store session state
    is_consented = False
    
    async def speak_and_send(sender: str, text: str):
        await websocket.send_json({
            "type": "transcript",
            "sender": sender,
            "text": text
        })
        
        # Synthesize audio to base64
        import base64
        out_wav = Path("poc") / f"ws_speech_{int(time.time()*1000)}.wav"
        tts_engine.save_to_file(text, str(out_wav))
        tts_engine.runAndWait()
        
        if out_wav.exists():
            with open(out_wav, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            await websocket.send_json({
                "type": "audio_playback",
                "audio": b64
            })
            try:
                out_wav.unlink()
            except Exception:
                pass

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type")
            
            if msg_type == "consent_granted":
                is_consented = True
                greeting = (
                    "Thank you for confirming consent. I am the Task Reviewer AI assistant. "
                    "I will guide you through your assignment briefing and review your submissions."
                )
                await speak_and_send("Task Reviewer AI", greeting)
                
            elif msg_type == "start_briefing" and is_consented:
                briefing = (
                    "Here is your assignment overview. Objective: Deliver a verified task review system. "
                    "Requirements include role-based access, evidence-based rubrics, and automated scheduling. "
                    "The submission deadline is Friday, 6 PM Indian Standard Time. Do you have any questions?"
                )
                await speak_and_send("Task Reviewer AI", briefing)
                
            elif msg_type == "user_speech" and is_consented:
                user_text = data.get("text", "")
                # Query local Ollama model if running
                prompt = (
                    f"You are the Task Reviewer AI assistant. The intern asked: \"{user_text}\". "
                    "Respond concisely in 1-2 spoken sentences based on standard task review guidelines. "
                    "Do not pretend to be human."
                )
                ai_reply = "I noted your inquiry. Please ensure all deliverables include reproducible tests."
                try:
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        res = await client.post("http://127.0.0.1:11434/api/generate", json={
                            "model": "llama3.2:1b",
                            "prompt": prompt,
                            "stream": False
                        })
                        if res.status_code == 200:
                            ai_reply = res.json().get("response", "").strip()
                except Exception:
                    pass
                    
                await speak_and_send("Task Reviewer AI", ai_reply)
                
    except WebSocketDisconnect:
        print("[VOICE ROOM] WebSocket disconnected.")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765)
