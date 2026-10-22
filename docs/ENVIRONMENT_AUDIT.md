# Environment and Hardware Audit

**Audit Date**: October 22, 2026  
**Auditor**: Lead Architect & Systems Engineer  
**Host Platform**: Microsoft Windows 11 Pro (Build 10.0.26200, 64-bit)  
**Workspace Path**: `D:\My Projects\AI-Task_Reviewer`  

---

## 1. Executive Summary & Constraints

This environment audit evaluates the host workstation's hardware, operating system, runtimes, audio pipeline, and dependencies to establish a grounded, production-grade deployment plan for the **Task Reviewer AI Agent**.

### Critical Environmental Findings:
1. **Total Physical Memory is 8.00 GB** (~7.73 GiB visible) with approximately **0.8 to 1.2 GB of free physical memory** under baseline desktop conditions.
2. **CPU is a 12th Gen Intel Core i3-1215U** (6 cores: 2 Performance cores + 4 Efficient cores, 8 logical processors) with AVX2 instruction support.
3. **GPU is Integrated Intel UHD Graphics** with no dedicated VRAM. All AI inference (LLM, STT, TTS) **must run on the CPU** using quantized, low-footprint models.
4. **Virtual Audio Infrastructure**: **Virtual Audio Cable (Line 1)** is already installed and verified as active in the audio subsystem (`Line 1 (Virtual Audio Cable)` Input and Output). This enables zero-hardware audio loopback for browser-based Google Meet automation.
5. **Disk Space**: The project volume (`D:`) has **13.53 GB free**, while the OS drive (`C:`) has **57.64 GB free**. Models and cache must be managed carefully to avoid disk exhaustion.
6. **Docker Status**: Docker Desktop binaries are present, but the daemon is not currently active. The application must support **Native Local Development** as primary, with **Docker Compose** provided for containerized staging/production.

---

## 2. Hardware Inventory (Grounded & Verified)

| Component | Specification | Operational Constraint / Impact |
| :--- | :--- | :--- |
| **Operating System** | Windows 11 Pro 64-bit (10.0.26200) | Windows PowerShell native environment; path handling must support Windows paths. |
| **Processor (CPU)** | Intel Core i3-1215U @ 1.20 GHz (Turbo 4.40 GHz)<br>6 physical cores (2 P-cores, 4 E-cores), 8 threads | CPU-bound AI inference. AVX2/FMA enabled. Fast enough for 1B-3B LLMs and quantized Whisper. |
| **Memory (RAM)** | 8,106,488 KB Total (~7.73 GiB)<br>Free: ~821 MB – 1,200 MB baseline | **Strict bottleneck**. Total active model working set must not exceed 2.0 GB. Models > 3B will cause OS thrashing or OOM. |
| **Graphics (GPU)** | Intel(R) UHD Graphics (Driver 32.0.101.7082)<br>Dedicated VRAM: 0 MB (Shared system memory) | No CUDA or ROCm. PyTorch / llama.cpp must use CPU/AVX2 kernels exclusively. |
| **Storage: C Drive** | NTFS, Total: 303.71 GB, Free: **57.64 GB** | Hosts OS, user profile, Ollama model cache (`~/.ollama`), and Python runtimes. |
| **Storage: D Drive** | NTFS, Total: 98.29 GB, Free: **13.53 GB** | Hosts application repository, virtual environments, database, and logs. |
| **Storage: E Drive** | NTFS, Total: 74.83 GB, Free: **5.33 GB** | Reserved/Not used for project. |

---

## 3. Audio & Media Subsystem

The audio subsystem was inspected via Windows CIM (`Win32_SoundDevice`) and Python `sounddevice`:

| Device Name | Type | Channel Configuration | System Role |
| :--- | :--- | :--- | :--- |
| **Line 1 (Virtual Audio Cable)** | Virtual MME / WASAPI / DirectSound | 2 In / 2 Out | **Loopback Pipeline**: Enables injecting synthetic bot voice into Google Meet mic and capturing incoming participant voice. |
| **Microphone Array (Realtek(R) Audio)** | Hardware Input | 2 In, 0 Out | Physical test microphone for human operator validation. |
| **Speakers (Realtek(R) Audio) / TOSHIBA-TV** | Hardware Output | 0 In, 2 Out | Physical audio monitoring. |

---

## 4. Software & Runtime Inventory

| Tool / Runtime | Installed Version | Location / Binary Path | Status & Notes |
| :--- | :--- | :--- | :--- |
| **Python** | 3.13.1 (64-bit) | `C:\Users\Arjumaan.M\AppData\Local\Programs\Python\Python313\python.exe` | Verified. Core backend runtime. |
| **uv** | Active | `C:\Users\Arjumaan.M\AppData\Local\hermes\bin\uv.exe` | High-performance Python package and venv manager. |
| **Node.js** | 22.14.0 (LTS) | `C:\Program Files\nodejs\node.exe` | Verified. Frontend Vite/React build runtime. |
| **npm** | 10.9.2 | `C:\Program Files\nodejs\npm.ps1` | Node package manager. |
| **pnpm** | Active | `C:\Users\Arjumaan.M\AppData\Roaming\npm\pnpm.ps1` | Fast alternative package manager. |
| **Git** | 2.47.0.windows.2 | `C:\Program Files\Git\cmd\git.exe` | Repository initialized and tracked. |
| **FFmpeg** | Active | `C:\Users\Arjumaan.M\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe` | Verified. Audio conversion, slicing, and normalization. |
| **Ollama** | 0.33.1 | `C:\Users\Arjumaan.M\AppData\Local\Programs\Ollama\ollama.exe` | Local LLM server running on `http://127.0.0.1:11434`. |
| **Google Chrome** | Active | `C:\Program Files\Google\Chrome\Application\chrome.exe` | Available for Playwright automation. |
| **Microsoft Edge** | Active | `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` | Available for Chromium automation. |
| **Docker Desktop** | Binaries Present | `C:\Program Files\Docker\Docker\resources\bin\docker.exe` | Daemon inactive; Docker Compose configured for deployment. |

---

## 5. Model Memory Estimates & Supported AI Configurations

Given the 8 GB total system RAM and integrated graphics, LLM and audio models must strictly observe the following memory budget:

### Memory Budget Allocation
```
Total System RAM: 8.0 GB
Operating System & Desktop Baseline: ~3.5 - 4.5 GB
FastAPI Backend + Vite Frontend Dev: ~0.8 GB
Whisper Speech-to-Text: ~0.4 - 0.6 GB
TTS Engine (Piper / SAPI5): ~0.2 GB
Headless Browser (Meet Automation): ~0.6 - 0.9 GB
Allocable Budget for Local LLM: ~1.2 - 2.0 GB MAX
```

### Model Feasibility Matrix

| Model | Quantization | Parameter Size | Estimated RAM Required | Inference Speed (CPU) | Viability on Host |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Llama-3.2-1B-Instruct** | Q4_K_M | 1.2B | ~1.1 GB | ~30 - 45 tps | **Highly Recommended** (Fast conversational agent) |
| **Llama-3.2-3B-Instruct** | Q4_K_M | 3.2B | ~2.0 GB | ~14 - 20 tps | **Supported** (Evaluation & structured extraction) |
| **Qwen-2.5-1.5B-Instruct** | Q4_K_M | 1.5B | ~1.2 GB | ~28 - 40 tps | **Supported** (High extraction accuracy) |
| **Qwen-2.5-3B-Instruct** | Q4_K_M | 3.1B | ~2.1 GB | ~12 - 18 tps | **Marginal** (Tightly fits RAM budget) |
| **Llama-3.1-8B-Instruct** | Q4_K_M | 8.0B | ~4.9 GB | ~3 - 6 tps | **Infeasible** (Will induce OS disk paging & OOM) |
| **Gemma-4-31B** | Q4_K_M | 31B | ~19.0 GB | < 0.5 tps | **Completely Infeasible** (Exceeds total RAM by 2.4x) |

### Speech Model Configuration:
1. **Speech-to-Text (STT)**:
   - Engine: `faster-whisper` (CTranslate2 backend with AVX2 quantization).
   - Model: `base.en` (140 MB, ~350 MB RAM working set) or `small.en` (460 MB, ~700 MB RAM working set).
   - Expected Real-Time Factor (RTF): < 0.25 on Intel i3-1215U (4 seconds of audio processed in < 1 second).
2. **Text-to-Speech (TTS)**:
   - Primary: `piper-tts` or `pyttsx3` / local synthesis engine.
   - Voice: Indian-English accent model (e.g. `en_IN` voice in Piper, or SAPI5 Indian voice if provisioned, or high-fidelity open-source Indian English phoneme mapping).
   - Latency: < 400ms for short sentences on CPU.

---

## 6. Architecture & Deployment Strategy

To respect the host machine's hardware profile while meeting all enterprise software requirements:
1. **Modular Monolith**:
   - Backend: Python 3.13 + FastAPI + SQLAlchemy + SQLite / PostgreSQL (with Alembic migrations).
   - Frontend: React 19 + TypeScript + Vite + Tailwind CSS.
   - Background Processing: Asyncio worker queue for local native execution; Celery + Redis configuration provided in Docker Compose for production scale.
2. **Google Meet Gateway**:
   - Standalone automation engine using Playwright with Chromium.
   - Virtual Audio Cable (Line 1) loopback for synthetic mic input and participant capture.
   - Transparent identification: AI participant joins with name `"Task Reviewer AI (Assistant)"`, displays recording disclaimer, and enforces consent prompts.
3. **Storage**:
   - Local filesystem object storage (`./storage/recordings`, `./storage/uploads`) with strict access validation and path traversal defenses.

---

## 7. Audit Conclusion & Next Phase Readiness

The host environment is **viable and ready** for implementation under the optimized CPU architecture:
- Hardware and runtimes verified.
- Virtual Audio Cable verified and available for the Google Meet audio bridge.
- Ollama local inference server verified and running.
- Phase 2 (Google Meet Feasibility Proof of Concept & `docs/MEET_FEASIBILITY.md`) can commence immediately.
