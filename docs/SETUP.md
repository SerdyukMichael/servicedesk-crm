# Инструкция по первичной настройке

## Шаг 1 — Установи программы на Windows

| Программа | Ссылка |
|-----------|--------|
| Git | https://git-scm.com/download/win |
| Python 3.11 | https://www.python.org/downloads/ — включи "Add to PATH" |
| Node.js 20 LTS | https://nodejs.org/en/download |
| VS Code | https://code.visualstudio.com/ |
| Docker Desktop | https://www.docker.com/products/docker-desktop/ |

## Шаг 2 — Настрой Git (один раз)

```powershell
git config --global user.name "SerdyukMichael"
git config --global user.email "твой@email.com"
```

## Шаг 3 — Клонируй репозиторий

```powershell
mkdir C:\Projects
cd C:\Projects
git clone https://github.com/SerdyukMichael/servicedesk-crm.git
cd servicedesk-crm
```

## Шаг 4 — Скопируй файлы проекта

Скопируй все файлы из архива в папку C:\Projects\servicedesk-crm\

## Шаг 5 — Первый push на GitHub

```powershell
git add .
git commit -m "Initial project structure — Phase 1"
git push origin main
```

## Шаг 6 — Запусти локальную БД

```powershell
docker-compose up -d mysql
docker ps
```

## Шаг 7 — Настрой и запусти Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Открой .env и замени SECRET_KEY на любые 32 символа
alembic upgrade head
uvicorn app.main:app --reload
```

Документация API: http://localhost:8000/docs

## Шаг 8 — Секреты для автодеплоя

GitHub: Settings → Secrets → New repository secret

| Ключ | Значение |
|------|----------|
| SERVER_HOST | IP сервера |
| SERVER_USER | ubuntu или root |
| SERVER_SSH_KEY | приватный SSH ключ |
