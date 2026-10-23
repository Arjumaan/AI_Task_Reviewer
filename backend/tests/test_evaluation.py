"""
Evaluation Engine, Evidence Verification, and Revision Loop Tests.
"""
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_evidence_backed_evaluation_flow(client: AsyncClient, test_users, auth_headers):
    assigner = test_users["assigner"]
    intern = test_users["intern"]
    assigner_headers = auth_headers(assigner)
    intern_headers = auth_headers(intern)

    # Setup task, version, and requirements
    task_res = await client.post("/api/v1/tasks/", json={"title": "ML Model Pipeline", "intern_id": intern.id}, headers=assigner_headers)
    task_id = task_res.json()["id"]

    await client.post(
        f"/api/v1/tasks/{task_id}/upload",
        files={"file": ("brief.txt", b"Build ML pipeline. Must pass all unit tests.", "text/plain")},
        headers=assigner_headers
    )
    draft_res = await client.post(f"/api/v1/tasks/{task_id}/extract-draft", headers=assigner_headers)
    await client.post(f"/api/v1/tasks/{task_id}/approve-specification", json=draft_res.json(), headers=assigner_headers)

    # 1. Intern submits deliverables
    sub_res = await client.post(
        "/api/v1/submissions/",
        json={
            "task_id": task_id,
            "repository_url": "https://github.com/intern/ml-pipeline",
            "commit_hash": "a1b2c3d4e5f6",
            "notes": "Completed initial implementation."
        },
        headers=intern_headers
    )
    assert sub_res.status_code == 201
    sub_data = sub_res.json()
    round_id = sub_data["review_rounds"][0]["id"]

    # 2. Evaluation Scenario A: Tests failed -> Must produce REVISION_REQUIRED
    eval_fail = await client.post(
        f"/api/v1/reviews/{round_id}/evaluate",
        json={
            "test_output": "FAILED tests/test_core.py::test_inference - AssertionError: 0.5 != 1.0",
            "repo_url": "https://github.com/intern/ml-pipeline",
            "meeting_transcripts": ["Intern: I attempted the pipeline but test_inference is failing."]
        },
        headers=assigner_headers
    )
    assert eval_fail.status_code == 200
    fail_data = eval_fail.json()
    assert fail_data["outcome"] == "REVISION_REQUIRED"
    assert len(fail_data["revision_requests"]) > 0

    # 3. Intern submits Appeal -> Must transition to HUMAN_REVIEW_REQUIRED
    appeal_res = await client.post(
        f"/api/v1/reviews/{round_id}/appeal",
        json={"reason": "The test failure was due to a floating point tolerance mismatch on GPU."},
        headers=intern_headers
    )
    assert appeal_res.status_code == 200
    assert appeal_res.json()["outcome"] == "HUMAN_REVIEW_REQUIRED"

    # 4. Evaluation Scenario B: Tests passed with verified evidence -> Must produce PASS
    # Intern creates submission for next round
    sub_pass = await client.post(
        "/api/v1/submissions/",
        json={
            "task_id": task_id,
            "repository_url": "https://github.com/intern/ml-pipeline",
            "commit_hash": "f6e5d4c3b2a1",
            "notes": "Fixed tolerance and added reproducible fixtures."
        },
        headers=intern_headers
    )
    round_2_id = sub_pass.json()["review_rounds"][0]["id"]

    eval_pass = await client.post(
        f"/api/v1/reviews/{round_2_id}/evaluate",
        json={
            "test_output": "14 passed, 0 failed in 0.85s (100% pass)",
            "repo_url": "https://github.com/intern/ml-pipeline",
            "meeting_transcripts": [
                "AI Reviewer: Please explain your architectural choices.",
                "Intern: We implemented reproducible test suites with strict assertion checks and container isolation."
            ]
        },
        headers=assigner_headers
    )
    assert eval_pass.status_code == 200
    pass_data = eval_pass.json()
    assert pass_data["outcome"] == "PASS"
    assert pass_data["total_score"] >= 80.0
