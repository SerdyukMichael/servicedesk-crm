@echo off
setlocal

echo [1/4] Проверка Docker...
docker info >nul 2>&1
if errorlevel 1 (
    echo Docker не запущен. Запускаю Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo Жду запуска Docker (60 сек)...
    timeout /t 10 /nobreak >nul
    :wait_docker
    docker info >nul 2>&1
    if errorlevel 1 (
        timeout /t 5 /nobreak >nul
        goto wait_docker
    )
    echo Docker запущен.
) else (
    echo Docker уже запущен.
)

echo.
echo [2/4] Поднимаю контейнеры...
cd /d "%~dp0.."
docker compose up -d --build
if errorlevel 1 (
    echo ОШИБКА: не удалось поднять контейнеры.
    pause
    exit /b 1
)

echo.
echo [3/4] Запускаю frontend (если не стартовал автоматически)...
docker start servicedesk_web >nul 2>&1

echo.
echo [4/4] Применяю миграции БД...
docker compose exec backend alembic upgrade head
if errorlevel 1 (
    echo ПРЕДУПРЕЖДЕНИЕ: миграции завершились с ошибкой. Проверьте вручную.
)

echo.
echo ============================================================
echo  Стенд поднят!
echo  Frontend:   http://localhost/
echo  Backend:    http://localhost:8000/docs
echo  MySQL:      localhost:3306
echo  Redis:      localhost:6379
echo ============================================================
echo.
pause
