"""
Verification of MeetingBaas Integration in AI Task Reviewer.
Tests bot-status adoption, live meeting association, and transcript sync pipeline.
"""
import httpx
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

def run_verification():
    print(">>> 1. Authenticating as Task Assigner...")
    auth_res = httpx.post(f"{BASE_URL}/auth/login", data={
        "username": "assigner@internal.company",
        "password": "SecretPass123!"
    })
    assert auth_res.status_code == 200, f"Login failed: {auth_res.text}"
    token = auth_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("   Assigner authenticated successfully.")

    print("\n>>> 2. Querying Live MeetingBaas Bot Status...")
    status_res = httpx.get(f"{BASE_URL}/meetings/bot-status", headers=headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    print("   Bot Status:", json.dumps(status_data, indent=2))

    print("\n>>> 3. Listing all MeetingBaas bots under the account...")
    bots_res = httpx.get(f"{BASE_URL}/meetings/baas/bots", headers=headers)
    assert bots_res.status_code == 200
    bots = bots_res.json()
    print(f"   Retrieved {len(bots)} bots from MeetingBaas account:")
    assert len(bots) > 0, "Expected at least one bot from MeetingBaas!"
    for b in bots:
        print(f"   - Bot ID: {b.get('bot_id')} | Status: {b.get('status')} | Duration: {b.get('duration')}s | URL: {b.get('meeting_url')}")

    target_bot = bots[0]
    target_bot_id = target_bot.get("bot_id")

    print("\n>>> 4. Associating Meeting with Task in Database...")
    tasks_res = httpx.get(f"{BASE_URL}/tasks/", headers=headers)
    tasks = tasks_res.json()
    target_task = tasks[0]
    task_id = target_task["id"]
    print(f"   Selected Task: {target_task['title']} (ID: {task_id})")

    # Schedule meeting with custom URL ktj-kjkj-xwk
    sched_res = httpx.post(f"{BASE_URL}/scheduling/schedule", json={
        "task_id": task_id,
        "meeting_type": "BRIEFING",
        "start_time_iso": "2026-10-23T11:00:00+05:30",
        "duration_minutes": 30,
        "timezone": "Asia/Kolkata",
        "custom_meet_url": "https://meet.google.com/meet/ktj-kjkj-xwk"
    }, headers=headers)
    assert sched_res.status_code == 201
    meeting = sched_res.json()
    meeting_id = meeting["id"]
    print(f"   Created Meeting record {meeting_id} with Google Meet URL: {meeting['google_meet_url']}")

    print(f"\n>>> 5. Testing Transcript & Recording Sync from MeetingBaas for bot {target_bot_id}...")
    sync_res = httpx.post(f"{BASE_URL}/meetings/{meeting_id}/sync-baas?bot_id={target_bot_id}", headers=headers)
    assert sync_res.status_code == 200
    sync_data = sync_res.json()
    print("   Sync result:", json.dumps(sync_data, indent=2))
    assert sync_data["success"] is True

    print("\n>>> 6. Fetching updated Meeting with Transcripts & Recordings...")
    meeting_res = httpx.get(f"{BASE_URL}/meetings/{meeting_id}", headers=headers)
    updated_meeting = meeting_res.json()
    print(f"   Meeting Status: {updated_meeting['status']}")
    print(f"   Recordings Count: {len(updated_meeting.get('recordings', []))}")
    if updated_meeting.get('recordings'):
        print(f"   Recording MP4 URL: {updated_meeting['recordings'][0]['file_path'][:90]}...")
        print(f"   Recording Duration: {updated_meeting['recordings'][0]['duration_seconds']}s")

    print("\n>>> ALL MEETINGBAAS INTEGRATION CHECKS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    run_verification()
