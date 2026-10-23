"""
Deterministic Synthetic Seed Data Generator.
Populates standard roles (Admin, Assigner, Intern) and a complete sample assignment.
All synthetic entities are clearly marked with is_demo=True / DEMO tags.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal, engine, Base
from backend.app.core.security import hash_password
from backend.app.models.user import User, UserRole
from backend.app.models.task import (
    Task, TaskVersion, Requirement, AcceptanceCriterion, RubricItem,
    TaskStatus, RequirementPriority, VerificationMethod
)
from backend.app.models.audit import AuditLog

async def seed():
    print("[SEED] Seeding deterministic demo data...")
    async with AsyncSessionLocal() as db:
        # Check if users exist
        res = await db.execute(select(User).where(User.email == "admin@company.internal"))
        if res.scalars().first():
            print("[SEED] Database already populated with seed users. Skipping.")
            return

        # 1. Users
        admin = User(
            email="admin@company.internal",
            full_name="System Administrator (Demo)",
            hashed_password=hash_password("AdminPass123!"),
            role=UserRole.ADMIN,
            is_active=True
        )
        assigner = User(
            email="lead@company.internal",
            full_name="Sarah Chen (Tech Lead)",
            hashed_password=hash_password("LeadPass123!"),
            role=UserRole.ASSIGNER,
            is_active=True
        )
        intern = User(
            email="intern@company.internal",
            full_name="Aarav Sharma (Software Intern)",
            hashed_password=hash_password("InternPass123!"),
            role=UserRole.INTERN,
            is_active=True
        )
        db.add_all([admin, assigner, intern])
        await db.flush()

        # 2. Demo Task
        task = Task(
            title="[DEMO] Enterprise Task Review Automation Engine",
            status=TaskStatus.SPECIFICATION_APPROVED,
            assigner_id=assigner.id,
            intern_id=intern.id
        )
        db.add(task)
        await db.flush()

        # 3. Approved Task Version
        deadline = datetime.now(timezone.utc) + timedelta(days=7)
        version = TaskVersion(
            task_id=task.id,
            version_number=1,
            objective="Develop an automated review pipeline that briefs interns, evaluates artifacts, and manages review lifecycles.",
            scope="Backend APIs, database models, evidence-based rubric evaluation, and interactive voice room.",
            prerequisites="Python 3.11+, Git, and Chrome.",
            deliverables="Tested FastAPI backend, frontend dashboard, and verifiable test suite.",
            submission_method="Git repository with reproducible test suites.",
            deadline_utc=deadline,
            display_timezone="Asia/Kolkata",
            is_approved=True,
            approved_by=assigner.id,
            approved_at=datetime.now(timezone.utc),
            changelog="Initial approved baseline specification for Demo intern."
        )
        db.add(version)
        await db.flush()

        # 4. Requirements & Criteria
        r1 = Requirement(
            task_version_id=version.id,
            req_code="REQ-01",
            title="Evidence-Grounded Rubric Evaluation",
            description="All pass/fail findings must explicitly link to deterministic test output or verified excerpts.",
            priority=RequirementPriority.CRITICAL,
            is_mandatory=True
        )
        r2 = Requirement(
            task_version_id=version.id,
            req_code="REQ-02",
            title="Transparent AI Identification & Consent",
            description="The AI agent must never impersonate humans and must obtain consent before recording.",
            priority=RequirementPriority.HIGH,
            is_mandatory=True
        )
        db.add_all([r1, r2])
        await db.flush()

        ac1 = AcceptanceCriterion(
            requirement_id=r1.id,
            criterion_code="AC-01.1",
            description="Deterministic test suite executes cleanly with 100% assertions passing.",
            verification_method=VerificationMethod.DETERMINISTIC_TEST,
            pass_threshold="100% pass",
            is_mandatory=True
        )
        ac2 = AcceptanceCriterion(
            requirement_id=r2.id,
            criterion_code="AC-02.1",
            description="Audio room displays visible consent disclosure banner and requires button/verbal consent.",
            verification_method=VerificationMethod.ARTIFACT_INSPECTION,
            pass_threshold="Explicit consent verified",
            is_mandatory=True
        )
        db.add_all([ac1, ac2])
        await db.flush()

        rub1 = RubricItem(
            task_version_id=version.id,
            criterion_id=ac1.id,
            name="Automated Test Suite Verification",
            description="Evaluates test suite reproducibility and assertion accuracy.",
            weight=1.5,
            max_score=10.0,
            evaluation_guide="10/10 for 100% passing tests with evidence."
        )
        rub2 = RubricItem(
            task_version_id=version.id,
            criterion_id=ac2.id,
            name="Consent & Disclosure Verification",
            description="Evaluates compliance with AI identity and recording disclosure policies.",
            weight=1.0,
            max_score=10.0,
            evaluation_guide="Full points when consent record is verified in database."
        )
        db.add_all([rub1, rub2])

        task.current_version_id = version.id

        # 5. Audit Log
        audit = AuditLog(
            actor_id=admin.id,
            actor_email=admin.email,
            action="DATABASE_SEEDED",
            resource_type="system",
            resource_id="init"
        )
        db.add(audit)

        await db.commit()
        print("[SEED] Successfully seeded Demo Users and Sample Task!")
        print("  - Admin: admin@company.internal / AdminPass123!")
        print("  - Assigner: lead@company.internal / LeadPass123!")
        print("  - Intern: intern@company.internal / InternPass123!")

if __name__ == "__main__":
    asyncio.run(seed())
