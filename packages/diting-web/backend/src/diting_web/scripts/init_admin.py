"""Initialize admin user script."""

import asyncio

from sqlalchemy import select

from diting_web.auth import get_password_hash
from diting_web.config import settings
from diting_web.db.session import AsyncSessionLocal
from diting_web.models.user import User


async def init_admin_user() -> None:
    """Initialize admin user."""
    async with AsyncSessionLocal() as db:
        # Check if admin user exists
        result = await db.execute(
            select(User).where(User.username == settings.admin_username)
        )
        existing_admin = result.scalar_one_or_none()

        if existing_admin:
            print(f"✅ Admin user '{settings.admin_username}' already exists")
            # Update to ensure is_admin is True
            if not existing_admin.is_admin:
                existing_admin.is_admin = True
                await db.commit()
                print(f"   Updated is_admin flag to True")
            return

        # Create admin user
        admin = User(
            username=settings.admin_username,
            email=f"{settings.admin_username}@admin.local",  # Default email
            hashed_password=get_password_hash(settings.admin_password),
            is_active=True,
            is_admin=True,  # Set admin flag
        )
        db.add(admin)
        await db.commit()

        print(f"✅ Admin user '{settings.admin_username}' created successfully")
        print(f"   Username: {settings.admin_username}")
        print(f"   Password: {settings.admin_password}")
        print(f"   Email: {admin.email}")
        print(f"   Is Admin: True")


if __name__ == "__main__":
    asyncio.run(init_admin_user())

