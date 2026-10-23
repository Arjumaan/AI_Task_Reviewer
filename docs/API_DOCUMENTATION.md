# REST API Documentation (OpenAPI v3.1 Specification)

Base URL: `http://localhost:8000/api/v1`  
Authentication: HTTP Bearer Token (`Authorization: Bearer <JWT_TOKEN>`)

---

## 1. Authentication Endpoints

### `POST /auth/login`
Authenticates a user and returns an access token.
- **Content-Type**: `application/x-www-form-urlencoded`
- **Request Body**:
  - `username` (string, email address)
  - `password` (string)
- **Response `200 OK`**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
    "token_type": "bearer"
  }
  ```

### `GET /auth/me`
Retrieves profile of currently authenticated user.
- **Headers**: `Authorization: Bearer <TOKEN>`
- **Response `200 OK`**:
  ```json
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "email": "assigner@internal.company",
    "full_name": "Senior Staff Architect",
    "role": "ASSIGNER",
    "is_active": true,
    "created_at": "2026-10-22T10:00:00Z"
  }
  ```

---

## 2. Tasks Endpoints

### `GET /tasks/`
Lists all visible tasks for the current user's role.
- **Roles**: `ADMIN`, `ASSIGNER`, `INTERN`
- **Response `200 OK`**: Array of `TaskResponse`.

### `POST /tasks/`
Creates a new draft task.
- **Roles**: `ADMIN`, `ASSIGNER`
- **Request Body**:
  ```json
  {
    "title": "Distributed Consensus Engine",
    "intern_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
  }
  ```
- **Response `201 Created`**: `TaskResponse`.

### `POST /tasks/{task_id}/upload`
Uploads and extracts raw brief document (PDF, DOCX, TXT).
- **Content-Type**: `multipart/form-data`
- **Form Key**: `file`
- **Response `200 OK`**:
  ```json
  {
    "document_id": "...",
    "filename": "brief.pdf",
    "detected_injection": false,
    "extracted_length": 3412
  }
  ```

### `POST /tasks/{task_id}/extract-draft`
Triggers local Ollama structured specification drafting.
- **Roles**: `ADMIN`, `ASSIGNER`
- **Response `200 OK`**: Returns `TaskSpecificationDraft` with extracted objective, deliverables, requirements, acceptance criteria, and rubrics.

### `POST /tasks/{task_id}/approve-specification`
Locks and publishes task specification version.
- **Roles**: `ADMIN`, `ASSIGNER`
- **Request Body**: Complete `TaskSpecificationDraft`
- **Response `200 OK`**: Updated `TaskResponse` with status `SPECIFICATION_APPROVED`.

---

## 3. Scheduling Endpoints

### `POST /scheduling/meetings`
Schedules briefing or review meeting in `Asia/Kolkata` timezone.
- **Roles**: `ADMIN`, `ASSIGNER`
- **Request Body**:
  ```json
  {
    "task_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "meeting_type": "BRIEFING",
    "start_time_iso": "2026-10-25T10:00:00+05:30",
    "duration_minutes": 30,
    "timezone": "Asia/Kolkata"
  }
  ```
- **Response `201 Created`**: Returns `MeetingResponse` with Google Meet URL or synthetic dry-run link.

---

## 4. Submissions & Reviews Endpoints

### `POST /submissions/`
Submits code repository and commit hash for review.
- **Roles**: `INTERN`
- **Request Body**:
  ```json
  {
    "task_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "repository_url": "https://github.com/intern/consensus-engine",
    "commit_hash": "a1b2c3d4e5f6",
    "notes": "Passed all deterministic unit tests."
  }
  ```
- **Response `201 Created`**: Returns `SubmissionResponse` with initialized `ReviewRound 1`.

### `POST /reviews/{round_id}/evaluate`
Executes evidence-backed rubric evaluation engine.
- **Roles**: `ADMIN`, `ASSIGNER`
- **Request Body**:
  ```json
  {
    "test_output": "14 passed, 0 failed in 0.82s (100% pass)",
    "repo_url": "https://github.com/intern/consensus-engine",
    "meeting_transcripts": [
      "AI Reviewer: Explain your failure recovery mechanism.",
      "Intern: We implemented raft log replication with automatic leader re-election."
    ]
  }
  ```
- **Response `200 OK`**: Returns updated `ReviewRoundResponse` with `outcome` (`PASS`, `REVISION_REQUIRED`, `HUMAN_REVIEW_REQUIRED`), confidence scores, and revision action items.

### `POST /reviews/{round_id}/appeal`
Files an intern dispute or appeal against an automated review finding.
- **Roles**: `INTERN`
- **Request Body**:
  ```json
  {
    "reason": "Floating point tolerance mismatch on GPU hardware."
  }
  ```
- **Response `200 OK`**: Transitions status to `HUMAN_REVIEW_REQUIRED`.

### `POST /reviews/{round_id}/override`
Allows company assigner to manually override an outcome.
- **Roles**: `ADMIN`, `ASSIGNER`
- **Request Body**:
  ```json
  {
    "outcome": "PASS",
    "notes": "Verified offline unit tests manually on assigner workstation."
  }
  ```

---

## 5. Telemetry & Benchmarks Endpoints

### `GET /health`
System liveness check and subsystem readiness.
- **Response `200 OK`**:
  ```json
  {
    "status": "healthy",
    "services": {
      "database": "ok",
      "ollama": "ok",
      "speech_tts": "ok",
      "speech_stt": "ok",
      "storage": "ok"
    },
    "metrics": {
      "ollama_model": "llama3.2:1b",
      "ram_available_mb": 1140,
      "platform": "win32"
    }
  }
  ```

### `POST /benchmarks/run`
Executes live host CPU inference benchmark.
- **Roles**: `ADMIN`
- **Response `200 OK`**: Returns tokens/sec, latency, memory peak, and success status.
