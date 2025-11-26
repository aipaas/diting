"""Initialize PostgreSQL extensions."""

import asyncio

from sqlalchemy import text

from diting_web.db.session import AsyncSessionLocal


async def init_extensions() -> None:
    """Initialize PostgreSQL extensions required by the application."""
    async with AsyncSessionLocal() as db:
        try:
            # Create uuid-ossp extension
            await db.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            print("✅ Created extension: uuid-ossp")
            
            # Create pg_trgm extension
            await db.execute(text('CREATE EXTENSION IF NOT EXISTS "pg_trgm"'))
            print("✅ Created extension: pg_trgm")
            
            await db.commit()
            print("✅ Database extensions initialized successfully")
        except Exception as e:
            print(f"⚠️  Warning: Could not create extensions: {e}")
            print("   Extensions may already exist or require superuser privileges")
            await db.rollback()


if __name__ == "__main__":
    asyncio.run(init_extensions())
