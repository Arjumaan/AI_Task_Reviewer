"""
Meeting Scheduling, Rescheduling, and Timezone Tests.
"""
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_scheduling_lifecycle(client: AsyncClient, test_users, auth_headers):
    assigner = test_users["assigner"]
    headers = auth_headers(assigner)

    # 1. Create task
    task_res = await client.post("/api/v1/tasks/", json={"title": "Data Pipeline Task"}, headers=headers)
    task_id = task_res.json()["id"]

    # 2. Cannot schedule briefing while task is in DRAFT status
    bad_sched = await client.post(
        "/api/v1/scheduling/schedule",
        json={
            "task_id": task_id,
            "meeting_type": "BRIEFING",
            "start_time_iso": "2026-10-25T14:00:00+05:30",
            "duration_minutes": 30,
            "timezone": "Asia/Kolkata"
        },
        headers=headers
    )
    assert bad_sched.status_code == 400

    # 3. Upload & Approve
    await client.post(
        f"/api/v1/tasks/{task_id}/upload",
        files={"file": ("brief.txt", b"Build pipeline with tests.", "text/plain")},
        headers=headers
    )
    draft_res = await client.post(f"/api/v1/tasks/{task_id}/extract-draft", headers=headers)
    await client.post(f"/api/v1/tasks/{task_id}/approve-specification", json=draft_res.json(), headers=headers)

    # 4. Schedule briefing
    sched_res = await client.post(
        "/api/v1/scheduling/schedule",
        json={
            "task_id": task_id,
            "meeting_type": "BRIEFING",
            "start_time_iso": "2026-10-25T14:00:00+05:30",
            "duration_minutes": 30,
            "timezone": "Asia/Kolkata"
        },
        headers=headers
    )
    assert sched_res.status_code == 201
    meeting_data = sched_res.json()
    meeting_id = meeting_data["id"]
    assert "https://meet.google.com/" in meeting_data["google_meet_url"]
    assert meeting_data["is_dry_run"] is True

    # 5. Reschedule meeting
    resched_res = await client.post(
        f"/api/v1/scheduling/meetings/{meeting_id}/reschedule",
        json={
            "new_start_time_iso": "2026-10-26T10:00:00+05:30",
            "duration_minutes": 45,
            "reason": "Host requested morning slot."
        },
        headers=headers
    )
    assert resched_res.status_code == 200
    assert resched_res.json()["status"] == "RESCHEDULED"
