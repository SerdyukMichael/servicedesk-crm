# ER: Модель данных — ServiceDesk CRM

**Версия:** 1.1 | **Дата:** 31.03.2026 | **Статус:** Актуально

> **v1.1 (аудит документации 31.03.2026):**
> - `users`: добавлены поля `position`, `department` (П-4)
> - `equipment.client_id`: изменён на nullable, SET NULL (П-1, UC-1008)
> - `tickets`: добавлены поля отмены `cancellation_reason`, `cancelled_by`, `cancelled_at` (UC-912)
> - `equipment_history`: поле `return_date` → `event_date`; добавлено `act_number` (П-2, UC-1007/1008)
> - `equipment_documents`: добавлено поле `history_id` (UC-1008)
> - `equipment_models`: добавлено поле `warranty_months_default` (UC-1009)

> Сводная схема всех сущностей MVP (Модули 8, 9, 10, 14).
> Поля собраны из раздела «Ключевые данные» каждого UC и RTM.
> Для реализации использовать SQLAlchemy ORM + Alembic.

---

## Условные обозначения

| Символ | Значение |
| --- | --- |
| `PK` | Primary key |
| `FK →` | Foreign key (ссылка на таблицу.поле) |
| `UQ` | Unique constraint |
| `NN` | Not Null |
| `SOFT` | Soft delete (`is_deleted = true`) |
| `COMP` | Вычисляемое поле (computed / property) |
| `JSON` | jsonb (PostgreSQL) / JSON (MySQL) |
| `AUDIT` | Изменения фиксируются в audit_log |

---

## Модуль 8 — Учёт персонала

### `users` — Карточки сотрудников (BR-F-800)

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | integer | PK, NN, autoincrement | Первичный ключ |
| email | varchar(128) | NN, UQ, index | Email (логин в систему) |
| full_name | varchar(128) | NN | ФИО |
| position | varchar(100) | | Должность (UC-801) |
| department | varchar(100) | | Подразделение (UC-801) |
| password_hash | varchar(255) | NN | bcrypt |
| roles | JSON | NN, default `["engineer"]` | Массив ролей: `["admin","svc_mgr"...]` — union прав (BR-F-801) |
| client_id | integer | FK → clients.id, SET NULL, nullable | Заполняется только для роли `client_user` — организация клиента |
| phone | varchar(32) | | Рабочий телефон |
| telegram_chat_id | varchar(64) | | Telegram chat ID для уведомлений |
| is_active | boolean | NN, default true | Активна ли учётная запись |
| is_deleted | boolean | NN, default false, SOFT | Soft delete |
| last_login_at | timestamp | | Дата последнего входа (read-only) |
| created_at | timestamp | NN | |
| updated_at | timestamp | NN | |

> **Допустимые роли:** `admin`, `sales_mgr`, `svc_mgr`, `engineer`, `manager`, `warehouse`, `accountant`, `director`, `client_user`
> Один сотрудник может иметь несколько ролей. Права = union всех ролей.

**Связи:** `engineer_competencies(engineer_id)`, `absences(user_id)`, `tickets(assigned_engineer_id)`, `tickets(created_by_user_id)`, `work_acts(via ticket)`, `audit_log(user_id)`

---

### `engineer_competencies` — Компетенции инженеров (BR-F-802)

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | bigint | PK, NN | |
| engineer_id | bigint | FK → users.id, NN | Только роль `service_engineer` |
| equipment_model_id | bigint | FK → equipment_models.id, NN | Модель из справочника |
| certificate_number | varchar(100) | | NULL если не заполнено |
| certificate_valid_until | date | | NULL = без срока; если заполнен и истёк → инженер недоступен для назначения |
| last_training_date | date | | Не позже текущей даты |
| is_deleted | boolean | NN, default false, SOFT | |

> **UQ:** пара `(engineer_id, equipment_model_id)` — уникальная.
> Если `certificate_valid_until` NULL — проверка срока не выполняется (BR-F-804).

---

### `absences` — Отпуска и больничные (BR-F-808)

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | bigint | PK, NN | |
| user_id | bigint | FK → users.id, NN | Сотрудник |
| type | enum | NN | `vacation` / `sick_leave` / `other` |
| start_date | date | NN | |
| end_date | date | NN | ≥ start_date |
| notes | text | | Комментарий |
| created_by | bigint | FK → users.id, NN | Кто создал запись |
| created_at | timestamp | NN | |

> При назначении заявки на инженера — система проверяет пересечение дат (предупреждение, не блокирует).

---

### `audit_log` — Аудит-лог (BR-F-807, BR-NF-014)

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | bigint | PK, NN | |
| user_id | bigint | FK → users.id | Кто совершил действие (NULL = system) |
| action | varchar(100) | NN | `create` / `update` / `delete` / `roles_assign` / etc. |
| entity | varchar(100) | NN | Имя сущности (`user`, `ticket`, `equipment`...) |
| entity_id | bigint | NN | ID изменённой записи |
| old_value | JSON | | Старое состояние |
| new_value | JSON | | Новое состояние |
| ip_address | varchar(45) | | IP-адрес клиента |
| created_at | timestamp | NN | Время события (append-only) |

> **Append-only**: DELETE/UPDATE на этой таблице запрещены на уровне БД.
> Хранение ≥ 2 лет (BR-NF-014).

---

## Справочники (используются несколькими модулями)

### `clients` — Клиентские организации

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | integer | PK, NN, autoincrement | |
| name | varchar(255) | NN, index | Название организации |
| inn | varchar(12) | | ИНН |
| kpp | varchar(9) | | КПП |
| legal_address | text | | Юридический адрес |
| contract_type | enum | NN, default `none` | `premium` / `standard` / `none` — тип договора (BR-F-902) |
| contract_number | varchar(64) | | |
| contract_valid_until | date | | |
| address | text | | Фактический адрес |
| manager_id | integer | FK → users.id, SET NULL | Ответственный менеджер |
| is_deleted | boolean | NN, default false, SOFT | |
| created_at | timestamp | NN | |
| updated_at | timestamp | NN | |

**Связи:** `equipment(client_id)`, `tickets(client_id)`, `client_contacts(client_id)`

---

### `client_contacts` — Контактные лица клиентов

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | integer | PK, NN, autoincrement | |
| client_id | integer | FK → clients.id, NN, CASCADE | Организация |
| name | varchar(128) | NN | ФИО контакта |
| phone | varchar(32) | | |
| email | varchar(128) | | |
| position | varchar(128) | | Должность |
| is_primary | boolean | NN, default false | Основной контакт организации |
| is_active | boolean | NN, default true | |
| portal_access | boolean | NN, default false | Есть ли доступ к порталу |
| portal_role | enum | nullable | `client_user` / `client_admin` |
| portal_user_id | integer | FK → users.id, SET NULL, nullable | Учётная запись в `users` (создаётся при выдаче доступа) |
| created_by | integer | FK → users.id, SET NULL | Кто создал |
| created_at | timestamp | NN | |
| updated_at | timestamp | NN | |

---

### `equipment_models` — Справочник моделей оборудования

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | integer | PK, NN, autoincrement | |
| name | varchar(255) | NN | Наименование модели |
| manufacturer | varchar(128) | | Производитель |
| category | enum | NN, default `other` | `atm` / `card_printer` / `pos_terminal` / `other` |
| description | text | | |
| warranty_months_default | integer | | Срок гарантии по умолчанию в месяцах (UC-1009) |
| is_active | boolean | NN, default true | |

---

### `spare_parts` — Номенклатура запчастей (склад)

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | integer | PK, NN, autoincrement | |
| sku | varchar(64) | NN, UQ, index | Артикул (SKU) |
| name | varchar(255) | NN | Наименование |
| category | varchar(64) | | Категория |
| unit | varchar(16) | NN, default `шт` | Единица измерения |
| quantity | integer | NN, default 0 | Текущий остаток |
| min_quantity | integer | NN, default 0 | Минимальный остаток (порог пополнения) |
| unit_price | decimal(12,2) | NN, default 0 | Цена за единицу |
| currency | varchar(3) | NN, default `RUB` | Валюта |
| vendor_id | integer | FK → vendors.id, SET NULL | Поставщик |
| description | text | | |
| is_active | boolean | NN, default true | |

---

## Модуль 10 — Учёт оборудования

### `equipment` — Паспорт оборудования (BR-F-1000)

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | integer | PK, NN, autoincrement | |
| client_id | integer | FK → clients.id, nullable, SET NULL | Текущий владелец; NULL = оборудование не закреплено за клиентом (UC-1008) |
| model_id | integer | FK → equipment_models.id, NN, RESTRICT | |
| serial_number | varchar(128) | NN, UQ | Глобально уникален (BR-R-008) |
| location | text | | Адрес/место установки |
| status | enum | NN, default `active` | `active` / `in_repair` / `decommissioned` / `written_off` |
| installed_at | date | | Дата установки |
| warranty_until | date | | Дата окончания гарантии |
| notes | text | | |
| is_deleted | boolean | NN, default false, SOFT | |
| created_at | timestamp | NN | |
| updated_at | timestamp | NN | |

---

### `equipment_documents` — Документы к оборудованию (BR-F-1004)

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | bigint | PK, NN | |
| equipment_id | bigint | FK → equipment.id, NN | |
| history_id | bigint | FK → equipment_history.id, nullable | Привязка к записи истории передач (UC-1008); NULL для общих документов |
| doc_type | enum | NN | `passport` / `warranty` / `manual` / `act` / `other` |
| file_name | varchar(255) | NN | |
| file_url | varchar(500) | NN | Ссылка на файловое хранилище |
| file_size_kb | integer | NN | |
| mime_type | varchar(100) | | `application/pdf`, `image/jpeg`... |
| uploaded_by | bigint | FK → users.id, NN | |
| uploaded_at | timestamp | NN | |
| is_deleted | boolean | NN, default false, SOFT | |

> Допустимые форматы: PDF, JPEG, PNG, DOCX, XLSX, ZIP. Максимум 20 МБ.

---

### `equipment_history` — История передач и возвратов (BR-R-009)

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | bigint | PK, NN | |
| equipment_id | bigint | FK → equipment.id, NN | |
| event_type | enum | NN | `initial_assignment` / `transfer` / `return` / `write_off` |
| from_client_id | bigint | FK → clients.id | Клиент до события (NULL при первоначальном назначении) |
| to_client_id | bigint | FK → clients.id | Клиент после (NULL при возврате без нового клиента) |
| return_type | enum | | `warranty_replacement` / `buyback` (только при event_type=return) |
| event_date | date | | Дата события (переименовано из `return_date` v1.1) |
| act_number | varchar(64) | | Номер акта приёма-передачи (UC-1008) |
| reason | text | | Обязательно при event_type=return; опционально для остальных |
| claim_created | boolean | | Создана ли рекламация вендору (Модуль 11) |
| recorded_by | bigint | FK → users.id, NN | |
| recorded_at | timestamp | NN | |

> Записи не удаляются физически (BR-R-009). append-only для event_type=return.

---

### `maintenance_schedules` — Графики планового ТО (BR-F-1009)

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | bigint | PK, NN | |
| equipment_id | bigint | FK → equipment.id, UQ | Один график на единицу |
| interval_months | integer | NN | Периодичность в месяцах |
| first_maintenance_date | date | NN | Дата первого ТО |
| next_maintenance_date | date | NN, COMP | Авто: last + interval |
| last_ticket_created_at | date | | Дата последней авто-заявки |
| is_active | boolean | NN, default true | |
| created_by | bigint | FK → users.id, NN | |
| updated_at | timestamp | NN | |

---

### `repair_history` — История ремонтов оборудования (BR-F-1001)

| Поле в БД | Псевдоним в API | Тип | Ограничения | Описание |
| --- | --- | --- | --- | --- |
| id | id | bigint | PK, NN | |
| equipment_id | equipment_id | bigint | FK → equipment.id, NN | |
| ticket_id | ticket_id | bigint | FK → tickets.id | NULL если без заявки |
| action_type | work_type | varchar(64) | NN | `unplanned_repair` / `planned_maintenance` / `warranty_repair` / `installation` / `diagnostics` |
| performed_at | work_date | timestamp | NN | Дата выполнения работ |
| performed_by | engineer_id | bigint | FK → users.id | |
| parts_used | parts_used | JSON | | [{part_id, name, qty}] — денормализованный снапшот |
| description | description | text | | |
| created_at | created_at | timestamp | NN | |

> **Примечание:** В DB-слое сохранены исторические имена (`action_type`, `performed_by`, `performed_at`). API экспонирует поля под именами из UC-1002 через псевдонимы Pydantic-схемы.

---

## Модуль 9 — Заявки на обслуживание

### `tickets` — Заявки (BR-F-900, BR-F-901)

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | integer | PK, NN, autoincrement | |
| number | varchar(32) | NN, UQ, index | Формат: T-YYYYMMDD-XXXX (например T-20260328-0001) |
| client_id | integer | FK → clients.id, NN, RESTRICT | |
| equipment_id | integer | FK → equipment.id, SET NULL | NULL если не привязана к оборудованию |
| assigned_to | integer | FK → users.id, SET NULL | NULL пока не назначен инженер |
| created_by | integer | FK → users.id, NN, RESTRICT | Кто создал |
| title | varchar(255) | NN | Заголовок заявки |
| description | text | | |
| type | enum | NN, default `repair` | `repair` / `maintenance` / `diagnostics` / `installation` |
| priority | enum | NN, default `medium` | `critical` / `high` / `medium` / `low` |
| status | enum | NN, default `new` | `new` / `assigned` / `in_progress` / `waiting_part` / `on_review` / `completed` / `closed` / `cancelled` |
| sla_deadline | timestamp | | Авто: created_at + SLA_HOURS[priority] |
| work_template_id | integer | FK → work_templates.id, SET NULL | Применённый шаблон |
| closed_at | timestamp | | |
| cancellation_reason | text | | Причина отмены; обязательна при status=cancelled (UC-912) |
| cancelled_by | integer | FK → users.id, SET NULL | Кто отменил (UC-912) |
| cancelled_at | timestamp | | Дата и время отмены (UC-912) |
| is_deleted | boolean | NN, default false, SOFT | |
| created_at | timestamp | NN | |
| updated_at | timestamp | NN | |

---

### `ticket_attachments` — Вложения заявок (BR-F-915)

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | bigint | PK, NN | |
| ticket_id | bigint | FK → tickets.id, NN | |
| file_name | varchar(255) | NN | |
| file_url | varchar(500) | NN | |
| file_size_kb | integer | NN | ≤ 20 МБ |
| uploaded_by_type | enum | NN | `client` / `engineer` / `operator` |
| uploaded_by_id | bigint | | FK → users.id или client_contacts.id |
| uploaded_at | timestamp | NN | |
| is_deleted | boolean | NN, default false, SOFT | |

---

### `work_acts` — Акты выполненных работ

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | integer | PK, NN, autoincrement | |
| ticket_id | integer | FK → tickets.id, NN, RESTRICT, UQ | Один акт на заявку |
| engineer_id | integer | FK → users.id, NN, RESTRICT | Исполнитель |
| work_description | text | | |
| parts_used | JSON | | Использованные запчасти (денормализованный снапшот) |
| total_time_minutes | integer | | |
| signed_by | integer | FK → users.id, SET NULL | Кто подписал акт |
| signed_at | timestamp | | |
| created_at | timestamp | NN | |

---

### `work_act_parts` — Использованные запчасти в акте (BR-F-907)

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | bigint | PK, NN | |
| work_act_id | bigint | FK → work_acts.id, NN | |
| part_id | bigint | FK → spare_parts.id, NN | |
| qty | integer | NN | > 0 |
| source | enum | NN, default 'main' | `main` / `engineer_mobile` — основной или передвижной склад |

> При сохранении акта (`is_draft = false`): `spare_parts.qty_main -= qty` (или с передвижного). Откат невозможен (BR-R-005).

---

### `ticket_comments` — Комментарии к заявкам

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | integer | PK, NN, autoincrement | |
| ticket_id | integer | FK → tickets.id, NN, CASCADE | |
| user_id | integer | FK → users.id, NN, RESTRICT | Автор комментария |
| text | text | NN | |
| created_at | timestamp | NN | |

---

### `work_templates` — Шаблоны типовых работ

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | integer | PK, NN, autoincrement | |
| name | varchar(255) | NN | |
| equipment_model_id | integer | FK → equipment_models.id, SET NULL | |
| description | text | | |
| is_active | boolean | NN, default true | |
| created_by | integer | FK → users.id, SET NULL | |
| created_at | timestamp | NN | |
| updated_at | timestamp | NN | |

### `work_template_steps` — Шаги шаблона работ

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | integer | PK, NN, autoincrement | |
| template_id | integer | FK → work_templates.id, NN, CASCADE | |
| step_order | integer | NN | Порядковый номер шага |
| description | text | NN | Описание шага |
| estimated_minutes | integer | | Оценочное время выполнения |

---

## Модуль 14 — Уведомления

### `notification_settings` — Настройки уведомлений пользователя (BR-F-1401)

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | bigint | PK, NN | |
| user_id | bigint | FK → users.id, NN | |
| event_type | enum | NN | 7 значений: `ticket_assigned_to_me` / `ticket_status_changed` / `sla_violation` / `payment_due` / `maintenance_due` / `warranty_expiring` / `new_comment_on_my_ticket` |
| channel | enum | NN | `email` / `push` / `in_app` |
| enabled | boolean | NN | |
| updated_at | timestamp | NN | |

> **UQ:** пара `(user_id, event_type, channel)`.
> `in_app` нельзя отключить (ИП-1 в UC-1401): CHECK constraint `NOT (channel='in_app' AND enabled=false)`.

---

### `notifications` — Лента in-app уведомлений (BR-F-1403)

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | integer | PK, NN, autoincrement | |
| user_id | integer | FK → users.id, NN, CASCADE | Получатель |
| event_type | varchar(64) | NN | |
| title | varchar(255) | NN | |
| body | text | | |
| ticket_id | integer | FK → tickets.id, SET NULL | Связанная заявка |
| is_read | boolean | NN, default false | |
| created_at | timestamp | NN | |

---

## Схема связей (краткий граф)

```
users ──┬──< engineer_competencies >── equipment_models
        ├──< absences
        ├──< tickets (assigned_engineer_id, created_by_user_id)
        ├──< comments (author_id)
        ├──< work_acts (via tickets)
        ├──< notification_settings
        └──< notifications

clients ──┬──< equipment (client_id)
           ├──< tickets (client_id)
           └──< client_contacts ──< comments (author_client_id)

equipment ──┬──< tickets (equipment_id)
             ├──< equipment_documents
             ├──< equipment_history
             ├──< repair_history
             └──── maintenance_schedules

tickets ──┬──< ticket_attachments
           ├──< work_acts ──< work_act_parts >── spare_parts
           ├──< comments
           └──< repair_history (ticket_id)
```

---

## Вендоры и запчасти

### `vendors` — Поставщики

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | integer | PK, NN, autoincrement | |
| name | varchar(255) | NN | |
| inn | varchar(12) | | |
| contact_name | varchar(128) | | |
| contact_phone | varchar(32) | | |
| contact_email | varchar(128) | | |
| website | varchar(255) | | |
| notes | text | | |
| is_active | boolean | NN, default true | |

---

## Финансы

### `invoices` — Счета

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | integer | PK, NN, autoincrement | |
| number | varchar(32) | NN, UQ, index | Номер счёта |
| client_id | integer | FK → clients.id, NN, RESTRICT | |
| ticket_id | integer | FK → tickets.id, SET NULL | Связанная заявка |
| type | enum | NN, default `service` | `service` / `parts` / `mixed` |
| status | enum | NN, default `draft` | `draft` / `sent` / `paid` / `cancelled` / `overdue` |
| issue_date | date | NN | Дата выставления |
| due_date | date | | Срок оплаты |
| subtotal | decimal(14,2) | NN, default 0 | Сумма без НДС |
| vat_rate | decimal(5,2) | NN, default 20.00 | Ставка НДС, % |
| vat_amount | decimal(14,2) | NN, default 0 | Сумма НДС |
| total_amount | decimal(14,2) | NN, default 0 | Итого к оплате |
| notes | text | | |
| created_by | integer | FK → users.id, NN, RESTRICT | |
| paid_at | timestamp | | |
| created_at | timestamp | NN | |
| updated_at | timestamp | NN | |

### `invoice_items` — Строки счёта

| Поле | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| id | integer | PK, NN, autoincrement | |
| invoice_id | integer | FK → invoices.id, NN, CASCADE | |
| description | varchar(512) | NN | |
| quantity | decimal(10,3) | NN, default 1 | |
| unit | varchar(16) | NN, default `шт` | |
| unit_price | decimal(12,2) | NN | |
| total | decimal(14,2) | NN | quantity × unit_price |
| sort_order | integer | NN, default 0 | |

---

## Таблицы-справочники (seed data)

При инициализации системы заполнить:

| Таблица | Данные |
| --- | --- |
| `equipment_models` | Список моделей банкоматов и платёжного оборудования |
| `notification_settings` | Матрица умолчаний (BR-F-1401): все события включены для email и in_app |
| `spare_parts` | Базовая номенклатура запчастей |

---

## Модели, запланированные для будущих фаз

| Модуль | Таблица | Статус |
| --- | --- | --- |
| Модуль 11 (Рекламации) | `vendor_claims` | Backlog |
| Модуль 3 (Продажи) | `sales_orders` | Backlog |
| Модуль 8 (HR) | `engineer_competencies`, `absences` | Backlog |

