"""
Local TTS Engine Verification & Benchmark Script.
Tests speech synthesis latency, voice quality, and audio generation
for the AI Task Reviewer briefing and review disclosures.
"""
import sys
import time
import os
from pathlib import Path
import pyttsx3
import soundfile as sf

DISCLOSURE_TEXT = (
    "Hello, I am the Task Reviewer AI assistant. "
    "I will be briefing you on the assignment requirements and reviewing your deliverables. "
    "Please note that this session is being recorded and transcribed for evaluation purposes. "
    "Do you consent to proceed with this session?"
)

BRIEFING_SAMPLE = (
    "The assignment objective is to implement a robust, secure task review automation service. "
    "All criteria must be verifiably backed by automated test suites or reproducible artifacts. "
    "The deadline is Friday, 6:00 PM Indian Standard Time."
)

def benchmark_tts():
    print("=" * 60)
    print("LOCAL TTS ENGINE BENCHMARK")
    print("=" * 60)
    
    start_init = time.perf_counter()
    engine = pyttsx3.init()
    init_time = (time.perf_counter() - start_init) * 1000
    print(f"Engine Initialization Time: {init_time:.2f} ms")
    
    voices = engine.getProperty('voices')
    print(f"Total System Voices Detected: {len(voices)}")
    selected_voice = None
    
    for v in voices:
        print(f" - ID: {v.id}")
        print(f"   Name: {v.name}")
        print(f"   Languages: {v.languages}, Gender: {getattr(v, 'gender', 'N/A')}")
        # Prefer Indian-English or Hazel/Zira
        if any(token in v.name.lower() for token in ["india", "heera", "ravi", "veena", "hazel"]):
            if selected_voice is None or "india" in v.name.lower():
                selected_voice = v
                
    if not selected_voice and voices:
        selected_voice = voices[0]
        
    print(f"\nSelected Voice: {selected_voice.name if selected_voice else 'Default'}")
    if selected_voice:
        engine.setProperty('voice', selected_voice.id)
        
    engine.setProperty('rate', 165) # Natural cadence
    engine.setProperty('volume', 1.0)
    
    # Benchmark synthesis to file
    out_dir = Path("poc") / "audio_samples"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "disclosure_announcement.wav"
    
    print(f"\nSynthesizing Disclosure Announcement ({len(DISCLOSURE_TEXT.split())} words)...")
    start_synth = time.perf_counter()
    engine.save_to_file(DISCLOSURE_TEXT, str(out_file))
    engine.runAndWait()
    synth_duration = (time.perf_counter() - start_synth) * 1000
    
    file_size_kb = out_file.stat().st_size / 1024
    print(f"Synthesis Complete in: {synth_duration:.2f} ms")
    print(f"Generated File: {out_file.resolve()} ({file_size_kb:.1f} KB)")
    
    # Read audio metadata
    data, sr = sf.read(str(out_file))
    audio_len_sec = len(data) / sr
    rtf = (synth_duration / 1000.0) / audio_len_sec
    print(f"Audio Duration: {audio_len_sec:.2f} seconds")
    print(f"Real-Time Factor (RTF): {rtf:.3f}x (< 1.0 is faster than real time)")
    
    return {
        "voice": selected_voice.name if selected_voice else "Default",
        "init_ms": init_time,
        "synth_ms": synth_duration,
        "audio_len_sec": audio_len_sec,
        "rtf": rtf,
        "output_path": str(out_file)
    }

if __name__ == "__main__":
    benchmark_tts()
