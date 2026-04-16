"""
Seed-скрипт: добавляет недостающих сотрудников и исправляет устаревшие роли.
Безопасен для повторного запуска (idempotent).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.core.security import hash_password as get_password_hash
from app.models import User

# Пароль по умолчанию для всех новых пользователей
DEFAULT_PASSWORD = "ServiceDesk2026!"

USERS_TO_SEED = [
    # email                          full_name               roles
    ("engineer2@servicedesk.local",  "Смирнов Дмитрий",      ["engineer"]),
    ("svc.manager@servicedesk.local","Козлова Наталья",      ["svc_mgr"]),
    ("sales@servicedesk.local",      "Федоров Артём",        ["sales_mgr"]),
    ("warehouse@servicedesk.local",  "Попов Сергей",         ["warehouse"]),
    ("accountant@servicedesk.local", "Волкова Ирина",        ["accountant"]),
    ("director@servicedesk.local",   "Новиков Михаил",       ["director"]),
]

# Роли, которые нужно исправить (email → новые роли)
ROLES_FIX = {
    "manager@servicedesk.local": ["svc_mgr"],
}


def run():
    db = SessionLocal()
    created, fixed, skipped = 0, 0, 0

    # Исправляем устаревшие роли
    for email, new_roles in ROLES_FIX.items():
        user = db.query(User).filter(User.email == email).first()
        if user:
            if user.roles != new_roles:
                print(f"  FIX  {email}: {user.roles} → {new_roles}")
                user.roles = new_roles
                fixed += 1
            else:
                print(f"  OK   {email}: роль уже {new_roles}")

    # Добавляем новых сотрудников
    for email, full_name, roles in USERS_TO_SEED:
        exists = db.query(User).filter(User.email == email).first()
        if exists:
            print(f"  SKIP {email}: уже существует")
            skipped += 1
            continue

        user = User(
            email=email,
            full_name=full_name,
            password_hash=get_password_hash(DEFAULT_PASSWORD),
            roles=roles,
            is_active=True,
            is_deleted=False,
        )
        db.add(user)
        print(f"  ADD  {email} ({roles[0]}) — {full_name}")
        created += 1

    db.commit()
    db.close()
    print(f"\nГотово: создано {created}, исправлено {fixed}, пропущено {skipped}")
    print(f"Пароль для новых пользователей: {DEFAULT_PASSWORD}")


if __name__ == "__main__":
    run()
