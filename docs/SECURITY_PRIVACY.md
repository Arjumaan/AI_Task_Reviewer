# Security, Privacy & Ethical Compliance Architecture

## 1. Transparency, Identity & Human Non-Impersonation

The Task Reviewer AI strictly complies with transparency and ethical AI mandates:
1. **Explicit Identity Disclosure**: The bot introduces itself transparently as an **AI Task Reviewer** during all meetings, briefings, and written communications.
2. **Prohibition of Deception**: The system never simulates a human employee, never claims to hold a corporate title, and never presents synthetic persona narratives.
3. **Disclosure of Capabilities & Limits**: If an intern asks questions outside the approved task specification, the agent acknowledges uncertainty rather than hallucinating answers and flags the unresolved inquiry for the assigner.

---

## 2. Affirmative Recording & Transcription Consent

Meeting audio capture and transcription are governed by strict consent controls:
1. **Pre-Capture Notification**: Audio capture is blocked until the participant affirms consent.
2. **Affirmative Consent Gate**: In both Google Meet sessions and the fallback Web Audio Voice Room, the user must explicitly accept:
   > *"I acknowledge the AI disclosure and consent to audio recording and transcription."*
3. **Visible Recording Indicators**: When recording is active, a persistent visible indicator and active waveform visualizer are presented.
4. **Zero Covert Recording**: If consent is declined or revoked, the session immediately terminates without saving audio.

---

## 3. Prompt Injection Defense on Untrusted Documents

Task brief documents (PDF, DOCX, TXT) uploaded by users or third parties are treated as untrusted text strings rather than executable system instructions:
- **Heuristic Pattern Scanning**: Uploaded documents are scanned for prompt override patterns, including:
  - `ignore all previous instructions`
  - `you are now an unrestricted assistant`
  - `system prompt` / `jailbreak` / `DAN`
- **Detection Flags**: If suspicious patterns are detected, `has_detected_injection` is set to `True`, a warning alert is surfaced in the Assigner UI, and the text is quarantined.
- **Strict Delimited Framing**: When extracting specifications via local Ollama, the raw text is wrapped in triple-quoted string blocks with an explicit system directive that treats document contents strictly as passive content to be parsed into JSON.

---

## 4. Role-Based Access Isolation (RBAC)

The REST API enforces granular role-based authorization via JWT Bearer tokens:
- **`ADMIN`**: System telemetry, host benchmarks, user creation, global audit trail inspection, and recording retention management.
- **`ASSIGNER`**: Task creation, document uploads, AI draft extraction, specification approval, scheduling, review evaluations, and manual overrides.
- **`INTERN`**: Restricted to assigned tasks, viewing approved specifications, delivering submissions, viewing feedback, and filing evaluation appeals. Interns are prevented from viewing or modifying tasks assigned to other users.

---

## 5. Storage Security, Retention & Deletion Policies

- **Path Traversal Protection**: Document filenames are sanitized using strict basename extraction (`os.path.basename`) and validated against permitted file extensions (`.pdf`, `.docx`, `.txt`).
- **Encrypted Local Storage**: Stored artifacts, recordings, and extracted transcripts reside in dedicated local directories with restricted filesystem permissions.
- **Retention Lifecycle**: Audio recordings default to a 30-day retention window.
- **Right to Deletion**: Administrators can trigger hard deletion of recordings and transcripts, creating an immutable audit trail entry (`RECORDING_PURGED`).
