# Google Cloud OAuth & External Integrations Guide

> [!IMPORTANT]
> **Proprietary External Dependency Disclosure**:  
> Google Meet, Google Calendar API, and Gmail API are **proprietary, external cloud services provided by Google LLC**, and are **NOT open-source components**. All other application code, speech engines, and LLM inference models in Task Reviewer AI are strictly 100% free and open-source software (FOSS).

---

## 1. Google Cloud Console Configuration

To integrate live Google Calendar scheduling (which generates authentic Google Meet conference links) and Gmail briefing summaries:

### Step 1: Create a Google Cloud Project
1. Navigate to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click **Select a project** > **New Project**.
3. Name the project `Task-Reviewer-AI` and click **Create**.

### Step 2: Enable Required APIs
1. In the navigation menu, go to **APIs & Services** > **Library**.
2. Search for and enable:
   - **Google Calendar API**
   - **Gmail API**

### Step 3: Configure OAuth Consent Screen
1. Go to **APIs & Services** > **OAuth consent screen**.
2. Select **User Type**:
   - Choose **Internal** if using a Google Workspace domain.
   - Choose **External** with test users for personal testing.
3. Fill in the App Information:
   - **App name**: `Task Reviewer AI`
   - **User support email**: Your company admin email.
   - **Developer contact information**: Your email address.
4. Click **Save and Continue**.

### Step 4: Add OAuth Scopes
Add the following required scopes:
- `https://www.googleapis.com/auth/calendar.events`: Create and manage Google Meet events.
- `https://www.googleapis.com/auth/gmail.send`: Send briefing and review summary emails.

### Step 5: Create OAuth 2.0 Client Credentials
1. Go to **APIs & Services** > **Credentials**.
2. Click **Create Credentials** > **OAuth client ID**.
3. Select **Application type**: **Web application**.
4. Set **Authorized redirect URIs**:
   - Local Development: `http://localhost:8000/api/v1/auth/google/callback`
   - Production: `https://your-domain.com/api/v1/auth/google/callback`
5. Click **Create** and download the client credentials or note the Client ID and Client Secret.

---

## 2. Environment Variables Configuration

Add the client credentials to your `.env` file:

```bash
GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="your-client-secret"
GOOGLE_REDIRECT_URI="http://localhost:8000/api/v1/auth/google/callback"
```

---

## 3. Built-In Offline Dry-Run Mode

If Google Cloud credentials are not configured, or if your machine is offline:
- The system automatically activates **Scheduling Dry-Run Mode**.
- Synthetic, format-compliant Google Meet URLs (`https://meet.google.com/meet-xxx-xxxx-xxx`) are generated deterministically.
- Briefing emails are composed, validated against idempotency constraints, and logged to audit records without dropping requests.
- No third-party paid APIs (e.g. Recall.ai, Deepgram, OpenAI) are ever invoked.
