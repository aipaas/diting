"""检查管理员账户脚本"""
import asyncio
from sqlalchemy import select
from diting_web.config import settings
from diting_web.db.session import AsyncSessionLocal
from diting_web.models.admin_user import AdminUser
from diting_web.core.security import verify_password, get_password_hash


async def check_admin():
    """检查管理员账户"""
    print("=" * 60)
    print("DiTing 管理员账户检查")
    print("=" * 60)
    
    # 显示配置的账户信息
    print(f"\n📋 配置信息:")
    print(f"   用户名: {settings.admin_username}")
    print(f"   密码: {settings.admin_password}")
    
    # 连接数据库
    async with AsyncSessionLocal() as db:
        # 查询管理员用户
        result = await db.execute(
            select(AdminUser).where(AdminUser.username == settings.admin_username)
        )
        user = result.scalar_one_or_none()
        
        if user is None:
            print(f"\n❌ 错误: 用户 '{settings.admin_username}' 不存在于数据库中")
            print(f"\n💡 解决方案:")
            print(f"   运行以下命令初始化管理员账户:")
            print(f"   uv run python -m diting_web.scripts.init_admin")
            return
        
        print(f"\n✅ 用户存在于数据库")
        print(f"   用户ID: {user.id}")
        print(f"   用户名: {user.username}")
        print(f"   激活状态: {user.is_active}")
        print(f"   哈希密码: {user.hashed_password[:50]}...")
        
        # 测试密码验证
        print(f"\n🔐 密码验证测试:")
        is_valid = verify_password(settings.admin_password, user.hashed_password)
        
        if is_valid:
            print(f"   ✅ 密码验证成功！")
            print(f"\n🎉 账户正常，可以使用以下凭证登录:")
            print(f"   用户名: {user.username}")
            print(f"   密码: {settings.admin_password}")
        else:
            print(f"   ❌ 密码验证失败！")
            print(f"\n💡 解决方案:")
            print(f"   数据库中的密码与配置不匹配")
            print(f"   选项1: 重新初始化管理员（会更新密码）")
            
            # 提供更新密码的选项
            print(f"\n是否要更新密码到配置文件中的值？(yes/no)")
            choice = input().strip().lower()
            
            if choice == 'yes':
                # 更新密码
                new_hash = get_password_hash(settings.admin_password)
                user.hashed_password = new_hash
                await db.commit()
                
                # 验证更新
                is_valid_now = verify_password(settings.admin_password, user.hashed_password)
                if is_valid_now:
                    print(f"\n✅ 密码已更新并验证成功！")
                    print(f"   用户名: {user.username}")
                    print(f"   密码: {settings.admin_password}")
                else:
                    print(f"\n❌ 密码更新失败")
            else:
                print(f"\n跳过密码更新")
        
        # 测试所有用户
        print(f"\n📊 数据库中所有管理员账户:")
        all_users_result = await db.execute(select(AdminUser))
        all_users = all_users_result.scalars().all()
        
        if not all_users:
            print(f"   没有找到任何管理员账户")
        else:
            for u in all_users:
                print(f"   - ID: {u.id}")
                print(f"     用户名: {u.username}")
                print(f"     激活: {u.is_active}")
                print(f"     最后登录: {u.last_login_at}")
                print()


if __name__ == "__main__":
    asyncio.run(check_admin())

