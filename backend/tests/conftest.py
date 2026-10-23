"""
Pytest Fixtures and Async Test Client Configuration.
"""
import sys
from pathlib import Path
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import event

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.core.security import hash_password, create_access_token
from backend.app.models.user import User, UserRole

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

# Configure SQLite memory engine
test_engine = create_async_engine(TEST_DB_URL, echo=False)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()
        
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def test_users(db_session: AsyncSession):
    admin = User(
        email="test_admin@company.com",
        full_name="Test Admin",
        hashed_password=hash_password("AdminPass123!"),
        role=UserRole.ADMIN,
        is_active=True
    )
    assigner = User(
        email="test_assigner@company.com",
        full_name="Test Assigner",
        hashed_password=hash_password("AssignerPass123!"),
        role=UserRole.ASSIGNER,
        is_active=True
    )
    intern = User(
        email="test_intern@company.com",
        full_name="Test Intern",
        hashed_password=hash_password("InternPass123!"),
        role=UserRole.INTERN,
        is_active=True
    )
    db_session.add_all([admin, assigner, intern])
    await db_session.commit()
    await db_session.refresh(admin)
    await db_session.refresh(assigner)
    await db_session.refresh(intern)
    return {"admin": admin, "assigner": assigner, "intern": intern}

@pytest.fixture
def auth_headers():
    def _make_headers(user: User):
        token = create_access_token(data={"sub": user.id, "role": user.role.value, "email": user.email})
        return {"Authorization": f"Bearer {token}"}
    return _make_headers
