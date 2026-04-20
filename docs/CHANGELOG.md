# CHANGELOG

## [Unreleased] — 2026-04-16

**Блокировка редактирования акта при существующем/оплаченном счёте** (BR-F-126, BR-F-127)

### Backend
- `PATCH /api/v1/tickets/{id}/work-act`:
  - Guard: если по заявке создан счёт (статус ≠ `cancelled`) → только `admin` может редактировать акт; остальные роли получают 403 `ACT_LOCKED_INVOICE_EXISTS` (BR-F-126)
  - При изменении позиций и существующем **неоплаченном** счёте: автоматически заменяются позиции счёта и пересчитываются `subtotal`, `vat_amount`, `total_amount` (BR-F-127)
  - При изменении позиций и существующем **оплаченном** счёте и расхождении суммы: возвращает 409 `INVOICE_PAID_MISMATCH` с полями `act_total`, `invoice_total`
  - Новый флаг `force_save: bool` в `WorkActUpdate`: при `true` сохраняет акт, счёт не изменяется (BR-F-127)
- Новые хелперы: `_calc_act_total(items)`, `_sync_invoice_from_act(invoice, act_items, db)`
- 8 новых тестов в `tests/test_work_act_invoice_lock.py` (все зелёные; полный сьют: 396/396)

### Frontend
- `TicketDetailPage`: кнопка «Редактировать акт» скрыта для не-admin если счёт существует (BR-F-126)
- `TicketDetailPage`: диалог подтверждения при 409 `INVOICE_PAID_MISMATCH` с кнопкой «Сохранить принудительно» (повтор с `force_save=true`)
- `endpoints.ts`: добавлен параметр `force_save?: boolean` в `updateWorkAct`

### RBAC
- `engineer` добавлен в `_READ_ROLES` для `/api/v1/invoices` (BR-F-119, BR-F-120: инженер должен видеть связанный счёт и статус оплаты)
- Обновлена `RBAC_Matrix.md`: engineer имеет `📖⁷` на просмотр счетов

### Документация
- `DocSpec_WorkAct.md` v1.1: добавлены BR-F-126, BR-F-127 в раздел проверок и таблицу ролей
- `RBAC_Matrix.md`: обновлена таблица акта — разделены строки редактирования с/без счёта
- `RTM.md`: добавлены R1-10 (BR-F-126) и R1-11 (BR-F-127), статус ✅

---

## [1.0.0] — 2026-04-15

**Единый каталог материальных ценностей + история цен** (BR-F-122, BR-P-006)

### Архитектурное решение
Отдельная сущность `product_catalog` (добавленная в 0.9.1) упразднена. `SparePart` — единый каталог материальных ценностей: для части позиций ведётся прайс с историей изменений. `price_history` покрывает оба справочника: услуги (`entity_type='service'`) и запчасти (`entity_type='spare_part'`).

### Backend
- Удалены: таблица `product_catalog`, эндпоинт `/api/v1/product-catalog`, модель, схемы
- `SparePart`: добавлены поля `unit_price`, `currency`, `created_by`, `created_at`, `updated_at`
- `PATCH /api/v1/parts/{id}/price` — установка/изменение цены (роли: admin, svc_mgr); автоматически пишет запись в `price_history`
- `GET /api/v1/parts/{id}/price-history` — история изменений цены; недоступен `client_user`
- `GET /api/v1/parts?has_price=true` — фильтр: только позиции с ценой > 0
- Новая таблица `price_history`: полиморфная ссылка `(entity_type, entity_id)`, хранит старую/новую цену, валюту, причину, автора, дату
- Миграция `011_remove_product_catalog`

### Frontend
- `PartsPage` полностью переработана:
  - Колонка «Цена» с валютой и ссылкой «история»
  - Кнопка «Уст. цену» / «Цена» — только для admin, svc_mgr
  - Модальное окно установки/изменения цены (причина обязательна, ≥ 5 символов)
  - Модальное окно «История цен» с таблицей изменений
- `TicketDetailPage`: выпадающий список запчастей при создании акта фильтруется по `has_price=true` (BR-F-122)
- Удалены: `ProductCatalogPage.tsx`, `useProductCatalog.ts`, маршрут `/product-catalog`, пункт меню «Товары»
- `SparePart` в `types.ts`: поле `price` заменено на `unit_price: string` + `currency: string`

### База данных
- Миграция `011`: удалена `product_catalog`; откат enum `work_act_item_type` → `service|part`; откат `invoice_item_type` → `service|part|manual`; создана `price_history`

### Тесты
- Удалены: `test_product_catalog.py`
- Добавлены: `test_parts_price.py` — 14 тестов (установка цены, права, история, сортировка)
- Итого: **378 тестов, все зелёные**

### Документы
- `ER_DataModel.md`, `RBAC_Matrix.md`, `RTM.md`, `BRD`, `UC-101.md` — обновлены
- `docs/sa/API_Specification.yaml`, `Backend_Architecture.md`, `Frontend_Architecture.md` — обновлены
- `releases/v1.0.0/CHANGES.md`, `releases/v1.0.0/db_migrations.sql` — сформированы

### Инфраструктура
- CI/CD (`deploy.yml`): добавлен шаг `docker cp dist → nginx-контейнер` для обновления фронтенда без пересборки образа на сервере
- CI/CD: добавлен `docker compose build backend` перед `up` — теперь новый Python-код гарантированно попадает в контейнер

---

## [0.9.1] — 2026-04-12

**Product Catalog MVP** (UC-102) — *впоследствии заменён архитектурным решением v1.0.0*

- Таблица `product_catalog`, эндпоинт `/api/v1/product-catalog` (CRUD)
- Страница «Прайс-лист товаров» в интерфейсе
- Миграция `010_product_catalog`
- Фикс `docker-compose.yml`: `nginx.conf` по умолчанию для локального стенда

---

## [0.9.0] — 2026-04-09

**Подписание акта, статус оплаты, защита редактирования** (BR-F-115 – BR-F-120)

### Backend
- `POST /tickets/{id}/work-act/sign` — подписание акта без act_id; только `client_user`
- Ограничение `POST /work-act/{act_id}/sign` до роли `client_user` (ранее admin/svc_mgr тоже могли)
- `GET /invoices?ticket_id=X` — новый фильтр для выборки счёта по заявке
- `InvoiceResponse.is_paid: bool` — вычисляемое поле (`status == "paid"`)

### Frontend
- Кнопка «Редактировать акт» скрыта если акт подписан (BR-F-115)
- «Подписать акт» — только для `client_user`; статус «✓ Подписан [дата]» (BR-F-116, BR-F-117)
- Кнопка «Создать счёт» disabled без позиций; скрыта если счёт уже существует (BR-F-118)
- Строка «Счёт» рядом с актом: ссылка + badge оплаты (BR-F-119, BR-F-120)
- InvoicesPage: исправлен баг с именем клиента; добавлена колонка «Оплачен»

### Тесты
- Обновлён тест подписания: svc_mgr получает 403 (согласно BR-F-116)
- Итого: **364 теста, все зелёные**

### Документы
- BRD: BR-F-115 дополнен UI-правилом скрытия кнопки
- UC-904 v1.3: новый AC-сценарий «Кнопка «Редактировать акт» скрыта после подписания»

---

## [0.8.0] — 2026-04-08

**Редактирование акта выполненных работ** (BR-F-114, BR-F-115)

### Backend
- `PATCH /api/v1/tickets/{ticket_id}/work-act` — обновление описания, времени и позиций акта; позиции заменяются целиком
- Возвращает 403 если акт подписан (`signed_by IS NOT NULL`)
- Доступен ролям: `engineer`, `svc_mgr`, `admin`
- Новая схема `WorkActUpdate`

### Frontend
- Кнопка «Редактировать акт» в карточке заявки (скрыта после подписания)
- Форма предзаполняется данными существующего акта
- Хук `useUpdateWorkAct`
- Исправлен тип `WorkAct`: `signed_by: number | null` вместо `signed_by_engineer`/`signed_by_client`

### Тесты
- 8 новых TDD-тестов (`test_work_act_edit.py`), итого **364 теста**

### Документы
- BRD: добавлены BR-F-114, BR-F-115
- UC-904: АП-0 (редактирование), ИП-6 (блокировка подписанного)
- RBAC Matrix v2.3: строка «Редактировать акт (до подписания)»

---

## [0.7.0] — 2026-04-07

**Прайс-листы услуг и позиции акта** (BR-F-110 – BR-F-113, BR-P-001 – BR-P-004)

### Backend
- `ServiceCatalog` — справочник услуг (CRUD, категории, прайс)
- `WorkActItem` — структурированные позиции акта (тип, ссылка, цена на момент сохранения)
- `POST /invoices/from-act/{ticket_id}` — счёт из акта (BR-P-003)
- Миграция 010: `service_catalog`, `work_act_items`, расширен `invoice_items`
- 355 тестов (все зелёные)

### Frontend
- `/service-catalog` — страница прайс-листа (таблица, CRUD, фильтр по категории)
- Форма акта — секция позиций (услуга/запчасть, автоподстановка цены, итог)
- Кнопка «Создать счёт из акта» на странице заявки

---

## [0.6.0] — 2026-04-03

**Security hardening** — закрыты критические и высокие уязвимости перед выкладкой на внешний сервер.

**Ключевые изменения:**

- Инфраструктура: порты MySQL, Redis и backend-API закрыты от внешнего доступа; исходный код больше не монтируется в production-контейнер
- CORS: `allow_origins=["*"]` заменён на список разрешённых доменов через переменную окружения `ALLOWED_ORIGINS`
- HTTPS: готовый `nginx.prod.conf` с TLS 1.2/1.3, HSTS, OCSP stapling, полным набором security headers и HTTP→HTTPS redirect
- Rate limiting: 5 попыток входа в минуту на `/auth/login` через nginx
- Swagger UI (`/docs`, `/redoc`) отключён в production через флаг `DEBUG`
- Download endpoint файлов вложений защищён JWT-аутентификацией и row-level фильтрацией
- `client_user` не может редактировать заявки чужой организации (S-05)
- `client_user` не может просматривать контакты, оборудование и заявки через `/clients/{id}/contacts|equipment|tickets` чужой организации (S-06)
- `assign_ticket` закрыт для роли `client_user` (только `admin`, `svc_mgr`)
- `change_ticket_status` требует явной роли (`admin`, `svc_mgr`, `engineer`, `client_user`) и соблюдает row-level фильтрацию
- 20 новых тестов безопасности (345 всего)

### Инфраструктура

#### docker-compose.yml

- Порты `3306`, `6379`, `8000` больше не пробрасываются на хост — сервисы доступны только внутри Docker-сети
- Volume-mount исходного кода (`./backend:/app`) убран из production-конфига
- Redis теперь требует пароль (`${REDIS_PASSWORD}`)
- Дефолтные значения паролей убраны из compose-файла

#### docker-compose.override.yml (новый)

- Dev-оверрайд: Docker Compose подхватывает автоматически на localhost
- Возвращает dev-порты, volume-mount'ы и `--reload` только для локальной разработки
- На продакшен-сервере этот файл не должен присутствовать

#### frontend/nginx.conf

- `limit_req_zone` + `limit_req` на `/api/v1/auth/login`: 5 req/min, burst=3
- Security headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`

#### frontend/nginx.prod.conf (новый)

- HTTP→HTTPS redirect (port 80 → 443)
- TLS 1.2/1.3, современные cipher suites, OCSP stapling, session cache
- `Strict-Transport-Security` (HSTS, 1 год)
- `Content-Security-Policy`, `Permissions-Policy`, полный набор security headers
- Пути к сертификатам Let's Encrypt: `./ssl/fullchain.pem`, `./ssl/privkey.pem`

### Backend

#### CORS (S-02)

- `backend/app/core/config.py` — добавлена настройка `allowed_origins: List[str]` с разумными dev-дефолтами
- `backend/app/main.py` — `allow_origins` берётся из `settings.allowed_origins`; `allow_methods` и `allow_headers` сужены до необходимых; Swagger отключён при `DEBUG=false`

#### Аутентификация на download endpoint (S-04)

- `GET /tickets/{id}/attachments/{fid}/download` — добавлены `Depends(get_current_user)` и `client_scope`; анонимный доступ возвращает 401; `client_user` получает 404 при попытке скачать файл чужой организации

#### Row-level security: tickets (S-05, S-11)

- `PUT /tickets/{id}` — добавлен `client_scope`; `client_user` получает 404 при попытке изменить чужую заявку
- `PATCH /tickets/{id}/assign` — роль `client_user` удалена из разрешённых; только `admin`, `svc_mgr`
- `PATCH /tickets/{id}/status` — добавлены `require_roles("admin","svc_mgr","engineer","client_user")` и `client_scope`

#### Row-level security: client sub-resources (S-06)

- `GET /clients/{id}/contacts` — добавлен `client_scope`; 404 при попытке просмотреть контакты чужой организации
- `GET /clients/{id}/equipment` — аналогично
- `GET /clients/{id}/tickets` — аналогично

### Документация

- `docs/security-audit.md` — отчёт аудита безопасности (19 уязвимостей, оценки, рекомендации)

### Тесты

- `backend/tests/test_security_fixes.py` — 20 тестов: S-04 (download auth), S-05 (update/assign row-level), S-06 (sub-resource row-level), S-11 (status change roles)
- `backend/tests/test_tickets.py` — обновлён `TestTicketFilesDownload`: все вызовы download с auth headers

---

## [0.5.0] — 2026-04-03

**Портал самообслуживания клиента (UC-301)** — роль `client_user`, изоляция данных по организации, управление комментариями и подпись актов.

**Ключевые изменения:**

- Новая роль `client_user`: выдача и отзыв доступа к порталу из карточки клиента
- Row-level фильтрация для `client_user` на всех list- и **detail-эндпоинтах** — попытка открыть данные чужой организации по прямому URL возвращает HTTP 404
- Комментарии: `client_user` не видит внутренние комментарии, не может пометить свой как внутренний; в шапке комментария отображаются ФИО и email автора
- Акт выполненных работ: `client_user` может подписать акт своей организации
- 28 новых тестов (305 всего)

### UC-301 — Управление контактами клиента (расширение)

#### Новая роль: `client_user`
- Роль для сотрудников клиентских организаций, получивших доступ к порталу
- При выдаче доступа к порталу автоматически создаётся учётная запись пользователя с ролью `client_user`
- Временный пароль возвращается в ответе API (отображается однократно)
- При отзыве доступа учётная запись деактивируется

#### Права доступа `client_user` (RBAC)
- **Заявки** — только своей организации (чтение + создание)
- **Клиенты** — только своя организация
- **Оборудование** — только своей организации
- **Модели оборудования** — весь справочник (только чтение)
- **Счета** — только своей организации
- **Пользователи** — только пользователи своей организации
- **Склад запчастей** — доступ закрыт (403)

#### Backend
- `backend/app/api/deps.py` — добавлена зависимость `get_client_scope()`: возвращает `client_id` для `client_user`, иначе `None`
- `backend/app/models/__init__.py` — модель `User`: добавлено поле `client_id` (FK → clients); модель `ClientContact`: добавлены поля `is_primary`, `portal_access`, `portal_role`, `portal_user_id`, `created_by`, `created_at`, `updated_at`
- `backend/app/schemas/__init__.py` — новые схемы: `ClientContactUpdate`, `ClientContactPortalAccess`, `ClientContactPortalGrantResponse`
- `backend/app/api/endpoints/clients.py` — полная реализация CRUD контактов + `POST /{id}/contacts/{cid}/portal-access` (выдача) + `DELETE` (отзыв)
- `backend/app/api/endpoints/tickets.py` — фильтрация по `client_scope`
- `backend/app/api/endpoints/equipment.py` — фильтрация по `client_scope`
- `backend/app/api/endpoints/invoices.py` — фильтрация по `client_scope`
- `backend/app/api/endpoints/users.py` — фильтрация по `client_scope`
- `backend/app/api/endpoints/parts.py` — блокировка `client_user` с 403

#### Миграции
- `007_client_contacts_portal.py` — поля портала в `client_contacts`
- `008_client_user_role.py` — `client_id` в `users`, `portal_user_id` в `client_contacts`

#### Frontend
- `frontend/src/api/types.ts` — `client_user` в тип `UserRole`; `client_id` в интерфейс `User`
- `frontend/src/components/Layout.tsx` — `client_user` в `ROLE_LABELS`; пункт «Склад» скрыт для `client_user`; «Пользователи» доступен `client_user`
- `frontend/src/App.tsx` — маршруты `/users` и `/equipment-models` открыты для `client_user`
- `frontend/src/api/endpoints.ts` — новые методы: `updateClientContact`, `deactivateClientContact`, `grantPortalAccess`, `revokePortalAccess`
- `frontend/src/hooks/useClients.ts` — хуки для новых операций с контактами
- `frontend/src/pages/ClientDetailPage.tsx` — полный CRUD контактов: добавление, редактирование, деактивация, выдача/отзыв доступа к порталу
- `frontend/src/pages/UsersPage.tsx` — редактирование и деактивация/активация пользователей

#### Документация
- `docs/UC-301.md` — обновлён основной поток: выдача доступа создаёт учётную запись
- `docs/RBAC_Matrix.md` — добавлена роль `client_user` с полной матрицей прав
- `docs/ER_DataModel.md` — обновлены таблицы `users` и `client_contacts`

#### Тесты
- `backend/tests/test_client_user_role.py` — 15 тестов: выдача/отзыв портального доступа, row-level фильтрация по всем модулям, 403 для склада

---

### Безопасность — row-level фильтрация на detail-эндпоинтах

- [backend] `GET /tickets/{id}` — добавлена проверка `client_scope`: `client_user` получает HTTP 404 при попытке открыть заявку чужой организации
- [backend] `GET /tickets/{id}/comments`, `POST /tickets/{id}/comments`, `GET /tickets/{id}/attachments`, `GET /tickets/{id}/work-act`, `GET /tickets/{id}/status-history` — все sub-resource эндпоинты проверяют `client_scope` через обновлённый `_require_ticket(db, ticket_id, client_scope)`
- [backend] `GET /clients/{id}` — `client_user` получает HTTP 404, если `id != users.client_id`
- [backend] `GET /equipment/{id}` — добавлена проверка `client_scope`
- [backend] `GET /equipment/{id}/history` — добавлена проверка `client_scope`
- [docs] `UC-901.md` (v1.3) — добавлен раздел «Ограничения доступа для client_user» с таблицей всех эндпоинтов
- [docs] `UC-301.md` (v1.2) — добавлен раздел «Ограничения доступа client_user к данным клиента»
- [docs] `UC-1001.md` — добавлено ограничение для `client_user` в разделе RBAC
- [tests] `test_row_level_detail.py` — 16 тестов: попытки доступа к чужим заявкам, клиентам, оборудованию возвращают 404; доступ к своим — 200

---

### UC-301 — Портал клиента: комментарии и подпись акта

- [backend] `TicketComment`: добавлено поле `is_internal` (boolean, default false); миграция `009_ticket_comments_is_internal.py`
- [backend] `CommentCreate`: поле `is_internal: bool = False`; `CommentResponse`: поле `is_internal` + вложенный `author` (full_name, email); новая схема `CommentAuthorResponse`
- [backend] `GET /tickets/{id}/comments` — `client_user` видит только внешние комментарии (`is_internal=False`); ответ включает автора
- [backend] `POST /tickets/{id}/comments` — сохраняет `is_internal` из запроса; возвращает автора
- [backend] `POST /tickets/{id}/work-act/{act_id}/sign` — добавлена роль `client_user`; row-level проверка: `ticket.client_id == current_user.client_id`
- [frontend] `TicketDetailPage` — чекбокс «Внутренний комментарий» скрыт для `client_user`; `canSignAct` включает `client_user`; email автора отображается рядом с именем
- [docs] `UC-301.md` v1.1 — добавлен раздел «Поведение client_user на карточке заявки»
- [docs] `RBAC_Matrix.md` v2.2 — расширена таблица client_user: комментарии и подпись акта
- [tests] `test_comments_and_sign.py` — 12 тестов: видимость комментариев, автор в ответе, подпись акта, row-level защита, двойная подпись (400)

---

## [0.4.0] — 2026-04-02

### Модели оборудования (UC-1007)
- Справочник моделей с CRUD, активация/деактивация
- Страница `/equipment-models`

### Другие улучшения
- Bat-скрипт `scripts/start.bat` для запуска локального стенда
- UC-1008, UC-1009, UC-912 — документация

---

## [0.3.0] — 2026-03-xx

### Паспорт оборудования (UC-1001)
- Страница `/equipment/:id` — карточка оборудования с заявками

---

## [0.2.0] — ранее

### CRM — клиенты, заявки, уведомления, пользователи
- Клиентская база с контактами
- Заявки на ремонт/ТО
- Система уведомлений
- Управление пользователями
