# Аудит безопасности — ServiceDesk CRM

**Дата:** 2026-04-03  
**Версия системы:** 0.5.0  
**Охват:** backend (FastAPI), frontend (React/Nginx), инфраструктура (Docker Compose)  
**Метод:** ручной статический анализ исходного кода  
**Угрозы вне охвата:** DDoS-атаки

---

## Сводная таблица

| # | Уровень | Категория | Краткое описание |
|---|---------|-----------|-----------------|
| S-01 | КРИТИЧЕСКИЙ | Сеть | Нет HTTPS — передача данных открытым текстом |
| S-02 | КРИТИЧЕСКИЙ | CORS | `allow_origins=["*"]` — любой сайт может делать API-запросы |
| S-03 | КРИТИЧЕСКИЙ | Инфраструктура | MySQL 3306 и Redis 6379 доступны напрямую из интернета |
| S-04 | ВЫСОКИЙ | IDOR / RBAC | Анонимный endpoint скачивания файлов |
| S-05 | ВЫСОКИЙ | RBAC | `client_user` может редактировать заявки чужой организации (PUT/PATCH) |
| S-06 | ВЫСОКИЙ | RBAC | `client_user` видит контакты и оборудование любого клиента через sub-resource |
| S-07 | ВЫСОКИЙ | Инфраструктура | Backend порт 8000 открыт напрямую, минуя Nginx |
| S-08 | ВЫСОКИЙ | Аутентификация | Нет защиты от brute-force на `/auth/login` |
| S-09 | ВЫСОКИЙ | Инфраструктура | Исходный код монтируется в контейнер — записываемый том в продакшене |
| S-10 | СРЕДНИЙ | Аутентификация | JWT хранится в `localStorage` — уязвим к XSS |
| S-11 | СРЕДНИЙ | Авторизация | `change_ticket_status` доступен любому авторизованному пользователю |
| S-12 | СРЕДНИЙ | Сеть | Swagger UI (`/docs`, `/redoc`) открыт в продакшене |
| S-13 | СРЕДНИЙ | Инфраструктура | Дефолтные пароли к БД в `docker-compose.yml` |
| S-14 | СРЕДНИЙ | Заголовки HTTP | Отсутствуют security headers в Nginx |
| S-15 | СРЕДНИЙ | Загрузка файлов | Тип файла не проверяется по содержимому (magic bytes) |
| S-16 | НИЗКИЙ | Утечка информации | Временный пароль портала передаётся в теле HTTP-ответа |
| S-17 | НИЗКИЙ | Утечка информации | `/health` раскрывает имя приложения и версию |
| S-18 | НИЗКИЙ | Перечисление | Все ID — последовательные целые числа |
| S-19 | НИЗКИЙ | Аудит | Журнал аудита покрывает только контакты клиентов |

---

## Детальное описание уязвимостей

---

### S-01 — КРИТИЧЕСКИЙ: Нет HTTPS

**Файл:** `frontend/nginx.conf`  
**Строка:** 2 (`listen 80`)

Nginx слушает только HTTP. Все данные — токены JWT, пароли, персональные данные клиентов — передаются в открытом виде. Любой наблюдатель на сетевом пути (провайдер, man-in-the-middle) может перехватить сессию.

**Риск:** перехват учётных данных, кража сессии (JWT).

---

### S-02 — КРИТИЧЕСКИЙ: CORS wildcard

**Файл:** `backend/app/main.py`  
**Строка:** 18

```python
allow_origins=["*"],
allow_credentials=True,
```

Комбинация `allow_origins=["*"]` с `allow_credentials=True` нарушает спецификацию CORS и отклоняется браузерами, однако `allow_credentials=True` при wildcard-origins фактически означает, что любой сайт может инициировать cross-origin запросы от лица залогиненного пользователя. Дополнительно: зная URL API, сторонний сайт может взаимодействовать с API без ограничений по Origin.

**Риск:** CSRF-подобные атаки из вредоносного сайта; утечка данных через cross-origin requests.

---

### S-03 — КРИТИЧЕСКИЙ: База данных и Redis доступны из интернета

**Файл:** `docker-compose.yml`  
**Строки:** 20, 35

```yaml
mysql:
  ports:
    - "3306:3306"   # ← видно всему интернету

redis:
  ports:
    - "6379:6379"   # ← без пароля, видно всему интернету
```

Docker пробрасывает порты на `0.0.0.0`, обходя firewall правила ОС (ufw/iptables). Redis в конфигурации по умолчанию работает **без пароля**. MySQL использует слабые пароли из дефолтных значений `.env`.

**Риск:** прямой доступ к БД; чтение/запись всей базы данных без аутентификации через Redis; компрометация всей системы.

---

### S-04 — ВЫСОКИЙ: Анонимный endpoint скачивания файлов

**Файл:** `backend/app/api/endpoints/tickets.py`  
**Строки:** 473–497

```python
@router.get("/{ticket_id}/attachments/{file_id}/download")
def download_attachment_direct(
    ticket_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    # ← нет Depends(get_current_user)
):
    """Download endpoint without JWT auth — accessible via direct browser link."""
```

Endpoint намеренно создан без аутентификации. ID файлов последовательные. Злоумышленник может перебрать все `file_id` и скачать вложения к любой заявке (паспортные данные, акты, финансовые документы).

**Риск:** несанкционированный доступ ко всем вложениям без учётной записи.

---

### S-05 — ВЫСОКИЙ: `client_user` может изменить заявку чужой организации

**Файл:** `backend/app/api/endpoints/tickets.py`  
**Строки:** 173–190, 209–240

```python
_MANAGE_ROLES = ("admin", "svc_mgr", "client_user")

@router.put("/{ticket_id}", ...)
def update_ticket(
    ...,
    _: User = Depends(require_roles(*_MANAGE_ROLES)),  # ← client_user разрешён
    # нет client_scope
):

@router.patch("/{ticket_id}/assign", ...)
def assign_ticket(
    ...,
    _: User = Depends(require_roles(*_MANAGE_ROLES)),  # ← client_user разрешён
    # нет client_scope
):
```

`client_user` входит в `_MANAGE_ROLES`, но на этих endpoints нет фильтрации по `client_scope`. Пользователь портала может изменить заголовок, описание, приоритет любой заявки или назначить инженера на заявку другого банка.

**Риск:** несанкционированная модификация данных чужих организаций.

---

### S-06 — ВЫСОКИЙ: `client_user` видит данные любой организации через sub-resource endpoints

**Файл:** `backend/app/api/endpoints/clients.py`  
**Строки:** 246–258, 501–529

```python
@router.get("/{client_id}/contacts", ...)
def list_contacts(
    client_id: int,
    ...,
    _: User = Depends(get_current_user),  # ← нет client_scope
):

@router.get("/{client_id}/equipment", ...)
def list_client_equipment(
    client_id: int,
    ...,
    _: User = Depends(get_current_user),  # ← нет client_scope
):

@router.get("/{client_id}/tickets", ...)
def list_client_tickets(
    client_id: int,
    ...,
    _: User = Depends(get_current_user),  # ← нет client_scope
):
```

`client_user`, зная `client_id` любой организации, может получить полный список её контактов (с email, телефонами), оборудования и заявок через прямой URL. Защита на `GET /clients/{id}` (404 на чужой org) здесь не помогает — sub-resource доступны напрямую.

**Риск:** утечка персональных данных (контакты), бизнес-данных (оборудование, история заявок).

---

### S-07 — ВЫСОКИЙ: Backend API доступен напрямую на порту 8000

**Файл:** `docker-compose.yml`  
**Строка:** 48

```yaml
backend:
  ports:
    - "8000:8000"
```

FastAPI слушает на `0.0.0.0:8000`. Любой запрос с внешнего IP к порту 8000 попадает прямо в backend, минуя Nginx (security headers, rate limiting, access log). Также доступны `/docs` и `/redoc`.

**Риск:** обход nginx-уровня защиты; прямой доступ к Swagger; утечка внутренней маршрутизации.

---

### S-08 — ВЫСОКИЙ: Нет защиты от brute-force на `/auth/login`

**Файл:** `backend/app/api/endpoints/auth.py`  
**Строки:** 40–72

Endpoint не ограничивает количество попыток входа. Нет:
- account lockout после N неудачных попыток
- rate limiting (slowloris, IP-based throttling)
- CAPTCHA или задержки ответа

Временной атакой можно перебрать пароли пользователей.

**Риск:** компрометация учётных записей через перебор паролей.

---

### S-09 — ВЫСОКИЙ: Исходный код монтируется записываемым томом в production

**Файл:** `docker-compose.yml`  
**Строки:** 55–56, 67–69

```yaml
backend:
  volumes:
    - ./backend:/app  # ← полный исходный код, записываемый

celery_worker:
  volumes:
    - ./backend:/app  # ← аналогично
```

Том монтируется read-write. Если злоумышленник получит RCE или доступ к файловой системе хоста, он сможет модифицировать `deps.py`, `security.py` или любой другой файл — и Python выполнит изменённый код без перезапуска контейнера (uvicorn с `--reload`).

**Риск:** постоянный бэкдор, полная компрометация системы.

---

### S-10 — СРЕДНИЙ: JWT токен хранится в `localStorage`

**Файл:** `frontend/src/api/axios.ts`  
**Строка:** 6

```typescript
const token = localStorage.getItem('token')
```

`localStorage` доступен из любого JavaScript на странице. При наличии XSS-уязвимости в любой зависимости или будущем коде — токен можно украсть и использовать с любого устройства до истечения 8 часов (текущий TTL).

**Риск:** кража сессии при XSS-атаке.

---

### S-11 — СРЕДНИЙ: Смена статуса заявки доступна любому авторизованному пользователю

**Файл:** `backend/app/api/endpoints/tickets.py`  
**Строки:** 243–308

```python
@router.patch("/{ticket_id}/status", ...)
def change_ticket_status(
    ...,
    current_user: User = Depends(get_current_user),  # ← любой авторизованный
    # нет require_roles, нет client_scope
):
```

Нет ни проверки роли, ни проверки `client_scope`. Любой авторизованный пользователь, включая `client_user`, может перевести заявку в любой допустимый по FSM статус (например, `cancelled`), в том числе заявки чужой организации.

**Риск:** несанкционированная манипуляция статусами заявок, отмена чужих заявок.

---

### S-12 — СРЕДНИЙ: Swagger UI открыт в production

**Файл:** `backend/app/main.py`  
**Строки:** 8–13

```python
app = FastAPI(
    docs_url="/docs",    # ← доступен публично
    redoc_url="/redoc",  # ← доступен публично
    ...
)
```

Swagger UI на `http://<server>:8000/docs` раскрывает полную схему API (все эндпоинты, параметры, схемы данных), что существенно облегчает разведку для атакующего.

**Риск:** информационная разведка; упрощение эксплойта других уязвимостей.

---

### S-13 — СРЕДНИЙ: Дефолтные пароли к БД в `docker-compose.yml`

**Файл:** `docker-compose.yml`  
**Строки:** 10–13

```yaml
MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-rootpass}
MYSQL_PASSWORD: ${MYSQL_PASSWORD:-sdpass}
```

Если `.env` не создан или переменные не заданы, система стартует с паролями `rootpass` / `sdpass`. Это типичные пароли в словарях брутфорса.

**Риск:** компрометация БД при отсутствии или неполном `.env`.

---

### S-14 — СРЕДНИЙ: Отсутствуют HTTP security headers

**Файл:** `frontend/nginx.conf`

Не заданы следующие заголовки:

| Заголовок | Защита от |
|-----------|-----------|
| `Strict-Transport-Security` | Downgrade-атаки, принудительный HTTPS |
| `X-Frame-Options: DENY` | Clickjacking |
| `X-Content-Type-Options: nosniff` | MIME-sniffing атаки |
| `Content-Security-Policy` | XSS, инъекция внешних скриптов |
| `Referrer-Policy` | Утечка URL в заголовке Referer |
| `Permissions-Policy` | Несанкционированный доступ к камере/микрофону/геолокации |

**Риск:** clickjacking, MIME-sniffing, XSS через внешние ресурсы.

---

### S-15 — СРЕДНИЙ: Загруженные файлы не проверяются по содержимому

**Файл:** `backend/app/api/endpoints/tickets.py`  
**Строки:** 376–415

```python
attachment = TicketFile(
    ...
    file_type=file.content_type,  # ← берётся из запроса, не из содержимого файла
    file_data=data,
)
```

Проверяется только размер файла (20 MB). MIME-тип берётся из `Content-Type` запроса, который полностью контролирует клиент. При возврате файла:

```python
inline_types = ("image/", "text/")
disposition = "inline" if any(mime.startswith(t) for t in inline_types) else "attachment"
```

Злоумышленник загружает SVG с XSS-пейлоадом, указав `Content-Type: image/svg+xml` — файл откроется в браузере inline и выполнит скрипт.

**Риск:** stored XSS через вредоносные SVG-файлы.

---

### S-16 — НИЗКИЙ: Временный пароль передаётся в теле HTTP-ответа

**Файл:** `backend/app/api/endpoints/clients.py`  
**Строки:** 458–461

```python
result.temporary_password = temp_password
return result
```

Временный пароль нового портального пользователя возвращается в JSON-ответе. При отсутствии HTTPS (S-01) пароль перехватывается в открытом виде. Даже при HTTPS — он попадает в логи proxy-серверов, в network tab разработчика, в логи nginx.

**Риск:** компрометация временного пароля; по-умолчанию пользователи его не меняют.

---

### S-17 — НИЗКИЙ: `/health` раскрывает версию приложения

**Файл:** `backend/app/main.py`  
**Строка:** 38

```python
return {"status": "ok", "app": settings.app_name, "version": "2.0.0"}
```

Endpoint доступен без аутентификации. Раскрывает имя системы и точную версию, что упрощает поиск CVE для конкретной версии компонента.

**Риск:** информационная разведка (незначительный).

---

### S-18 — НИЗКИЙ: Последовательные целочисленные ID во всех сущностях

**Все модели:** `backend/app/models/__init__.py`

Все первичные ключи — автоинкрементные `Integer`. Зная один `ticket_id` или `file_id`, атакующий легко перечисляет все записи последовательным перебором. В сочетании с S-04 (анонимный download) это даёт полный доступ ко всем файлам.

**Риск:** энумерация данных при наличии других уязвимостей; IDOR.

---

### S-19 — НИЗКИЙ: Журнал аудита охватывает только контакты клиентов

**Файл:** `backend/app/api/endpoints/clients.py`

`AuditLog` записи создаются только для операций с `ClientContact`. Изменения заявок, оборудования, пользователей, настроек ролей — не логируются. При инциденте будет невозможно восстановить картину действий злоумышленника.

**Риск:** затруднённое расследование инцидентов (forensics).

---

## Приоритеты устранения

### Блокеры перед выкладкой в продакшен (КРИТИЧЕСКИЕ + ВЫСОКИЕ)

1. **S-01** — настроить TLS (Let's Encrypt + certbot или reverse proxy с SSL)
2. **S-03** — убрать `ports` у `mysql` и `redis` из `docker-compose.yml`; Redis защитить паролем через `requirepass`
3. **S-07** — убрать `ports: - "8000:8000"` у backend (backend доступен только внутри Docker сети)
4. **S-02** — заменить `allow_origins=["*"]` на конкретный домен фронтенда
5. **S-04** — добавить `Depends(get_current_user)` на `/download` endpoint
6. **S-05** — добавить `client_scope` в `update_ticket` и `assign_ticket`
7. **S-06** — добавить `client_scope` в `list_contacts`, `list_client_equipment`, `list_client_tickets`
8. **S-08** — добавить rate limiting (slowapi или nginx `limit_req`)
9. **S-09** — убрать volume-mount в production; собирать образ с кодом внутри
10. **S-11** — добавить `require_roles` и `client_scope` в `change_ticket_status`

### Рекомендуется устранить до первых реальных клиентов (СРЕДНИЕ)

11. **S-12** — отключить `/docs` и `/redoc` в production (`docs_url=None, redoc_url=None`)
12. **S-13** — убедиться, что `.env` задан с сильными паролями; убрать дефолтные значения из `docker-compose.yml`
13. **S-14** — добавить security headers в `nginx.conf`
14. **S-15** — проверять MIME тип по magic bytes (библиотека `python-magic`), запретить SVG/HTML/JS

### Технический долг (НИЗКИЕ)

15. **S-10** — рассмотреть переход на httpOnly cookies для хранения JWT
16. **S-16** — не включать временный пароль в тело ответа; отправлять по email или показывать только один раз через отдельный безопасный канал
17. **S-17** — убрать версию из `/health` или закрыть endpoint аутентификацией
18. **S-18** — рассмотреть UUID или ULID для публичных ID (особенно для файлов)
19. **S-19** — расширить `AuditLog` на все write-операции

---

*Аудит проведён по исходному коду. Динамическое тестирование (пентест) не выполнялось.*
