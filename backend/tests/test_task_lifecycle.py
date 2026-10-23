"""
Task Creation, Document Upload, Draft Extraction, and Approval Tests.
"""
import io
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_task_creation_and_approval(client: AsyncClient, test_users, auth_headers):
    assigner = test_users["assigner"]
    intern = test_users["intern"]
    assigner_headers = auth_headers(assigner)
    intern_headers = auth_headers(intern)

    # 1. Assigner creates task
    create_res = await client.post(
        "/api/v1/tasks/",
        json={"title": "Build Authentication Gateway", "intern_id": intern.id},
        headers=assigner_headers
    )
    assert create_res.status_code == 201
    task_id = create_res.json()["id"]

    # 2. Assigner uploads assignment brief text
    fake_doc = io.BytesIO(b"Assignment Brief:\nImplement JWT and bcrypt authentication gateway.\nDeliverables: code, tests, docs.")
    files = {"file": ("brief.txt", fake_doc, "text/plain")}
    upload_res = await client.post(
        f"/api/v1/tasks/{task_id}/upload",
        files=files,
        headers=assigner_headers
    )
    assert upload_res.status_code == 200
    assert upload_res.json()["filename"] == "brief.txt"

    # 3. Extract draft specification
    draft_res = await client.post(
        f"/api/v1/tasks/{task_id}/extract-draft",
        headers=assigner_headers
    )
    assert draft_res.status_code == 200
    draft_data = draft_res.json()
    assert len(draft_data["requirements"]) > 0

    # 4. Intern cannot approve specification (Must be 403 Forbidden)
    intern_approve = await client.post(
        f"/api/v1/tasks/{task_id}/approve-specification",
        json=draft_data,
        headers=intern_headers
    )
    assert intern_approve.status_code == 403

    # 5. Assigner approves specification
    approve_res = await client.post(
        f"/api/v1/tasks/{task_id}/approve-specification",
        json=draft_data,
        headers=assigner_headers
    )
    assert approve_res.status_code == 200
    approved_task = approve_res.json()
    assert approved_task["status"] == "SPECIFICATION_APPROVED"
    assert approved_task["current_version_id"] is not None
