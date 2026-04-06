# v0.6.0 — Security Hardening

## Frontend
- Добавлен rate limiting на `/api/v1/auth/login` (5 req/min, burst=3) через nginx
- Security headers: X-Content-Type-Options, X-Frame-Options, Referrer-Policy
- Новый `nginx.prod.conf`: HTTP→HTTPS redirect, TLS 1.2/1.3, HSTS, OCSP stapling, CSP

## Backend
- CORS: `allow_origins=["*"]` → список из `ALLOWED_ORIGINS` env-переменной
- Swagger UI (`/docs`, `/redoc`) отключён в production при `DEBUG=false`
- Download endpoint `/tickets/{id}/attachments/{fid}/download` защищён JWT + row-level фильтрацией
- `assign_ticket` закрыт для `client_user` (только `admin`, `svc_mgr`)
- `change_ticket_status` требует явной роли + row-level фильтрацию
- `client_user` не может редактировать заявки и просматривать данные чужой организации
- 20 новых тестов безопасности (345 всего)

## Database
- Миграции в этой версии: нет (security-изменения не требовали схемных изменений)

## Инфраструктура
- Порты MySQL (3306), Redis (6379), Backend (8000) закрыты от внешнего доступа
- Volume-mount исходного кода убран из production-конфига
- `docker-compose.override.yml` — dev-оверрайд (не деплоится на сервер)
- Redis теперь требует пароль (`REDIS_PASSWORD`)

## Документы
- Обновлены: `docs/CHANGELOG.md`, `docs/RBAC_Matrix.md`, `docs/security-audit.md`
- Добавлен: `docs/DEPLOY_REMOTE.md`
