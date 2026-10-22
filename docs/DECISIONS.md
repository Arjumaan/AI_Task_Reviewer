# Architecture Decisions Log (ADR)

## ADR-001: System Architecture — Modular Monolith
* **Status**: Accepted
* **Context**: The Task Reviewer AI manages task analysis, scheduling, Google Meet sessions, audio streaming, evaluation, and notifications. System resources are constrained (8 GB RAM, Intel Core i3 CPU). A distributed microservice fleet would consume excessive idle memory and add needless network serialization overhead.
* **Decision**: Adopt a Modular Monolith architecture using FastAPI (Python 3.13) for the backend and React + TypeScript + Vite for the frontend. Keep strict domain boundaries between modules:
  - `tasks`: Document ingestion, text extraction, specification draft, assigner approval.
  - `scheduling`: Timezone handling (Asia/Kolkata), Google Calendar integration, idempotency, event lifecycles.
  - `agent`: Briefing and review conversational state machines, context windows, prompt management.
  - `media`: Audio device routing, Playwright browser bot, WebRTC/Virtual Audio Cable bridge, local STT/TTS.
  - `evaluation`: Deterministic & LLM-assisted rubrics, evidence extraction, revision loop.
  - `notifications`: Gmail API delivery, audit records, retry policies.
  - `audit`: Immutable audit trails for all actions, recordings, and evaluations.
* **Consequences**: Minimal memory overhead, zero inter-service network latency, simplified testing and deployment. Can be containerized with Docker Compose or run directly on native OS.

---

## ADR-002: Local LLM Engine — Ollama with 1B-3B Quantized Instruct Models
* **Status**: Accepted
* **Context**: Paid AI APIs (OpenAI, Anthropic, ElevenLabs, Deepgram) are strictly prohibited. Local hardware has 8.0 GB RAM (~1 GB free at baseline) and an Intel Core i3-1215U CPU with integrated UHD graphics (no CUDA).
* **Decision**: Use Ollama with CPU-quantized instruct models:
  - Primary Conversational Model: `llama3.2:1b` (1.3 GB RAM, ~35 tps) for low-latency dialogue during briefings and reviews.
  - Extraction & Evaluation Model: `llama3.2:3b` (2.0 GB RAM, ~15 tps) or `qwen2.5:1.5b` (1.1 GB RAM) for structured JSON extraction and evidence analysis.
* **Consequences**: Fully local, zero API cost, strict privacy (task documents and audio transcripts never leave the machine). Larger models (>3B) are rejected to prevent system OOM.

---

## ADR-003: Speech Processing — Faster-Whisper & Piper/SAPI5 TTS
* **Status**: Accepted
* **Context**: Need accurate real-time speech-to-text (STT) and intelligible natural voice text-to-speech (TTS) with Indian-English preference, running entirely offline.
* **Decision**:
  - STT: `faster-whisper` (CTranslate2 with int8 CPU quantization) using `base.en` (~140MB) or `small.en` (~460MB).
  - TTS: `piper-tts` with Indian English voice model (`en_IN`) as primary; SAPI5 `pyttsx3` as offline zero-dependency system fallback.
* **Consequences**: Total speech pipeline uses < 800 MB RAM, meeting the strict memory budget.

---

## ADR-004: Google Meet Proof of Concept & Gateway Architecture
* **Status**: Accepted
* **Context**: The AI agent must join Google Meet as a clearly identified participant (`"Task Reviewer AI (Assistant)"`), state disclosure/recording consent, receive meeting audio, and speak into the meeting microphone.
* **Decision**:
  - Use Playwright with Chromium automation.
  - Use **Virtual Audio Cable (`Line 1`)** for bidirectional audio routing:
    - Bot TTS plays audio into `Line 1 (Virtual Audio Cable) Output`, which Chromium captures as its simulated microphone input.
    - Chromium renders participant audio into system output or dedicated loopback for transcription.
  - Provide an interactive, local **Web Voice Room** fallback if Google Meet blocks bot entry due to bot-detection or unauthenticated guest policies.
* **Consequences**: Allows rigorous end-to-end testing without proprietary paid meeting bot services (Recall.ai, etc.).

---

## ADR-005: Database & Persistence — SQLite Native / PostgreSQL Production
* **Status**: Accepted
* **Context**: Needs robust schema migrations, UUID keys, foreign key constraints, and transactional integrity while allowing instant zero-setup local execution without requiring a running Docker daemon.
* **Decision**:
  - Use SQLAlchemy 2.0 with Alembic migrations.
  - Default database URL is SQLite (`sqlite+aiosqlite:///./storage/reviewer.db`) with Foreign Keys enabled for zero-friction local native development.
  - Seamlessly switch to PostgreSQL (`postgresql+asyncpg://...`) via `DATABASE_URL` environment variable for Docker Compose or production deployments.
* **Consequences**: Developers can run and test the entire platform without spinning up external containers, while production deployments retain full PostgreSQL enterprise capabilities.
