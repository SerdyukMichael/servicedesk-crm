"""
ServiceDesk CRM — Seed Script
==============================
Заполняет БД начальными данными: справочники, тестовые пользователи, демо-клиент.

Запуск:
    cd backend
    python ../scripts/seed.py

Требования:
    - Применены миграции: alembic upgrade head  (или запущен docker-compose с init.sql)
    - Переменная DATABASE_URL задана в .env или окружении
"""

import sys
import os

# Добавить backend/ в путь для импорта app.*
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from dotenv import load_dotenv
import json

load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))

DATABASE_URL = os.getenv('DATABASE_URL', 'mysql+pymysql://sduser:sdpass@localhost:3306/servicedesk')
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

engine = create_engine(DATABASE_URL, echo=False)

# ============================================================
# СПРАВОЧНИК: Модели оборудования
# ============================================================
EQUIPMENT_MODELS = [
    # Принтеры карт Matica
    {'name': 'Matica XID 580i',      'manufacturer': 'Matica Technologies', 'warranty_period_months': 12},
    {'name': 'Matica XID 8600',      'manufacturer': 'Matica Technologies', 'warranty_period_months': 12},
    {'name': 'Matica MC110',         'manufacturer': 'Matica Technologies', 'warranty_period_months': 12},
    # Банкоматы NCR
    {'name': 'NCR SelfServ 84',      'manufacturer': 'NCR Corporation',     'warranty_period_months': 24},
    {'name': 'NCR SelfServ 87',      'manufacturer': 'NCR Corporation',     'warranty_period_months': 24},
    {'name': 'NCR SelfServ 6627',    'manufacturer': 'NCR Corporation',     'warranty_period_months': 24},
    # Банкоматы Diebold Nixdorf
    {'name': 'Diebold Nixdorf DN 200',  'manufacturer': 'Diebold Nixdorf',  'warranty_period_months': 24},
    {'name': 'Diebold Nixdorf Procash 2050xe', 'manufacturer': 'Diebold Nixdorf', 'warranty_period_months': 24},
    # Банкоматы Nautilus Hyosung
    {'name': 'Nautilus Hyosung MX5600SE', 'manufacturer': 'Nautilus Hyosung', 'warranty_period_months': 12},
    {'name': 'Nautilus Hyosung MX8800', 'manufacturer': 'Nautilus Hyosung',  'warranty_period_months': 12},
    # Банкоматы Wincor (теперь DN)
    {'name': 'Wincor Nixdorf ProCash 2100xe', 'manufacturer': 'Diebold Nixdorf', 'warranty_period_months': 24},
    # Терминалы оплаты
    {'name': 'Ingenico iSC Touch 480', 'manufacturer': 'Ingenico',          'warranty_period_months': 12},
    {'name': 'VeriFone MX 915',        'manufacturer': 'VeriFone',          'warranty_period_months': 12},
]

# ============================================================
# СПРАВОЧНИК: Номенклатура запчастей
# ============================================================
SPARE_PARTS = [
    # --- Принтеры карт Matica ---
    {'article': 'MAT-CLN-580',  'name': 'Комплект чистки Matica XID 580i',            'unit': 'компл.'},
    {'article': 'MAT-RBN-YMCKO','name': 'Риббон YMCKO Matica 250 отпечатков',         'unit': 'шт.'},
    {'article': 'MAT-RBN-KO',   'name': 'Риббон KO (монохром) Matica 1000 отп.',      'unit': 'шт.'},
    {'article': 'MAT-HEAD-580', 'name': 'Печатающая головка Matica XID 580i',          'unit': 'шт.'},
    {'article': 'MAT-FEED-ROL', 'name': 'Ролик подачи карт Matica',                   'unit': 'шт.'},
    {'article': 'MAT-CARD-CLN', 'name': 'Карта чистки Matica (10 шт/упак.)',          'unit': 'упак.'},
    {'article': 'MAT-FILM-LAM', 'name': 'Ламинатная плёнка Matica 1000 карт',         'unit': 'рулон'},

    # --- Банкоматы NCR ---
    {'article': 'NCR-DISP-ROL', 'name': 'Ролик диспенсера купюр NCR SelfServ',        'unit': 'шт.'},
    {'article': 'NCR-FEED-ROL', 'name': 'Ролик подачи банкнот NCR',                   'unit': 'шт.'},
    {'article': 'NCR-PCKR-ROL', 'name': 'Ролик приёма банкнот NCR (Picker)',          'unit': 'шт.'},
    {'article': 'NCR-SENSOR-IR','name': 'ИК-датчик прохода банкнот NCR',              'unit': 'шт.'},
    {'article': 'NCR-BELT-TRNS','name': 'Ремень транспортёра NCR',                    'unit': 'шт.'},
    {'article': 'NCR-PRNT-HEAD','name': 'Печатающая головка чекового принтера NCR',   'unit': 'шт.'},
    {'article': 'NCR-PRNT-ROLL','name': 'Бумага чековая NCR 80mm х 300м',            'unit': 'рулон'},
    {'article': 'NCR-JRNL-ROLL','name': 'Бумага журнала аудита NCR 58mm х 200м',     'unit': 'рулон'},
    {'article': 'NCR-LOCK-SET', 'name': 'Комплект замков сейфа NCR',                  'unit': 'компл.'},
    {'article': 'NCR-SHUTTER',  'name': 'Шаттер (заслонка) кардридера NCR',           'unit': 'шт.'},

    # --- Банкоматы Diebold Nixdorf ---
    {'article': 'DN-DISP-ROL',  'name': 'Ролик диспенсера Diebold Nixdorf',           'unit': 'шт.'},
    {'article': 'DN-FEED-SET',  'name': 'Комплект роликов подачи DN ProCash',         'unit': 'компл.'},
    {'article': 'DN-BELT-ASM',  'name': 'Сборка ремня транспортёра DN',               'unit': 'шт.'},
    {'article': 'DN-SENSOR-SET','name': 'Комплект датчиков DN ProCash',               'unit': 'компл.'},
    {'article': 'DN-RCPT-PRNT', 'name': 'Блок чекового принтера DN',                  'unit': 'шт.'},
    {'article': 'DN-PAPER-80',  'name': 'Бумага для принтера DN 80mm x 300м',        'unit': 'рулон'},

    # --- Банкоматы Nautilus Hyosung ---
    {'article': 'NH-DISP-MOD',  'name': 'Модуль диспенсера Nautilus Hyosung MX5600', 'unit': 'шт.'},
    {'article': 'NH-FEED-ROL',  'name': 'Ролик подачи NH MX5600',                    'unit': 'шт.'},
    {'article': 'NH-SENSOR-IR', 'name': 'Инфракрасный датчик NH',                    'unit': 'шт.'},
    {'article': 'NH-BELT-FEED', 'name': 'Ремень механизма подачи NH',                'unit': 'шт.'},

    # --- Расходные материалы (универсальные) ---
    {'article': 'UNIV-THERMAL-80', 'name': 'Термобумага 80mm x 80м (чековый принтер)', 'unit': 'рулон'},
    {'article': 'UNIV-GREASE-10', 'name': 'Смазка техническая универсальная 10мл',   'unit': 'тюбик'},
    {'article': 'UNIV-CONTACT',   'name': 'Чистящий спрей для контактов 200мл',      'unit': 'баллон'},
    {'article': 'UNIV-WIPES-ATM', 'name': 'Чистящие салфетки для оборудования (50 шт)', 'unit': 'упак.'},
    {'article': 'UNIV-BRUSH-SET', 'name': 'Набор кистей для чистки механизмов',      'unit': 'набор'},

    # --- Кардридеры (моторизованные) ---
    {'article': 'CR-MOTOR-STD',  'name': 'Мотор кардридера стандартный',             'unit': 'шт.'},
    {'article': 'CR-HEAD-READ',  'name': 'Считывающая головка кардридера',            'unit': 'шт.'},
    {'article': 'CR-SHUTTER-U',  'name': 'Заслонка кардридера универсальная',        'unit': 'шт.'},
    {'article': 'CR-CLN-CARD10', 'name': 'Карта чистки кардридера (10 шт/уп.)',      'unit': 'упак.'},

    # --- Источники бесперебойного питания ---
    {'article': 'UPS-BAT-12V7',  'name': 'АКБ для UPS 12V 7Ah',                     'unit': 'шт.'},
    {'article': 'UPS-BAT-12V12', 'name': 'АКБ для UPS 12V 12Ah',                    'unit': 'шт.'},
]

# ============================================================
# НАЧАЛЬНЫЕ ПОЛЬЗОВАТЕЛИ СИСТЕМЫ
# ============================================================
INITIAL_USERS = [
    {
        'full_name':   'Системный администратор',
        'position':    'Системный администратор',
        'department':  'IT',
        'phone':       '+70000000000',
        'email':       'admin@servicedesk.local',
        'roles':       ['admin'],
        'password':    'ChangeMe123!',   # ОБЯЗАТЕЛЬНО сменить после первого входа
    },
    {
        'full_name':   'Руководитель сервиса',
        'position':    'Руководитель сервисной службы',
        'department':  'Сервис',
        'phone':       '+70000000001',
        'email':       'svc_mgr@servicedesk.local',
        'roles':       ['svc_mgr'],
        'password':    'ChangeMe123!',
    },
    {
        'full_name':   'Инженер Петров Иван',
        'position':    'Инженер по обслуживанию',
        'department':  'Сервис',
        'phone':       '+70000000002',
        'email':       'engineer1@servicedesk.local',
        'roles':       ['engineer'],
        'password':    'ChangeMe123!',
    },
    {
        'full_name':   'Инженер Сидорова Мария',
        'position':    'Инженер по обслуживанию',
        'department':  'Сервис',
        'phone':       '+70000000003',
        'email':       'engineer2@servicedesk.local',
        'roles':       ['engineer'],
        'password':    'ChangeMe123!',
    },
    {
        'full_name':   'Менеджер по продажам',
        'position':    'Менеджер по работе с клиентами',
        'department':  'Продажи',
        'phone':       '+70000000004',
        'email':       'sales@servicedesk.local',
        'roles':       ['sales_mgr'],
        'password':    'ChangeMe123!',
    },
    {
        'full_name':   'Кладовщик Склада',
        'position':    'Кладовщик',
        'department':  'Склад',
        'phone':       '+70000000005',
        'email':       'warehouse@servicedesk.local',
        'roles':       ['warehouse'],
        'password':    'ChangeMe123!',
    },
    {
        'full_name':   'Директор',
        'position':    'Генеральный директор',
        'department':  'Руководство',
        'phone':       '+70000000006',
        'email':       'director@servicedesk.local',
        'roles':       ['director'],
        'password':    'ChangeMe123!',
    },
]

# ============================================================
# ДЕМО-КЛИЕНТ (для первоначального тестирования)
# ============================================================
DEMO_CLIENTS = [
    {'name': 'ПАО Сбербанк',          'contract_type': 'premium',  'contract_number': 'SD-2026-001', 'address': 'г. Москва, ул. Вавилова, д. 19'},
    {'name': 'ВТБ Банк (ПАО)',         'contract_type': 'premium',  'contract_number': 'SD-2026-002', 'address': 'г. Москва, ул. Мясницкая, д. 35'},
    {'name': 'АО Альфа-Банк',          'contract_type': 'standard', 'contract_number': 'SD-2026-003', 'address': 'г. Москва, ул. Каланчёвская, д. 27'},
    {'name': 'ПАО Росбанк',            'contract_type': 'standard', 'contract_number': 'SD-2026-004', 'address': 'г. Москва, Сухаревская пл., д. 1'},
    {'name': 'КБ Тестовый (демо)',      'contract_type': 'none',     'contract_number': None,          'address': 'г. Москва, ул. Тестовая, д. 1'},
]


def upsert_equipment_models(session: Session):
    print('→ Справочник моделей оборудования...')
    for m in EQUIPMENT_MODELS:
        result = session.execute(
            text("SELECT id FROM equipment_models WHERE name = :name"),
            {'name': m['name']}
        ).fetchone()
        if not result:
            session.execute(
                text("""
                    INSERT INTO equipment_models (name, manufacturer, warranty_period_months)
                    VALUES (:name, :manufacturer, :wpm)
                """),
                {'name': m['name'], 'manufacturer': m['manufacturer'], 'wpm': m['warranty_period_months']}
            )
            print(f'   + {m["name"]}')
        else:
            print(f'   = {m["name"]} (уже существует)')
    session.commit()
    print(f'   Итого: {len(EQUIPMENT_MODELS)} моделей')


def upsert_spare_parts(session: Session):
    print('→ Номенклатура запчастей...')
    for p in SPARE_PARTS:
        result = session.execute(
            text("SELECT id FROM spare_parts WHERE article = :article"),
            {'article': p['article']}
        ).fetchone()
        if not result:
            session.execute(
                text("""
                    INSERT INTO spare_parts (article, name, unit, qty_main)
                    VALUES (:article, :name, :unit, 0)
                """),
                {'article': p['article'], 'name': p['name'], 'unit': p['unit']}
            )
            print(f'   + [{p["article"]}] {p["name"]}')
    session.commit()
    print(f'   Итого: {len(SPARE_PARTS)} позиций')


def upsert_users(session: Session):
    print('→ Пользователи системы...')
    for u in INITIAL_USERS:
        result = session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {'email': u['email']}
        ).fetchone()
        if not result:
            hashed = pwd_context.hash(u['password'])
            session.execute(
                text("""
                    INSERT INTO users
                        (full_name, position, department, phone, email, roles, password_hash, status, is_active)
                    VALUES
                        (:full_name, :position, :department, :phone, :email,
                         :roles, :password_hash, 'active', 1)
                """),
                {
                    'full_name':     u['full_name'],
                    'position':      u['position'],
                    'department':    u['department'],
                    'phone':         u['phone'],
                    'email':         u['email'],
                    'roles':         json.dumps(u['roles']),
                    'password_hash': hashed,
                }
            )
            # notification_settings создаются автоматически триггером trg_user_after_insert
            print(f'   + {u["full_name"]} ({u["email"]})')
        else:
            print(f'   = {u["email"]} (уже существует)')
    session.commit()
    print(f'   Итого: {len(INITIAL_USERS)} пользователей')


def upsert_demo_clients(session: Session):
    print('→ Демо-клиенты...')
    for c in DEMO_CLIENTS:
        result = session.execute(
            text("SELECT id FROM clients WHERE name = :name"),
            {'name': c['name']}
        ).fetchone()
        if not result:
            session.execute(
                text("""
                    INSERT INTO clients (name, contract_type, contract_number, address)
                    VALUES (:name, :ct, :cn, :address)
                """),
                {
                    'name':    c['name'],
                    'ct':      c['contract_type'],
                    'cn':      c['contract_number'],
                    'address': c['address'],
                }
            )
            print(f'   + {c["name"]}')
    session.commit()
    print(f'   Итого: {len(DEMO_CLIENTS)} клиентов')


def main():
    print('=' * 60)
    print('ServiceDesk CRM — Seed Script')
    print('=' * 60)
    print(f'DATABASE_URL: {DATABASE_URL}')
    print()

    with Session(engine) as session:
        upsert_equipment_models(session)
        upsert_spare_parts(session)
        upsert_users(session)
        upsert_demo_clients(session)

    print()
    print('=' * 60)
    print('Готово. Данные загружены.')
    print()
    print('Начальные учётные записи (сменить пароли при первом входе!):')
    print('-' * 60)
    for u in INITIAL_USERS:
        roles_str = ', '.join(u['roles'])
        print(f'  {u["email"]:40s} | роль: {roles_str}')
    print(f'  Пароль по умолчанию для всех: ChangeMe123!')
    print('=' * 60)


if __name__ == '__main__':
    main()
