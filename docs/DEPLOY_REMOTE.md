# План переноса ServiceDesk CRM на удалённый сервер

> Версия: 2.0 (после аудита сервера 188.120.243.122)
> Дата: 2026-04-04

---

## Результаты аудита сервера

| Параметр | Значение | Статус |
|----------|----------|--------|
| ОС | Ubuntu 24.04.4 LTS | ✅ |
| Ядро | 6.8.0-106-generic | ✅ |
| RAM | 1.8 GB (969 MB свободно) | ✅ |
| Диск | 40 GB (34 GB свободно) | ✅ |
| UFW | **ОТКЛЮЧЁН** | ❌ КРИТИЧНО |
| Docker | **Не установлен** | ⚠️ |
| Fail2ban | Установлен | ✅ |
| SSH password auth | Явно не отключён (дефолт = YES) | ❌ |
| ISPmanager | Установлена панель управления | ⚠️ |
| Nginx | Занимает порт 80 (ISPmanager) | ⚠️ КОНФЛИКТ |
| FTP (proftpd) | Открыт на порту 21 | ❌ |
| DNS (named) | Слушает публичный IP:53 | ❌ риск |
| Почта (exim4+dovecot) | 25/143/465/587/993/995 | ⚠️ |

### Открытые порты на публичном IP (до наших действий)

| Порт | Сервис | Решение |
|------|--------|---------|
| 21 | FTP (proftpd) | **Закрыть / отключить** — небезопасно |
| 22 | SSH | Оставить, усилить |
| 25 | SMTP (exim4) | Закрыть если почта не нужна |
| 80 | nginx (ISPmanager) | Переиспользовать как reverse proxy |
| 110 | POP3 (dovecot) | Закрыть |
| 143 | IMAP (dovecot) | Закрыть |
| 443 | — | Свободен → занять для HTTPS |
| 465 | SMTPS (exim4) | Закрыть |
| 587 | SMTP submission | Закрыть |
| 993 | IMAPS (dovecot) | Закрыть |
| 995 | POP3S (dovecot) | Закрыть |
| 1500 | ISPmanager (ihttpd) | Закрыть снаружи или оставить |
| 1501 | ISPmanager nginx | Закрыть снаружи или оставить |
| 3306 | MySQL (localhost only) | ✅ не торчит |
| 8080 | Apache2 (localhost only) | ✅ не торчит |

---

## Архитектура деплоя (с учётом ISPmanager)

На сервере уже есть ISPmanager с nginx на порту 80. Чтобы не сломать панель и не конфликтовать — **используем ISPmanager nginx как reverse proxy** для нашего приложения.

```
Интернет
   │
   ▼
[UFW: 80, 443, 22]
   │
   ▼
ISPmanager nginx (порт 80/443)
   │  /api/*  →  localhost:8000
   │  /*       →  статика React (или Docker nginx на 127.0.0.1:8090)
   ▼
Docker network (внутренняя сеть):
  ├── backend:8000   (НЕ торчит наружу)
  ├── mysql:3306     (НЕ торчит наружу)
  ├── redis:6379     (НЕ торчит наружу)
  ├── celery_worker
  └── celery_beat
```

**Docker-compose для прода**: frontend-контейнер не публикует 80/443 — только внутренний порт для backend. Вместо этого ISPmanager nginx обслуживает фронтенд.

Вариант реализации: backend-контейнер слушает на `127.0.0.1:8000`, ISPmanager nginx проксирует к нему.

---

## Фаза 0 — Безопасность сервера (ПЕРВЫМ ДЕЛОМ)

### 0.1 Закрыть ненужные сервисы

FTP — небезопасен, закрыть:
```bash
systemctl stop proftpd
systemctl disable proftpd
```

Почтовые сервисы (если почта не нужна):
```bash
systemctl stop exim4 dovecot
systemctl disable exim4 dovecot
```

DNS amplification — ограничить named (если DNS не нужен публично):
```bash
# Запретить рекурсию снаружи — в /etc/bind/named.conf.options:
# recursion no;
# allow-query { localhost; };
systemctl restart named
```

### 0.2 Включить UFW

```bash
# Сначала разрешить SSH — иначе отрежем себя!
ufw allow 22/tcp

# Потом включить с запретом всего входящего
ufw default deny incoming
ufw default allow outgoing

# Разрешить нужные порты
ufw allow 80/tcp      # HTTP
ufw allow 443/tcp     # HTTPS

# ISPmanager (оставить если нужен доступ к панели)
# ufw allow 1500/tcp
# ufw allow 1501/tcp

# Включить
ufw enable
ufw status verbose
```

### 0.3 Hardening SSH

```bash
nano /etc/ssh/sshd_config
```

Добавить/изменить:
```
PasswordAuthentication no
PermitRootLogin no
PubkeyAuthentication yes
X11Forwarding no
```

> **ВАЖНО**: Сначала скопировать публичный ключ на сервер, ПОТОМ отключать пароль!

```bash
# С локальной машины
ssh-copy-id deploy@188.120.243.122

# Проверить вход по ключу в новой вкладке
# Только после успешной проверки — перезапустить sshd
systemctl restart sshd
```

### 0.4 Создать deploy-пользователя

```bash
adduser deploy
usermod -aG sudo,docker deploy
mkdir -p /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/  # если есть ключи
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
```

### 0.5 Fail2ban — проверить конфиг

Fail2ban уже установлен (ISPmanager). Убедиться что SSH-защита активна:
```bash
fail2ban-client status
fail2ban-client status sshd
```

Если нет jail для sshd — добавить в `/etc/fail2ban/jail.local`:
```ini
[sshd]
enabled = true
port = 22
maxretry = 5
bantime = 3600
findtime = 600
```
```bash
systemctl restart fail2ban
```

---

## Фаза 1 — Установка Docker

> На сервере Docker **не установлен** — устанавливаем сейчас.

```bash
apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh
usermod -aG docker deploy

# Docker Compose (плагин)
apt install docker-compose-plugin -y

# Проверка
docker --version
docker compose version
```

---

## Фаза 2 — Клонирование кода

```bash
su - deploy
cd /opt
sudo mkdir servicedesk-crm
sudo chown deploy:deploy servicedesk-crm
git clone https://github.com/<ORG>/servicedesk-crm.git
cd servicedesk-crm
```

---

## Фаза 3 — Конфигурация .env файлов

> **Секреты НИКОГДА не в git.** Создаём вручную на сервере.

### /opt/servicedesk-crm/.env

```bash
nano /opt/servicedesk-crm/.env
```

```env
MYSQL_ROOT_PASSWORD=<сложный пароль ≥20 символов, уникальный>
MYSQL_DATABASE=servicedesk
MYSQL_USER=servicedesk_user
MYSQL_PASSWORD=<сложный пароль ≥20 символов, уникальный>
REDIS_PASSWORD=<сложный пароль ≥20 символов, уникальный>
```

### /opt/servicedesk-crm/backend/.env

```bash
nano /opt/servicedesk-crm/backend/.env
```

```env
DATABASE_URL=mysql+pymysql://servicedesk_user:<DB_PASSWORD>@mysql:3306/servicedesk
SECRET_KEY=<python3 -c "import secrets; print(secrets.token_hex(32))">
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG=False
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
```

### Права

```bash
chmod 600 /opt/servicedesk-crm/.env
chmod 600 /opt/servicedesk-crm/backend/.env
```

---

## Фаза 4 — Адаптация docker-compose.yml для продакшена

На сервере nginx уже занят ISPmanager, поэтому **frontend-контейнер не должен занимать порты 80/443**.

Создать `/opt/servicedesk-crm/docker-compose.prod.yml` — override для прода:

```yaml
services:
  frontend:
    ports: []     # убрать публичные порты — ISPmanager nginx проксирует
    ports:
      - "127.0.0.1:8090:80"   # только localhost, ISPmanager проксирует сюда

  backend:
    ports: []     # backend не торчит наружу
```

Запуск с override:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Или проще — изменить порты прямо в docker-compose.yml для прода.

### CORS — убрать wildcard

В `backend/app/main.py` изменить до запуска:
```python
# Было:
allow_origins=["*"]
# Стало:
allow_origins=["https://ваш-домен.ru"]
```

---

## Фаза 5 — SSL и настройка ISPmanager nginx

ISPmanager уже имеет встроенную интеграцию с Let's Encrypt.

### Вариант А — через ISPmanager UI (рекомендуется)

1. Зайти в ISPmanager: `https://188.120.243.122:1500`
2. Создать сайт для вашего домена
3. Включить SSL через Let's Encrypt (кнопка в интерфейсе)
4. Добавить кастомный nginx конфиг для reverse proxy

### Вариант Б — вручную через конфиг nginx

Найти конфиги ISPmanager nginx:
```bash
find /etc/nginx /usr/local/mgr5 -name "*.conf" | head -20
```

Добавить конфиг сайта (`/etc/nginx/conf.d/servicedesk.conf` или через ISPmanager):

```nginx
server {
    listen 80;
    server_name ваш-домен.ru www.ваш-домен.ru;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name ваш-домен.ru www.ваш-домен.ru;

    ssl_certificate     /etc/letsencrypt/live/ваш-домен.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ваш-домен.ru/privkey.pem;

    # Фронтенд (React SPA)
    location / {
        proxy_pass http://127.0.0.1:8090;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
nginx -t && systemctl reload nginx
```

---

## Фаза 6 — Перенос базы данных

### 6.1 Дамп на локальной машине (Windows)

```bash
docker compose exec mysql mysqldump \
  -u root -p${MYSQL_ROOT_PASSWORD} \
  --single-transaction \
  --routines \
  --triggers \
  servicedesk > servicedesk_dump.sql

gzip servicedesk_dump.sql
```

### 6.2 Нарезка на тома по 360 KB (лимит сервера)

```bash
# В Git Bash / WSL
split -b 360k servicedesk_dump.sql.gz dump_part_
ls -lh dump_part_*
```

### 6.3 Проверка целостности

```bash
# Локально — запомнить MD5
md5sum servicedesk_dump.sql.gz
```

### 6.4 Передача на сервер по SCP

```bash
for part in dump_part_*; do
  scp $part deploy@188.120.243.122:/tmp/
done
```

### 6.5 Сборка и распаковка на сервере

```bash
ssh deploy@188.120.243.122
cd /tmp
cat dump_part_* > servicedesk_dump.sql.gz
md5sum servicedesk_dump.sql.gz   # сравнить с локальным
gunzip servicedesk_dump.sql.gz
```

---

## Фаза 7 — Запуск контейнеров

```bash
cd /opt/servicedesk-crm

# Сначала только инфраструктура — дать стартовать
docker compose up -d mysql redis
sleep 30
docker compose ps

# Затем весь стек (сборка бэка: ~5–10 мин, RAM хватает)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## Фаза 8 — Восстановление базы данных

```bash
# Восстановить дамп
docker compose exec -T mysql mysql \
  -u root -p${MYSQL_ROOT_PASSWORD} \
  servicedesk < /tmp/servicedesk_dump.sql

# Применить миграции (на случай если код новее дампа)
docker compose exec backend alembic upgrade head
```

---

## Фаза 9 — Верификация

```bash
# Контейнеры
docker compose ps

# Логи
docker compose logs backend --tail=50

# Health check
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8090/

# Через домен
curl https://ваш-домен.ru/health
curl -X POST https://ваш-домен.ru/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"..."}'

# Firewall
ufw status numbered

# Открытые порты после всего
ss -tlnp | grep -v 127.0.0.1
```

---

## Чек-лист безопасности

### Критично (до go-live)
- [ ] UFW включён: открыты только 22, 80, 443
- [ ] SSH: вход только по ключу, root-логин запрещён
- [ ] FTP (proftpd) остановлен и отключён
- [ ] .env файлы: chmod 600, не в git
- [ ] Все пароли уникальные (≥ 20 символов), сгенерированы для прода
- [ ] SECRET_KEY сгенерирован заново
- [ ] DEBUG=False
- [ ] CORS: конкретный домен, не `*`

### Важно
- [ ] DNS (named) не отвечает на рекурсивные запросы снаружи
- [ ] Почтовые сервисы: отключены или ограничены UFW если не нужны
- [ ] MySQL: порт 3306 не торчит наружу (Docker-сеть, уже так)
- [ ] Redis: порт 6379 не торчит наружу (Docker-сеть)
- [ ] Backend 8000: только 127.0.0.1, не внешний
- [ ] SSL/HTTPS работает (certbot или ISPmanager)
- [ ] Fail2ban активен для SSH
- [ ] Автообновление сертификата настроено

### После запуска
- [ ] Сменить пароль ISPmanager если он дефолтный
- [ ] Проверить логи приложения через 24ч
- [ ] Убедиться что данные мигрировали корректно

---

## Матрица угроз

| Угроза | Статус до | Защита |
|--------|-----------|--------|
| Брутфорс SSH | ❌ пароль открыт | SSH-ключ + fail2ban + PermitRootLogin no |
| Открытый FTP | ❌ порт 21 открыт | Остановить proftpd |
| DNS amplification | ❌ named на публичном IP | Запретить рекурсию снаружи |
| Нет firewall | ❌ UFW inactive | Включить UFW |
| Прямой доступ к MySQL | ✅ только localhost | Не менять |
| Перехват трафика | ⚠️ нет 443 | Let's Encrypt через ISPmanager |
| Утечка секретов | нет .env | .env не в git, chmod 600 |
| Конфликт портов | ⚠️ nginx на 80 | Docker frontend → 127.0.0.1:8090 |
| Исчерпание RAM при сборке | ✅ 2GB должно хватить | Поэтапный старт |
| Повреждение дампа | — | MD5-проверка |
| Компрометация root | ❌ root login открыт | PermitRootLogin no после настройки deploy |
