# Release Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать инфраструктуру процесса релиза: папку `releases/`, артефакты текущей версии v0.6.0, git-тег, обновить CLAUDE.md.

**Architecture:** Чисто файловая и git-инфраструктура — никакого нового кода. Каждая версия хранит два файла: `CHANGES.md` (что изменилось по модулям) и `db_migrations.sql` (SQL-дамп Alembic-миграций). Текущая версия v0.6.0 бэкфиллируется вручную.

**Tech Stack:** git, Alembic (alembic upgrade --sql), Docker Compose, bash

---

## Файлы плана

| Действие | Путь |
|----------|------|
| Создать | `releases/v0.6.0/CHANGES.md` |
| Создать | `releases/v0.6.0/db_migrations.sql` |
| Изменить | `CLAUDE.md` — добавить секцию «Процесс релиза» |

---

## Task 1: Создать структуру releases/ и артефакты v0.6.0

**Files:**
- Create: `releases/v0.6.0/CHANGES.md`
- Create: `releases/v0.6.0/db_migrations.sql`

- [ ] **Step 1: Создать папку и CHANGES.md для v0.6.0**

Содержимое `releases/v0.6.0/CHANGES.md`:

```markdown
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
```

- [ ] **Step 2: Сгенерировать db_migrations.sql**

Запустить команду:
```bash
docker compose exec backend alembic upgrade head --sql > releases/v0.6.0/db_migrations.sql
```

Проверить что файл не пустой:
```bash
wc -l releases/v0.6.0/db_migrations.sql
```
Ожидаемый результат: несколько сотен строк SQL (все миграции 001–009).

> **Примечание:** Если база уже применила все миграции и `--sql` выдаёт пустой файл, это нормально — значит на чистой базе всё применится заново. Можно сгенерировать дамп от base до head:
> ```bash
> docker compose exec backend alembic upgrade base:head --sql > releases/v0.6.0/db_migrations.sql
> ```

- [ ] **Step 3: Закоммитить артефакты**

```bash
git add releases/
git commit -m "chore: add releases/ structure, backfill v0.6.0 artifacts"
```

---

## Task 2: Добавить секцию «Процесс релиза» в CLAUDE.md

**Files:**
- Modify: `CLAUDE.md` — добавить секцию перед «Git — правила»

- [ ] **Step 1: Добавить секцию в CLAUDE.md**

Найти в `CLAUDE.md` секцию `## Git — правила` и вставить перед ней:

```markdown
## Процесс релиза

Полный spec: `docs/superpowers/specs/2026-04-06-release-workflow-design.md`

### 6 шагов релиза

1. **Разработка** — код + тесты (`docker compose exec backend pytest tests/ -v`)
2. **Проверка** — разработчик проверяет на локальном стенде, фиксируем замечания
3. **Формирование релиза** (Claude, по команде):
   - Создать `releases/vX.Y.Z/CHANGES.md` (Frontend / Backend / Database / Инфраструктура / Документы)
   - Сгенерировать `releases/vX.Y.Z/db_migrations.sql`:
     ```bash
     docker compose exec backend alembic upgrade head --sql > releases/vX.Y.Z/db_migrations.sql
     ```
   - Показать оба файла разработчику
4. **Одобрение** — разработчик читает артефакты и даёт ОК
5. **Git** (Claude, после ОК):
   ```bash
   git add .
   git commit -m "feat: vX.Y.Z — краткое название"
   git tag vX.Y.Z
   git push && git push --tags
   ```
6. **Деплой на боевой сервер** (Claude):
   ```bash
   # SSH на 188.120.243.122 → cd ~/servicedesk-crm
   git pull origin main
   docker compose up -d --build
   docker compose exec backend alembic upgrade head
   ```

### Версионирование

| Сегмент | Когда меняется |
|---------|---------------|
| X (major) | Breaking changes, кардинальная смена архитектуры |
| Y (minor) | Новая функциональность (UC, модуль) |
| Z (patch) | Багфиксы без новых фич |

### Структура releases/

```
releases/
└── vX.Y.Z/
    ├── CHANGES.md        # что изменилось по модулям
    └── db_migrations.sql # SQL-дамп Alembic-миграций для проверки
```

```

- [ ] **Step 2: Проверить что CLAUDE.md читается корректно**

Открыть файл и убедиться что секция стоит на месте, нет артефактов форматирования.

- [ ] **Step 3: Закоммитить**

```bash
git add CLAUDE.md
git commit -m "docs: add release process to CLAUDE.md"
```

---

## Task 3: Поставить git-тег v0.6.0 и запушить

**Files:** только git-операции, файлов не создаём.

- [ ] **Step 1: Проверить текущее состояние**

```bash
git log --oneline -5
git tag
```

Убедиться что теги пусты (ни одного тега нет), HEAD — последний коммит.

- [ ] **Step 2: Поставить тег v0.6.0**

```bash
git tag v0.6.0
```

- [ ] **Step 3: Запушить коммиты и тег**

```bash
git push
git push --tags
```

Ожидаемый результат: в `git push --tags` увидим `* [new tag] v0.6.0 -> v0.6.0`.

- [ ] **Step 4: Проверить**

```bash
git tag
git show v0.6.0 --stat
```

Ожидаемый результат: тег `v0.6.0` присутствует, `git show` показывает коммит с файлами релиза.

---

## Self-Review (план против spec)

| Требование из spec | Задача |
|--------------------|--------|
| `releases/vX.Y.Z/CHANGES.md` структура | Task 1 Step 1 |
| `releases/vX.Y.Z/db_migrations.sql` генерация | Task 1 Step 2 |
| Бэкфилл v0.6.0 | Task 1 |
| CLAUDE.md — процесс всегда в контексте | Task 2 |
| Git-теги на каждую версию | Task 3 |
| Просмотр истории по тегам | Task 3 (после выполнения работает `git diff v0.6.0 v0.7.0`) |

Все требования покрыты. Placeholder'ов нет.
