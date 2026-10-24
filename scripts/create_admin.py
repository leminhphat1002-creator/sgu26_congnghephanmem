"""Tạo/đổi mật khẩu quản trị từ terminal, không có tài khoản mặc định.

python -m scripts.create_admin --username admin --generate
python -m scripts.create_admin --username admin --reset
"""

import argparse
import getpass
import secrets
from pathlib import Path

from sqlalchemy import delete, select

from app.core.db import get_sessionmaker
from app.modules.admin.models import AdminSession, AdminUser
from app.modules.admin.passwords import hash_password
from app.modules.admin.repository import AdminRepository


def main():
    parser = argparse.ArgumentParser(description="Create a local administrator")
    parser.add_argument("--username", default="admin")
    parser.add_argument(
        "--generate", action="store_true", help="Save a random password in data/admin-login.txt"
    )
    parser.add_argument("--reset", action="store_true", help="Explicitly reset an existing account")
    args = parser.parse_args()
    username = args.username.strip()
    if not username or len(username) > 80:
        parser.error("Username must have 1-80 characters")
    with get_sessionmaker()() as session:
        user = session.scalar(select(AdminUser).where(AdminUser.username == username))
        if user and not args.reset:
            parser.error("Account already exists; use --reset to change its password")
        password = (
            secrets.token_urlsafe(18)
            if args.generate
            else getpass.getpass("Password (12+ characters): ")
        )
        if not args.generate and password != getpass.getpass("Confirm password: "):
            parser.error("Passwords do not match")
        encoded = hash_password(password)
        if user is None:
            user = AdminUser(username=username, password_hash=encoded)
            session.add(user)
        else:
            user.password_hash = encoded
            session.execute(delete(AdminSession).where(AdminSession.user_id == user.id))
        session.commit()
        AdminRepository(session).record(
            username, "reset_account" if args.reset else "create_account"
        )
    if args.generate:
        target = Path("data/admin-login.txt")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            f"Username: {username}\nPassword: {password}\nLogin: /admin\n", encoding="utf-8"
        )
        print("Credentials saved to data/admin-login.txt (ignored by Git).")
    print("Administrator ready. Open /admin to sign in.")


if __name__ == "__main__":
    main()
