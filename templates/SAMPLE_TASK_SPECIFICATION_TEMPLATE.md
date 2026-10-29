# CloudSync Engine — Core Microservices & Integration Task Specification

**Organization:** CloudSync Infrastructure Labs  
**Document Type:** Technical Assignment & Engineering Task Specification  
**Target Intern Role:** Backend & Cloud Engineering Intern  
**Target Deadline:** 7 days from initial Google Meet briefing session  
**Review Platform:** AI Task Reviewer Automated Evaluation Engine  

---

## 1. Executive Summary

During our Q4 reliability and security review of the CloudSync microservices architecture, several critical issues and feature enhancements were identified across four primary platform services: api.cloudsync.internal, auth.cloudsync.internal, worker.cloudsync.internal, and storage.cloudsync.internal. These microservices manage real-time file synchronization, user authentication, and high-throughput background processing for over 250,000 active users.

The purpose of this assignment is for the intern to investigate the root causes of these vulnerabilities and performance bottlenecks, implement clean, modular code fixes, and establish automated unit and integration tests. Upon completion, the intern will present their deliverables in a live review session where code quality, deterministic test coverage, and architecture decisions will be evaluated against our strict engineering rubrics.

---

## 2. Target Platforms & Scope

The scope of this technical task covers the following microservices:
- auth.cloudsync.internal: Authentication, session state, and OAuth2 security tokens.
- api.cloudsync.internal: Public REST API gateway and high-frequency endpoints.
- worker.cloudsync.internal: Celery and Redis background queue processing engine.
- storage.cloudsync.internal: S3-compatible chunked upload and file integrity subsystem.

---

## 3. Overall Findings & Requirements Snapshot

ID Platform Primary Area Severity Status
REQ-01 auth.cloudsync.internal JWT Refresh Token Revocation & Expiration Critical Open
REQ-02 api.cloudsync.internal Token Bucket Rate Limiting for Burst Traffic High Open
REQ-03 worker.cloudsync.internal Asynchronous Dead Letter Queue & Retry Backoff High Open
REQ-04 storage.cloudsync.internal SHA-256 Checksum Validation for Chunked Uploads Medium Open

---

## 4. Detailed Technical Specifications & Acceptance Criteria

### REQ-01 — JWT Refresh Token Revocation & Expiration
- Platform: auth.cloudsync.internal
- Severity: Critical
- Problem Statement: Refresh tokens currently lack explicit database revocation checks upon user logout or password changes, allowing stale tokens to generate valid access tokens indefinitely.
- Implementation Requirements:
  1. Store refresh token jti in Redis with active TTL.
  2. Implement an explicit /auth/revoke endpoint to blacklist revoked tokens immediately.
  3. Reject any refresh requests containing blacklisted or expired tokens with HTTP 401 Unauthorized.
- Acceptance Criteria (AC-01.1): 100% pass on deterministic integration tests verifying immediate token rejection after logout.

### REQ-02 — Token Bucket Rate Limiting for Burst Traffic
- Platform: api.cloudsync.internal
- Severity: High
- Problem Statement: High-volume client requests during sync surges can overwhelm downstream databases due to missing rate limiting headers and bucket controls.
- Implementation Requirements:
  1. Implement a distributed Token Bucket rate limiter middleware (limit: 100 requests per minute per client IP).
  2. Return standard HTTP headers (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset).
  3. Gracefully return HTTP 429 Too Many Requests when limits are exceeded.
- Acceptance Criteria (AC-02.1): Deterministic mock tests simulate 150 concurrent requests and verify 50 requests receive HTTP 429 with correct headers.

### REQ-03 — Asynchronous Dead Letter Queue & Retry Backoff
- Platform: worker.cloudsync.internal
- Severity: High
- Problem Statement: Transient network errors during external webhooks cause worker task drops without retry backoff or quarantine.
- Implementation Requirements:
  1. Implement exponential backoff retry mechanism (maximum 3 retries, base delay: 2s).
  2. Route persistently failed tasks to a dedicated Dead Letter Queue (DLQ) with error telemetry.
  3. Emit structured logs containing error details and original payload metadata.
- Acceptance Criteria (AC-03.1): Automated worker tests verify 3 retry attempts before routing failed jobs to DLQ.

### REQ-04 — SHA-256 Checksum Validation for Chunked Uploads
- Platform: storage.cloudsync.internal
- Severity: Medium
- Problem Statement: Multi-part uploaded file chunks are stitched without final hash verification, risking silent data corruption during packet loss.
- Implementation Requirements:
  1. Calculate rolling SHA-256 checksum during chunk reassembly.
  2. Compare calculated hash against client-provided Content-SHA256 header.
  3. Abort assembly and purge corrupted chunk artifacts if hash mismatch occurs.
- Acceptance Criteria (AC-04.1): Artifact inspection test verifying corrupt chunk payload triggers immediate cleanup and HTTP 422 Unprocessable Entity.

---

## 5. Expected Intern Deliverables

To pass the technical evaluation, the intern must deliver:
1. Source Code Patches: Modular, well-formatted code addressing REQ-01 through REQ-04 with zero regressions.
2. Automated Test Suite: Unit and integration test suite with minimum 90% code coverage.
3. Pull Request & Repository: Submitted GitHub Pull Request link with commit hash and description.
4. Verification Report: Reproduction steps, test execution logs, and sandbox instructions.

---

## 6. Evaluation Criteria & Review Protocol

- Deterministic Testing (Weight: 40%): Automated execution of all test suites against staging criteria.
- Code Quality & Architecture (Weight: 30%): Clean separation of concerns, error handling, and type safety.
- Security & Integrity (Weight: 20%): Adherence to authentication standards and defense-in-depth principles.
- Documentation & Communication (Weight: 10%): Clear PR notes and verbal defense during the live Google Meet review.
