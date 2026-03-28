# Backend Deployment Guide — ServiceDesk CRM

## 1. Local Development Setup

### Prerequisites
- Python 3.11+
- MySQL 8.0 running locally (or via Docker)

### Steps

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate          # Linux / macOS
# venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and fill in all required variables (see section 3)

# Apply database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger UI is available at http://localhost:8000/docs

---

## 2. Docker Deployment

### Start the full stack

```bash
# From the project root
docker-compose up -d --build

# Apply migrations after containers are running
docker compose exec backend alembic upgrade head
```

### Start only the database (for local backend development)

```bash
docker-compose up -d mysql
```

### Service URLs

| Service   | URL                          |
|-----------|------------------------------|
| Frontend  | http://localhost/            |
| Backend API | http://localhost:8000/docs |
| MySQL     | localhost:3306               |

### Useful Docker commands

```bash
# View backend logs
docker compose logs -f backend

# Rebuild only the backend image
docker compose up -d --build backend

# Run Alembic migrations
docker compose exec backend alembic upgrade head

# Create a new migration
docker compose exec backend alembic revision --autogenerate -m "describe change"

# Rollback last migration
docker compose exec backend alembic downgrade -1

# Open a Python shell inside the container
docker compose exec backend python
```

---

## 3. Environment Variables

Copy `.env.example` to `.env` and fill in the values.

| Variable | Description | Example |
|----------|-------------|---------|
| `MYSQL_ROOT_PASSWORD` | MySQL root password | `rootsecret` |
| `MYSQL_DATABASE` | Database name | `servicedesk` |
| `MYSQL_USER` | Application DB user | `servicedesk_user` |
| `MYSQL_PASSWORD` | Application DB user password | `dbpassword` |
| `DATABASE_URL` | SQLAlchemy connection string | `mysql+pymysql://servicedesk_user:dbpassword@mysql:3306/servicedesk` |
| `SECRET_KEY` | JWT signing secret (generate with command below) | `abc123...` |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime in minutes | `480` |
| `REDIS_URL` | Redis URL (optional, for future use) | `redis://redis:6379/0` |
| `SMTP_HOST` | SMTP server host (optional) | `smtp.example.com` |
| `SMTP_PORT` | SMTP server port | `587` |
| `SMTP_USER` | SMTP username (optional) | `noreply@example.com` |
| `SMTP_PASSWORD` | SMTP password (optional) | `smtppassword` |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token (optional) | `123456:ABC...` |
| `MAX_FILE_SIZE_MB` | Maximum upload file size in MB | `20` |

**Generate a SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 4. Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "ok", "app": "ServiceDesk CRM", "version": "2.0.0"}
```

---

## 5. First Login Credentials

After running `alembic upgrade head`, create the first admin user by inserting directly into the database or by running the seed script (if provided).

**Via MySQL CLI:**

```sql
-- Connect to MySQL
USE servicedesk;

-- Insert admin user (password: Admin1234!)
-- Password hash below corresponds to "Admin1234!" hashed with bcrypt
INSERT INTO users (email, full_name, password_hash, roles, is_active, is_deleted, created_at, updated_at)
VALUES (
  'admin@servicedesk.local',
  'Администратор',
  '$2b$12$wOT0gDFqvNUwRJhP7A5JUekmjX7GaCLjDcB2CQRN12L5IfU8fQlCy',
  '["admin"]',
  1, 0,
  NOW(), NOW()
);
```

Or use a one-liner with Python (run from `backend/` with the venv activated):

```bash
python - <<'EOF'
import sys
sys.path.insert(0, ".")
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import User
import json

db = SessionLocal()
admin = User(
    email="admin@servicedesk.local",
    full_name="Администратор",
    password_hash=hash_password("Admin1234!"),
    roles=["admin"],
    is_active=True,
    is_deleted=False,
)
db.add(admin)
db.commit()
print(f"Admin user created: id={admin.id}")
db.close()
EOF
```

**Default credentials:**

| Field | Value |
|-------|-------|
| Email | `admin@servicedesk.local` |
| Password | `Admin1234!` |

> Change the password immediately after first login.

**Login endpoint:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@servicedesk.local", "password": "Admin1234!"}'
```

Response will contain `access_token` — pass it as `Authorization: Bearer <token>` in all subsequent requests.

---

## 6. Available Roles

| Role | Description |
|------|-------------|
| `admin` | Full system access |
| `svc_mgr` | Service manager — manage tickets, clients, equipment |
| `engineer` | Field engineer — view and work on assigned tickets |
| `director` | Read-only access to all modules |
| `sales_mgr` | Manages clients and contracts |
| `accountant` | Manages invoices |
| `warehouse` | Manages spare parts stock |

---

## 7. API Reference

| Path | Description |
|------|-------------|
| `GET /docs` | Swagger UI (interactive) |
| `GET /redoc` | ReDoc documentation |
| `GET /health` | Health check |
| `POST /api/v1/auth/login` | Obtain JWT token |
| `GET /api/v1/auth/me` | Current user info |
| `GET /api/v1/users` | List users |
| `GET /api/v1/clients` | List clients |
| `GET /api/v1/equipment` | List equipment |
| `GET /api/v1/tickets` | List tickets |
| `GET /api/v1/work-templates` | List work templates |
| `GET /api/v1/parts` | List spare parts |
| `GET /api/v1/vendors` | List vendors |
| `GET /api/v1/invoices` | List invoices |
| `GET /api/v1/notifications` | Current user notifications |
