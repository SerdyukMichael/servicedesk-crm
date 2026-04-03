"""
Pytest configuration for unit & integration tests.

Uses SQLite in-memory database — no external services required.
Run: pytest backend/tests/ -v
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Force test env vars BEFORE importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")

from sqlalchemy import text  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.main import app                    # noqa: E402
from app.models import User, Client, Equipment, EquipmentModel, Ticket, SparePart, Vendor, WorkTemplate, WorkTemplateStep, NotificationSetting  # noqa: E402
from app.core.security import hash_password, create_access_token  # noqa: E402

# ── In-memory SQLite engine ───────────────────────────────────────────────────

SQLALCHEMY_TEST_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Enable FK support in SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Fresh in-memory DB for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Disable FK constraints so tables can be dropped in any order
        with engine.connect() as conn:
            conn.execute(text("PRAGMA foreign_keys=OFF"))
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """FastAPI TestClient wired to the test DB."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── User factories ────────────────────────────────────────────────────────────

def make_user(db, email="user@test.com", full_name="Test User",
              roles=None, password="pass12345", is_active=True):
    u = User(
        email=email,
        full_name=full_name,
        password_hash=hash_password(password),
        roles=roles or ["engineer"],
        is_active=is_active,
        is_deleted=False,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def make_admin(db, email="admin@test.com", password="admin12345"):
    return make_user(db, email=email, full_name="Admin User",
                     roles=["admin"], password=password)


def make_svc_mgr(db, email="svcmgr@test.com"):
    return make_user(db, email=email, full_name="Service Manager", roles=["svc_mgr"])


def make_engineer(db, email="engineer@test.com"):
    return make_user(db, email=email, full_name="Engineer", roles=["engineer"])


def auth_headers(user_id: int, roles: list) -> dict:
    token = create_access_token({"sub": user_id, "roles": roles})
    return {"Authorization": f"Bearer {token}"}


def admin_headers(db) -> dict:
    u = make_admin(db)
    return auth_headers(u.id, u.roles)


# ── Object factories ──────────────────────────────────────────────────────────

def make_client(db, name="Тест Клиент", contract_type="none"):
    c = Client(name=name, contract_type=contract_type, is_deleted=False)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def make_equipment_model(db, name="NCR SelfServ 6683"):
    m = EquipmentModel(name=name, manufacturer="NCR", is_active=True)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def make_equipment(db, client_id, model_id, serial="SN-001"):
    e = Equipment(
        client_id=client_id,
        model_id=model_id,
        serial_number=serial,
        location="Test Location",
        status="active",
        is_deleted=False,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def make_ticket(db, client_id, equipment_id, created_by, priority="medium"):
    from datetime import datetime, timedelta
    sla_hours = {"critical": 4, "high": 8, "medium": 24, "low": 72}
    now = datetime.utcnow()
    t = Ticket(
        number=f"T-{now.strftime('%Y%m%d')}-0001",
        client_id=client_id,
        equipment_id=equipment_id,
        created_by=created_by,
        title="Test Ticket",
        description="Test description",
        type="repair",
        priority=priority,
        status="new",
        sla_deadline=now + timedelta(hours=sla_hours[priority]),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def make_spare_part(db, sku="SKU-001", quantity=10, min_quantity=2):
    p = SparePart(
        sku=sku,
        name="Test Part",
        category="consumable",
        unit="шт",
        quantity=quantity,
        min_quantity=min_quantity,
        unit_price=100.00,
        currency="RUB",
        is_active=True,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def make_vendor(db, name="Test Vendor"):
    v = Vendor(name=name, is_active=True)
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def make_work_template(db, name="Test Template", created_by=1):
    m = make_equipment_model(db, name=f"Model-{name}")
    t = WorkTemplate(
        name=name,
        equipment_model_id=m.id,
        is_active=True,
        created_by=created_by,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    step = WorkTemplateStep(template_id=t.id, step_order=1, description="Step 1")
    db.add(step)
    db.commit()
    db.refresh(t)
    return t
