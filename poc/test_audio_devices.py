"""
Audio Device & Virtual Cable Loopback Verification Script.
Tests device discovery, identifies Virtual Audio Cable,
and verifies loopback audio playback and capture.
"""
import sys
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
from pathlib import Path

def inspect_devices():
    print("=" * 60)
    print("AUDIO SUBSYSTEM INSPECTION")
    print("=" * 60)
    devices = sd.query_devices()
    vac_in = None
    vac_out = None
    
    for i, dev in enumerate(devices):
        name = dev["name"]
        max_in = dev["max_input_channels"]
        max_out = dev["max_output_channels"]
        host_api = sd.query_hostapis(dev["hostapi"])["name"]
        
        status_tag = ""
        if "virtual audio cable" in name.lower() or "line 1" in name.lower():
            status_tag = " [VIRTUAL AUDIO CABLE]"
            if max_in > 0 and vac_in is None:
                vac_in = (i, name, host_api)
            if max_out > 0 and vac_out is None:
                vac_out = (i, name, host_api)
                
        print(f"[{i:02d}] {name} ({host_api}) - In: {max_in}, Out: {max_out}{status_tag}")
        
    print("-" * 60)
    print(f"Detected Virtual Cable Input (Recording): {vac_in}")
    print(f"Detected Virtual Cable Output (Playback): {vac_out}")
    print("-" * 60)
    return vac_in, vac_out

def test_loopback(vac_in, vac_out, duration_sec=2.0, sample_rate=44100):
    if not vac_in or not vac_out:
        print("[WARNING] Virtual Audio Cable not fully identified. Skipping loopback test.")
        return False
        
    print(f"\n[LOOPBACK TEST] Generating {duration_sec}s 440Hz test sine tone...")
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    # Generate 440 Hz test sine wave with envelope
    envelope = np.sin(np.pi * t / duration_sec)
    tone = (0.5 * np.sin(2 * np.pi * 440 * t) * envelope).astype(np.float32)
    # Convert to stereo
    stereo_tone = np.column_stack([tone, tone])
    
    in_idx = vac_in[0]
    out_idx = vac_out[0]
    
    print(f"Playing to Device [{out_idx}]: {vac_out[1]}")
    print(f"Recording from Device [{in_idx}]: {vac_in[1]}")
    
    recorded_chunks = []
    
    try:
        # Start recording
        recording = sd.playrec(
            stereo_tone,
            samplerate=sample_rate,
            device=(in_idx, out_idx),
            channels=2,
            dtype='float32'
        )
        sd.wait()
        
        # Calculate RMS of recorded signal
        rms = np.sqrt(np.mean(recording ** 2))
        max_amp = np.max(np.abs(recording))
        print(f"\n[RESULT] Playback & Capture Complete!")
        print(f"Captured Max Amplitude: {max_amp:.4f}")
        print(f"Captured RMS: {rms:.4f}")
        
        out_path = Path("poc") / "loopback_test.wav"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), recording, sample_rate)
        print(f"Saved loopback recording to: {out_path.resolve()}")
        
        if rms > 0.01:
            print("[SUCCESS] Virtual Audio Cable loopback verified with strong signal fidelity!")
            return True
        else:
            print("[INFO] Signal captured was silent or low amplitude. May require volume adjustment or active audio repeater.")
            return False
            
    except Exception as e:
        print(f"[ERROR] Loopback test encountered an exception: {e}")
        return False

if __name__ == "__main__":
    v_in, v_out = inspect_devices()
    test_loopback(v_in, v_out)
