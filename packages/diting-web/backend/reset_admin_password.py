"""重置管理员密码脚本"""
import asyncio
from sqlalchemy import select, update
from diting_web.config import settings
from diting_web.db.session import AsyncSessionLocal
from diting_web.models.admin_user import AdminUser
from diting_web.core.security import get_password_hash


async def reset_password():
    """重置管理员密码为配置文件中的值"""
    print("=" * 60)
    print("DiTing 管理员密码重置")
    print("=" * 60)
    
    username = settings.admin_username
    password = settings.admin_password
    
    print(f"\n将重置以下账户的密码:")
    print(f"用户名: {username}")
    print(f"新密码: {password}")
    
    async with AsyncSessionLocal() as db:
        # 查找用户
        result = await db.execute(
            select(AdminUser).where(AdminUser.username == username)
        )
        user = result.scalar_one_or_none()
        
        if user is None:
            print(f"\n❌ 用户 '{username}' 不存在")
            print(f"\n正在创建新用户...")
            
            # 创建新用户
            new_user = AdminUser(
                username=username,
                hashed_password=get_password_hash(password),
                is_active=True,
            )
            db.add(new_user)
            await db.commit()
            
            print(f"✅ 用户创建成功！")
        else:
            print(f"\n找到用户: {user.username} (ID: {user.id})")
            print(f"正在更新密码...")
            
            # 更新密码
            user.hashed_password = get_password_hash(password)
            await db.commit()
            
            print(f"✅ 密码更新成功！")
        
        print(f"\n🎉 现在可以使用以下凭证登录:")
        print(f"   用户名: {username}")
        print(f"   密码: {password}")
        print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(reset_password())

