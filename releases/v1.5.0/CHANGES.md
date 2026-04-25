# v1.5.0 — SLA, Аудит-лог, Отчёты, График ТО

## Backend

### UC-905 — SLA полноценно
- Новые поля в таблице `tickets`: `sla_reaction_deadline`, `sla_reaction_violated`, `sla_resolution_violated`
- Celery-beat задача `check_sla_deadlines`: автоматическая проверка нарушений каждые 5 минут
- Фильтр `sla_violated` в `GET /api/v1/tickets` с поддержкой старых заявок (fallback на `sla_deadline`)

### UC-806 — Аудит-лог
- Новая таблица `audit_log` с индексами по `user_id`, `entity_type`, `action`, `created_at`
- Сервис `app/services/audit.py` с функцией `log_action()` + `extract_ip()`
- Логирование всех write-операций во всех модулях: auth (LOGIN), users, clients, equipment, tickets, invoices
- `GET /api/v1/audit-log` — пагинированный список с фильтрами (user_id, action, entity_type, date range, IP)
- `GET /api/v1/audit-log/export` — экспорт в CSV

### UC-910 — Отчёт по заявкам
- `GET /api/v1/reports/tickets` — агрегаты: by_status, by_type, by_priority, by_engineer
- Метрики SLA: `sla_reaction_compliance_pct`, `sla_resolution_compliance_pct`, `avg_resolution_hours`
- Фильтры: period_from, period_to, client_id, engineer_id
- `GET /api/v1/reports/tickets/export` — экспорт в XLSX (openpyxl)

### UC-908 — График технического обслуживания
- Новая таблица `maintenance_schedules` (equipment_id, frequency, first_date, next_date, is_active)
- API: `GET/POST/PUT /api/v1/equipment/{id}/maintenance-schedule`
- Celery задача `process_maintenance_schedules`: автоматическое создание заявок ТО, обновление `next_date`
- Сервис `app/services/maintenance.py`

### UC-403 — Создание счёта по акту
- `POST /api/v1/invoices/from-act/{ticket_id}` — создание счёта из позиций акта выполненных работ

## Frontend

### UC-905 — SLA в карточке заявки
- Countdown до дедлайна с цветовой индикацией (зелёный / оранжевый / красный)
- Отдельные строки для SLA реакции и SLA решения
- Fallback на старое поле `sla_deadline` для заявок без новых полей

### UC-806 — Страница аудит-лога
- Таблица с фильтрами: пользователь, действие, тип объекта, даты, IP-адрес
- Кнопка «▼ Подробнее» для записей с diff: показывает таблицу Поле / Было / Стало
- Подсветка изменённых строк (жёлтый), удалённых (красный), добавленных (зелёный)
- Кнопка «Экспорт CSV»

### UC-910 — Страница отчётов
- 3 KPI-карточки: SLA реакции %, SLA решения %, Среднее время решения
- Графики by_status, by_type, by_priority, by_engineer
- Кнопка экспорта отключена при пустых данных

### UC-403 — Карточка заявки
- Кнопка «Создать счёт из акта» заблокирована при оборудовании на гарантии
- Tooltip «Оборудование на гарантии»

## Database (Alembic)

| Миграция | Описание |
|----------|----------|
| `f1a2b3c4d5e6` | SLA поля в таблице `tickets` |
| `a1b2c3d4e5f6` | Таблица `audit_log` + индексы |
| `b2c3d4e5f6a1` | Таблица `maintenance_schedules` |

## Зависимости

- Добавлены: `celery`, `redis`, `openpyxl`
