"""
Обновляет пароли для указанных пользователей.
Запускать: python scripts/update_passwords.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import User

UPDATES = [
    ("admin@servicedesk.local",   "vk4jqDDelf$@!2xw"),
    ("engineer@servicedesk.local","4nI#YcZk!MNAfdRT"),
    ("manager@servicedesk.local", "cyfLw$vRwtT9tLB7"),
]

def run():
    db = SessionLocal()
    for email, new_pwd in UPDATES:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.password_hash = hash_password(new_pwd)
            print(f"  OK  {email}")
        else:
            print(f"  --  {email}: не найден")
    db.commit()
    db.close()
    print("Готово.")

if __name__ == "__main__":
    run()
