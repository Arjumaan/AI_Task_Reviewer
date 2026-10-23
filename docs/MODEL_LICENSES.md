# Model, Voice & Dependency License Audit

This document records the license verification for every machine learning model, voice checkpoint, runtime engine, and software dependency used within Task Reviewer AI.

---

## 1. Local Language Model Inference

| Component | Repository / Provider | License | Permitted Uses & Constraints |
| :--- | :--- | :--- | :--- |
| **Ollama Runtime** | [ollama/ollama](https://github.com/ollama/ollama) | **MIT License** | Completely free and open-source software for commercial and private use. |
| **Llama 3.2 1B Instruct** | [Meta AI / Hugging Face](https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct) | **Llama 3.2 Community License** | Free open-weights license permitting commercial deployment up to 700M monthly active users. Verified compatible with host memory constraints (~1.3 GB GGUF Q4_K_M). |

---

## 2. Speech Synthesis & Recognition Engines

| Component | Repository / Provider | License | Permitted Uses & Constraints |
| :--- | :--- | :--- | :--- |
| **Piper TTS Engine** | [rhasspy/piper](https://github.com/rhasspy/piper) | **MIT License** | Fast, local neural text-to-speech engine running natively on CPU. |
| **Piper Indian-English Voice Model** | CMU Indic / LibriTTS-R | **BSD 3-Clause / CC BY 4.0** | Open audio datasets and neural weights for local voice synthesis. |
| **faster-whisper STT** | [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) | **MIT License** | CTranslate2-based local reimplementation of OpenAI's Whisper model; zero cloud data transit. |
| **OpenAI Whisper Weights** | [openai/whisper](https://github.com/openai/whisper) | **MIT License** | Fully open-source acoustic weights. |

---

## 3. Web Framework, Core Libraries & Database

| Component | Source | License |
| :--- | :--- | :--- |
| **FastAPI** | tiangolo/fastapi | **MIT License** |
| **Uvicorn** | encode/uvicorn | **BSD-3-Clause** |
| **SQLAlchemy** | zzzeek/sqlalchemy | **MIT License** |
| **Alembic** | sqlalchemy/alembic | **MIT License** |
| **aiosqlite** | omnilib/aiosqlite | **MIT License** |
| **asyncpg** | MagicStack/asyncpg | **Apache 2.0** |
| **Pydantic** | pydantic/pydantic | **MIT License** |
| **pypdf** | py-pdf/pypdf | **BSD-3-Clause** |
| **python-docx** | python-openxml/python-docx | **MIT License** |
| **bcrypt** | pyca/bcrypt | **Apache 2.0** |
| **PyJWT** | jpadilla/pyjwt | **MIT License** |

---

## 4. Frontend & User Interface Stack

| Component | Source | License |
| :--- | :--- | :--- |
| **React** | facebook/react | **MIT License** |
| **Vite** | vitejs/vite | **MIT License** |
| **Tailwind CSS** | tailwindlabs/tailwindcss | **MIT License** |
| **Lucide Icons** | lucide-icons/lucide | **ISC License** |
| **Axios** | axios/axios | **MIT License** |

---

## 5. Verification Summary
- **Zero Paid AI APIs**: No OpenAI, Anthropic, ElevenLabs, Deepgram, or Recall.ai APIs are bundled or invoked by default.
- **Proprietary External Exceptions**: Google Calendar, Google Meet, and Gmail are documented separately as external Google cloud services.
