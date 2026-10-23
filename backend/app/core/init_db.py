"""
Database Schema Initialization and Migration Helper.
"""
import asyncio
from backend.app.core.database import engine, Base
import backend.app.models # Register all models

async def init_database():
    print("[DATABASE] Creating all tables according to SQLAlchemy metadata...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[DATABASE] Successfully created and verified all tables!")

if __name__ == "__main__":
    asyncio.run(init_database())
