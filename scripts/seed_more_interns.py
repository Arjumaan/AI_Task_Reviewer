import asyncio
from backend.app.core.database import AsyncSessionLocal
from backend.app.core.security import hash_password
from backend.app.models.user import User, UserRole
from sqlalchemy import select

INTERNS_TO_SEED = [
    {"email": "ananya@internal.company", "full_name": "Ananya Sen (Backend Systems Intern)"},
    {"email": "priyanshu@internal.company", "full_name": "Priyanshu Patel (AI/ML Intern)"},
    {"email": "rohan@internal.company", "full_name": "Rohan Verma (Fullstack Intern)"},
]

async def seed_interns():
    async with AsyncSessionLocal() as db:
        for intern_data in INTERNS_TO_SEED:
            res = await db.execute(select(User).where(User.email == intern_data["email"]))
            existing = res.scalars().first()
            if not existing:
                u = User(
                    email=intern_data["email"],
                    full_name=intern_data["full_name"],
                    hashed_password=hash_password("SecretPass123!"),
                    role=UserRole.INTERN,
                    is_active=True
                )
                db.add(u)
                print(f"Added intern: {intern_data['full_name']} <{intern_data['email']}>")
            else:
                print(f"Already exists: {intern_data['email']}")
        await db.commit()

if __name__ == "__main__":
    asyncio.run(seed_interns())
