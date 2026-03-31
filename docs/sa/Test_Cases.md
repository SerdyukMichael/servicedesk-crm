# Test Cases — ServiceDesk CRM

**Версия:** 1.0 | **Дата:** 27.03.2026 | **Автор:** Solution Architect

> 56 тест-кейсов охватывают Modules 8, 9, 10, 14 (MVP scope).
> Smoke-набор (20 кейсов) отмечен **[SMOKE]** — запускается в CI на каждый push.
> Формат: Предусловие → Шаги → Ожидаемый результат.

---

## Условные обозначения

| Маркер | Значение |
|---|---|
| **[SMOKE]** | Обязательный в CI, запускается на каждый push |
| **[RBAC]** | Тест проверяет права доступа |
| **[BR]** | Тест проверяет бизнес-правило |
| **[NEG]** | Негативный тест (ошибочный сценарий) |

---

## Module 8 — Управление пользователями

### T-AUTH-001 [SMOKE] — Успешная аутентификация

**Предусловие:** Пользователь admin@company.ru с ролью admin существует в БД.

**Шаги:**
1. `POST /api/v1/auth/login` с телом `{"email": "admin@company.ru", "password": "correctpass"}`

**Ожидаемый результат:**
- HTTP 200
- Тело: `{"access_token": "<jwt>", "token_type": "bearer"}`
- Токен декодируется, содержит `sub` = id пользователя
- `exp` = текущее время + 480 минут

---

### T-AUTH-002 [SMOKE][NEG] — Неверный пароль

**Шаги:**
1. `POST /api/v1/auth/login` с `{"email": "admin@company.ru", "password": "wrongpass"}`

**Ожидаемый результат:**
- HTTP 401
- `{"error": "INVALID_CREDENTIALS", "message": "Неверный email или пароль", "details": {}}`

---

### T-AUTH-003 [SMOKE][NEG] — Запрос без токена

**Шаги:**
1. `GET /api/v1/tickets` без заголовка `Authorization`

**Ожидаемый результат:**
- HTTP 401
- `{"error": "INVALID_TOKEN", ...}`

---

### T-AUTH-004 [NEG] — Истёкший токен

**Предусловие:** Токен с `exp` в прошлом.

**Шаги:**
1. `GET /api/v1/tickets` с заголовком `Authorization: Bearer <expired_token>`

**Ожидаемый результат:**
- HTTP 401

---

### T-USR-001 [SMOKE][RBAC] — Admin создаёт пользователя

**Предусловие:** Токен пользователя с ролью `admin`.

**Шаги:**
1. `POST /api/v1/users` с телом:
   ```json
   {"email": "engineer1@company.ru", "full_name": "Иван Петров", "role": "engineer", "password": "pass12345"}
   ```

**Ожидаемый результат:**
- HTTP 201
- `id` заполнен
- `hashed_password` не возвращается в ответе
- `is_active = true`, `is_deleted = false`

---

### T-USR-002 [SMOKE][RBAC][NEG] — Engineer не может создать пользователя

**Предусловие:** Токен пользователя с ролью `engineer`.

**Шаги:**
1. `POST /api/v1/users` с валидным телом

**Ожидаемый результат:**
- HTTP 403
- `{"error": "FORBIDDEN", ...}`

---

### T-USR-003 [BR][NEG] — Дубликат email

**Предусловие:** Пользователь с email `existing@company.ru` существует.

**Шаги:**
1. `POST /api/v1/users` с `email = "existing@company.ru"` (admin токен)

**Ожидаемый результат:**
- HTTP 409
- `{"error": "CONFLICT", ...}`

---

### T-USR-004 [BR][NEG] — Нельзя удалить самого себя

**Предусловие:** Администратор авторизован.

**Шаги:**
1. `DELETE /api/v1/users/{own_id}` с токеном этого же пользователя

**Ожидаемый результат:**
- HTTP 400
- `{"error": "CANNOT_DELETE_SELF", ...}`

---

### T-USR-005 — Soft delete пользователя

**Предусловие:** Пользователь с id=5 существует, токен admin.

**Шаги:**
1. `DELETE /api/v1/users/5`
2. `GET /api/v1/users/5`

**Ожидаемый результат:**
- Шаг 1: HTTP 204
- Шаг 2: HTTP 404 (запись помечена is_deleted=true, не возвращается)

---

### T-USR-006 [RBAC] — Инженер видит только свой профиль

**Предусловие:** Токен инженера.

**Шаги:**
1. `GET /api/v1/users` (список всех)

**Ожидаемый результат:**
- HTTP 403 — инженер не может просматривать список пользователей

---

## Module 10 — Оборудование

### T-EQP-001 [SMOKE][BR][NEG] — Дубликат серийного номера

**Предусловие:** Оборудование с `serial_number = "SN-TEST-0001"` существует.

**Шаги:**
1. `POST /api/v1/equipment` с `serial_number = "SN-TEST-0001"` (admin токен)

**Ожидаемый результат:**
- HTTP 409
- `{"error": "CONFLICT", "message": "Оборудование с серийным номером 'SN-TEST-0001' уже существует", ...}`

---

### T-EQP-002 [SMOKE] — Получить карточку оборудования

**Предусловие:** Оборудование с id=10 существует.

**Шаги:**
1. `GET /api/v1/equipment/10`

**Ожидаемый результат:**
- HTTP 200
- `serial_number`, `client_id`, `warranty_status` заполнены
- `warranty_status` ∈ {valid, expiring_soon, expired}

---

### T-EQP-003 — Создание оборудования

**Шаги:**
1. `POST /api/v1/equipment` с телом:
   ```json
   {"serial_number": "SN-NEW-9999", "client_id": 1, "model_id": 1, "warranty_expiry": "2027-12-31"}
   ```

**Ожидаемый результат:**
- HTTP 201
- `warranty_status = "valid"` (срок не истёк)

---

### T-EQP-004 — Soft delete оборудования

**Шаги:**
1. `DELETE /api/v1/equipment/{id}` (admin)
2. `GET /api/v1/equipment/{id}`

**Ожидаемый результат:**
- Шаг 1: HTTP 204
- Шаг 2: HTTP 404

---

### T-EQP-005 — Список оборудования с фильтром по клиенту

**Предусловие:** Клиент A имеет 3 единицы, Клиент B — 2 единицы.

**Шаги:**
1. `GET /api/v1/equipment?client_id={client_a_id}`

**Ожидаемый результат:**
- HTTP 200
- `total = 3`
- Все элементы имеют `client_id = client_a_id`

---

### T-EQP-006 — Загрузка документа к оборудованию

**Предусловие:** Оборудование с id=10 существует.

**Шаги:**
1. `POST /api/v1/equipment/10/documents` multipart с PDF файлом 5 МБ

**Ожидаемый результат:**
- HTTP 201
- `{"id": N, "file_name": "...", "mime_type": "application/pdf", "file_size": ...}`

---

### T-EQP-007 [BR][NEG] — Файл превышает 20 МБ

**Шаги:**
1. `POST /api/v1/equipment/10/documents` multipart с файлом 25 МБ

**Ожидаемый результат:**
- HTTP 400
- `{"error": "FILE_TOO_LARGE", ...}`

---

### T-EQP-008 — История ремонтов (UC-1002)

**Предусловие:** Оборудование id=X имеет 3 записи в `repair_history` (автосозданы при завершении заявок).

**Шаги:**
1. `GET /api/v1/equipment/{id}/history`

**Ожидаемый результат:**
- HTTP 200
- Массив из 3 объектов с полями `work_type`, `work_date`, `description`, `parts_used`, `ticket_id`
- Записи отсортированы по `work_date DESC` (новые сверху)

---

### T-EQP-009 — Фильтр истории по типу работ (UC-1002)

**Предусловие:** `repair_history` для оборудования: 2 записи `unplanned_repair`, 1 запись `planned_maintenance`.

**Шаги:**
1. `GET /api/v1/equipment/{id}/history?work_type=unplanned_repair`

**Ожидаемый результат:**
- HTTP 200
- Массив из 2 объектов, все `work_type = "unplanned_repair"`

---

### T-EQP-010b — Авто-создание записи при завершении заявки (BR-F-906)

**Предусловие:** Заявка типа `maintenance` назначена на оборудование, статус `in_progress`.

**Шаги:**
1. `PATCH /api/v1/tickets/{id}/status` `{"status": "completed"}`
2. `GET /api/v1/equipment/{equipment_id}/history`

**Ожидаемый результат:**
- В истории появилась новая запись с `work_type = "planned_maintenance"`
- `ticket_id` равен id завершённой заявки

---

### T-EQP-010 — Скачать документ оборудования (BLOB)

**Предусловие:** Документ с id=7 загружен (PDF).

**Шаги:**
1. `GET /api/v1/files/equipment-documents/7`

**Ожидаемый результат:**
- HTTP 200
- `Content-Type: application/pdf`
- Тело — байты PDF файла

---

## Module 9 — Заявки на обслуживание

### T-TKT-001 [SMOKE] — Создание заявки

**Предусловие:** Клиент с id=1 существует, admin токен.

**Шаги:**
1. `POST /api/v1/tickets` с телом:
   ```json
   {"title": "Замятие карт", "priority": "high", "ticket_type": "repair", "client_id": 1}
   ```

**Ожидаемый результат:**
- HTTP 201
- `ticket_number` соответствует шаблону `SD-2026-NNNNNN`
- `status = "new"`
- `sla_violated = false`
- `sla_deadline` = created_at + 8 ч (приоритет high)

---

### T-TKT-002 [SMOKE] — Назначение инженера

**Предусловие:** Заявка со статусом `new`, инженер с id=3 существует.

**Шаги:**
1. `PATCH /api/v1/tickets/{id}/assign` с `{"engineer_id": 3}` (svc_mgr токен)

**Ожидаемый результат:**
- HTTP 200
- `status = "in_progress"`
- `assigned_engineer_id = 3`

---

### T-TKT-003 [SMOKE][BR][NEG] — Закрытие без акта

**Предусловие:** Заявка в статусе `resolved`, акта нет.

**Шаги:**
1. `PATCH /api/v1/tickets/{id}/status` с `{"status": "closed"}`

**Ожидаемый результат:**
- HTTP 400
- `{"error": "TICKET_CLOSE_WITHOUT_ACT", "message": "Нельзя закрыть заявку без подписанного акта", ...}`

---

### T-TKT-004 [SMOKE][RBAC] — Инженер видит только свои заявки

**Предусловие:** Инженер A назначен на 2 заявки, инженер B — на 3.

**Шаги:**
1. Войти под инженером A
2. `GET /api/v1/tickets`

**Ожидаемый результат:**
- HTTP 200
- `total = 2`
- Все заявки имеют `assigned_engineer_id = A.id`

---

### T-TKT-005 [NEG] — Несуществующая заявка

**Шаги:**
1. `GET /api/v1/tickets/99999`

**Ожидаемый результат:**
- HTTP 404
- `{"error": "TICKET_NOT_FOUND", ...}`

---

### T-TKT-006 — Полный жизненный цикл заявки

**Шаги:**
1. `POST /tickets` → `status = new`
2. `PATCH /tickets/{id}/assign` → `status = in_progress`
3. `POST /tickets/{id}/work-act` с `work_description`
4. `POST /tickets/{id}/work-act/sign`
5. `PATCH /tickets/{id}/status` с `status = resolved`
6. `PATCH /tickets/{id}/status` с `status = closed`

**Ожидаемый результат:**
- Все шаги: HTTP 200/201
- Финальный `status = "closed"`
- `closed_at` заполнено

---

### T-TKT-007 — Фильтр заявок по статусу

**Предусловие:** 3 заявки new, 2 заявки in_progress.

**Шаги:**
1. `GET /api/v1/tickets?status=new`

**Ожидаемый результат:**
- `total = 3`
- Все `status = "new"`

---

### T-TKT-008 [BR] — Недопустимый переход статуса

**Предусловие:** Заявка в статусе `new`.

**Шаги:**
1. `PATCH /api/v1/tickets/{id}/status` с `{"status": "closed"}`

**Ожидаемый результат:**
- HTTP 400
- `{"error": "INVALID_STATUS_TRANSITION", ...}`

---

### T-TKT-009 — Применение шаблона при создании заявки (UC-911)

**Предусловие:** Шаблон id=5 с 3 работами и 2 запчастями для модели оборудования M.

**Шаги:**
1. `POST /api/v1/tickets` с `{"work_template_id": 5, ..., "equipment_id": (оборудование модели M)}`

**Ожидаемый результат:**
- HTTP 201
- В ответе `work_items` содержит 3 работы из шаблона
- `parts` содержит 2 позиции из шаблона

---

### T-TKT-010 — Добавление комментария

**Предусловие:** Заявка id=10 существует.

**Шаги:**
1. `POST /api/v1/tickets/10/comments` с `{"text": "Выехал на объект"}`
2. `GET /api/v1/tickets/10/comments`

**Ожидаемый результат:**
- Шаг 1: HTTP 201, `{"id": N, "text": "Выехал на объект", "author_name": ...}`
- Шаг 2: массив содержит добавленный комментарий

---

### T-TKT-011 — Загрузка вложения к заявке

**Шаги:**
1. `POST /api/v1/tickets/10/attachments` multipart с JPEG файлом 2 МБ

**Ожидаемый результат:**
- HTTP 201
- `{"id": N, "mime_type": "image/jpeg", "file_size": ...}`

---

### T-TKT-012 [BR][NEG] — Недопустимый тип файла для акта (фото)

**Шаги:**
1. Попытка загрузить `.exe` файл как вложение

**Ожидаемый результат:**
- HTTP 400
- `{"error": "UNSUPPORTED_FILE_TYPE", ...}`

---

### T-TKT-013 — Подписание акта выполненных работ

**Предусловие:** Заявка в статусе `in_progress`, акт создан (status=draft).

**Шаги:**
1. `POST /api/v1/tickets/{id}/work-act/sign`

**Ожидаемый результат:**
- HTTP 200
- `status = "signed"`
- `signed_at` заполнено

---

### T-TKT-014 — SLA нарушение помечается

**Предусловие:** Заявка priority=critical, created_at = 5 часов назад, status != closed.

**Шаги:**
1. Вызов `SLAService.check_violations(db)` (или Celery-задача)
2. `GET /api/v1/tickets/{id}`

**Ожидаемый результат:**
- `sla_violated = true`

---

### T-TKT-015 [RBAC] — Директор не может создавать заявки

**Предусловие:** Токен пользователя с ролью `director`.

**Шаги:**
1. `POST /api/v1/tickets` с валидным телом

**Ожидаемый результат:**
- HTTP 403

---

## Module 9 — Шаблоны работ (UC-911)

### T-TPL-001 [SMOKE][BR][NEG] — Создание шаблона без работ

**Шаги:**
1. `POST /api/v1/work-templates` с `{"name": "Пустой", "equipment_model_id": 1, "work_items": []}` (svc_mgr токен)

**Ожидаемый результат:**
- HTTP 400
- `{"error": "EMPTY_WORK_TEMPLATE", "message": "Добавьте хотя бы одну работу в шаблон", ...}`

---

### T-TPL-002 [SMOKE] — Создание валидного шаблона

**Шаги:**
1. `POST /api/v1/work-templates` с:
   ```json
   {
     "name": "ТО Matica XID 580i",
     "equipment_model_id": 1,
     "work_items": [{"order": 1, "description": "Чистка"}, {"order": 2, "description": "Смазка"}],
     "parts": [{"part_id": 5, "quantity": 2}]
   }
   ```

**Ожидаемый результат:**
- HTTP 201
- `work_items` содержит 2 позиции
- `parts` содержит 1 позицию

---

### T-TPL-003 [SMOKE] — Фильтр шаблонов по модели оборудования

**Предусловие:** Шаблон A для model_id=1, шаблон B для model_id=2.

**Шаги:**
1. `GET /api/v1/work-templates?equipment_model_id=1`

**Ожидаемый результат:**
- Массив содержит шаблон A
- Шаблон B не отображается

---

### T-TPL-004 — Редактирование шаблона

**Предусловие:** Шаблон с 2 работами.

**Шаги:**
1. `PUT /api/v1/work-templates/{id}` с 3 работами (добавлена третья)

**Ожидаемый результат:**
- HTTP 200
- `work_items` содержит 3 позиции

---

### T-TPL-005 — Soft delete шаблона

**Шаги:**
1. `DELETE /api/v1/work-templates/{id}` (svc_mgr токен)
2. `GET /api/v1/work-templates` — шаблон не возвращается

**Ожидаемый результат:**
- Шаг 1: HTTP 204
- Шаг 2: удалённый шаблон отсутствует в списке

---

### T-TPL-006 [RBAC][NEG] — Инженер не может удалить шаблон

**Шаги:**
1. `DELETE /api/v1/work-templates/{id}` с токеном engineer

**Ожидаемый результат:**
- HTTP 403

---

## Module 14 — Уведомления

### T-NTF-001 [SMOKE] — Количество непрочитанных

**Предусловие:** Пользователь авторизован, есть 2 непрочитанных уведомления.

**Шаги:**
1. `GET /api/v1/notifications/unread`

**Ожидаемый результат:**
- HTTP 200
- `{"count": 2}`

---

### T-NTF-002 [SMOKE][BR][NEG] — Нельзя отключить in_app канал

**Шаги:**
1. `PUT /api/v1/notifications/settings` с `[{"event_type": "ticket_assigned", "channel": "in_app", "enabled": false}]`

**Ожидаемый результат:**
- HTTP 400
- `{"error": "CANNOT_DISABLE_INAPP", ...}`

---

### T-NTF-003 — Создание уведомления при назначении заявки

**Предусловие:** Инженер с telegram_chat_id="123456789" и включёнными in_app + telegram уведомлениями.

**Шаги:**
1. `PATCH /api/v1/tickets/{id}/assign` (назначить инженера)

**Ожидаемый результат:**
- В таблице `notifications` создана запись для инженера с `event_type = "ticket_assigned"`
- Celery-задача отправки Telegram поставлена в очередь

---

### T-NTF-004 — Отметить прочитанным

**Предусловие:** Уведомление id=15, `is_read = false`.

**Шаги:**
1. `POST /api/v1/notifications/15/read`
2. `GET /api/v1/notifications` — проверить

**Ожидаемый результат:**
- Шаг 1: HTTP 204
- Шаг 2: уведомление id=15 имеет `is_read = true`

---

### T-NTF-005 — Отметить все прочитанными

**Предусловие:** 5 непрочитанных уведомлений.

**Шаги:**
1. `POST /api/v1/notifications/read-all`
2. `GET /api/v1/notifications/unread`

**Ожидаемый результат:**
- Шаг 1: HTTP 200, `{"updated": 5}`
- Шаг 2: `{"count": 0}`

---

### T-NTF-006 — Сброс настроек к умолчанию (UC-1401 АП-1)

**Предусловие:** Пользователь отключил email и telegram уведомления.

**Шаги:**
1. `POST /api/v1/notifications/settings/reset`
2. `GET /api/v1/notifications/settings`

**Ожидаемый результат:**
- Шаг 1: HTTP 204
- Шаг 2: все каналы `enabled = true`

---

### T-NTF-007 — SLA-нарушение генерирует уведомление руководителю

**Предусловие:** Заявка критического приоритета просрочена, svc_mgr с включёнными уведомлениями.

**Шаги:**
1. Запуск `SLAService.check_violations(db)`
2. `GET /api/v1/notifications` (под токеном svc_mgr)

**Ожидаемый результат:**
- Список содержит уведомление с `event_type = "sla_violated"`

---

### T-NTF-008 — Polling: уведомление появляется в течение 30 сек

**Предусловие:** Нет новых уведомлений у пользователя.

**Шаги:**
1. `GET /api/v1/notifications/unread` → `{"count": 0}`
2. (Другой пользователь назначает заявку)
3. Ждём до 30 секунд
4. `GET /api/v1/notifications/unread`

**Ожидаемый результат:**
- Шаг 4: `{"count": 1}`

---

## Отчёты

### T-RPT-001 — Отчёт по заявкам (UC-910)

**Предусловие:** За март 2026 создано 10 заявок, 8 закрыто в SLA, 2 с нарушением.

**Шаги:**
1. `GET /api/v1/reports/tickets?date_from=2026-03-01&date_to=2026-03-31` (director токен)

**Ожидаемый результат:**
- HTTP 200
- `total_tickets = 10`
- `sla_compliance.compliant = 8, violated = 2`
- `sla_compliance.pct ≈ 80.0`

---

### T-RPT-002 — Отчёт: нет данных за период

**Шаги:**
1. `GET /api/v1/reports/tickets?date_from=2020-01-01&date_to=2020-01-31`

**Ожидаемый результат:**
- HTTP 200
- `total_tickets = 0`

---

### T-RPT-003 — Экспорт PDF (UC-910)

**Шаги:**
1. `GET /api/v1/reports/tickets/export/pdf?date_from=2026-03-01&date_to=2026-03-31`

**Ожидаемый результат:**
- HTTP 200
- `Content-Type: application/pdf`
- Тело — непустые байты

---

### T-RPT-004 — Экспорт XLSX (UC-910)

**Шаги:**
1. `GET /api/v1/reports/tickets/export/xlsx?date_from=2026-03-01&date_to=2026-03-31`

**Ожидаемый результат:**
- HTTP 200
- `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

---

### T-RPT-005 — Отчёт по парку оборудования (UC-1006)

**Шаги:**
1. `GET /api/v1/reports/equipment?client_id=1` (director токен)

**Ожидаемый результат:**
- HTTP 200
- Данные только по клиенту id=1

---

### T-HLTH-001 [SMOKE] — Health check

**Шаги:**
1. `GET /health`

**Ожидаемый результат:**
- HTTP 200
- `{"status": "ok"}`

---

## Сводная таблица smoke-набора (20 кейсов)

| # | ID | Модуль | Описание |
|---|---|---|---|
| 1 | T-AUTH-001 | Auth | Успешный логин |
| 2 | T-AUTH-002 | Auth | Неверный пароль → 401 |
| 3 | T-AUTH-003 | Auth | Запрос без токена → 401 |
| 4 | T-USR-001 | Users | Admin создаёт пользователя |
| 5 | T-USR-002 | Users | Engineer не создаёт пользователей → 403 |
| 6 | T-EQP-001 | Equipment | Дубликат serial_number → 409 |
| 7 | T-EQP-002 | Equipment | Карточка оборудования |
| 8 | T-TKT-001 | Tickets | Создание заявки |
| 9 | T-TKT-002 | Tickets | Назначение инженера |
| 10 | T-TKT-003 | Tickets | Закрытие без акта → 400 |
| 11 | T-TKT-004 | Tickets | Инженер видит только свои заявки |
| 12 | T-TPL-001 | Templates | Шаблон без работ → 400 |
| 13 | T-TPL-002 | Templates | Создание валидного шаблона |
| 14 | T-TPL-003 | Templates | Фильтр по модели оборудования |
| 15 | T-NTF-001 | Notifications | Количество непрочитанных |
| 16 | T-NTF-002 | Notifications | Отключение in_app → 400 |
| 17 | T-FILE-001 | Files | Файл > 20 МБ → 400 |
| 18 | T-CLI-001 | Clients | Создание клиента |
| 19 | T-CLI-002 | Clients | Несуществующий клиент → 404 |
| 20 | T-HLTH-001 | Health | Health check |

---

## Клиенты — дополнительные

### T-CLI-001 [SMOKE] — Создание клиента

**Шаги:**
1. `POST /api/v1/clients` с `{"name": "ПАО Сбербанк", "inn": "7707083893"}` (admin токен)

**Ожидаемый результат:**
- HTTP 201
- `name = "ПАО Сбербанк"`

---

### T-CLI-002 [SMOKE][NEG] — Несуществующий клиент

**Шаги:**
1. `GET /api/v1/clients/99999`

**Ожидаемый результат:**
- HTTP 404

---

### T-FILE-001 [SMOKE][BR][NEG] — Файл > 20 МБ

**Шаги:**
1. `POST /api/v1/equipment/1/documents` с файлом 25 МБ

**Ожидаемый результат:**
- HTTP 400
- `{"error": "FILE_TOO_LARGE", ...}`
