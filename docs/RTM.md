# RTM: Матрица трассировки требований

**Версия:** 1.3 | **Дата:** 14.04.2026 | **Статус:** В работе

> Структура: Требование → Use Case → Компонент системы → Тест

---

## Условные обозначения

**Приоритет:** Must = обязательно | Should = важно | Could = желательно

**Компонент:**
- `endpoints/` — FastAPI-роутеры (`backend/app/api/endpoints/`)
- `models/` — SQLAlchemy ORM-модели (`backend/app/models/`)
- `services/` — бизнес-логика (`backend/app/services/`)
- `schemas/` — Pydantic-схемы (`backend/app/schemas/`)

**Тест:** `T-{модуль}-{номер}` — идентификатор теста в `backend/tests/`

**Статус теста:** ⬜ не написан | 🟡 в работе | ✅ готов

---

## Модуль 1 — Прайс-листы

| # | Требование | Описание | Приоритет | UC | Компонент | Тест | Статус |
|---|-----------|----------|-----------|-----|-----------|------|--------|
| R1-1 | BR-F-110 | Справочник услуг (ServiceCatalog): код, наименование, категория, ед. изм., цена, валюта, is_active | Must | UC-101 | `models/service_catalog.py`, `endpoints/pricelist.py` | T-1-001 | ⬜ |
| R1-2 | BR-F-111 | Автоподстановка цены из справочника при добавлении в акт/счёт | Must | UC-101, UC-102 | `endpoints/pricelist.py`, `endpoints/tickets.py` | T-1-002 | ⬜ |
| R1-3 | BR-F-112 | Запрет физического удаления — только деактивация | Must | UC-101, UC-102 | `endpoints/pricelist.py` (guard) | T-1-003 | ⬜ |
| R1-4 | BR-F-113 | Позиции акта: тип `service` (из `service_catalog`) / `part` (из `spare_parts`), ссылка на справочник, цена зафиксирована на момент сохранения | Must | UC-101, UC-102 | `models/work_act_items.py`, `endpoints/tickets.py` | T-1-004 | ⬜ |
| R1-5 | BR-F-121 | Управление ценами каталога матценностей (`spare_parts`): установка/изменение цены с указанием валюты и причины; автозапись в `price_history` (`entity_type='spare_part'`); просмотр истории цен | Must | UC-102 | `models/spare_parts.py`, `models/price_history.py`, `endpoints/parts.py` | T-1-005 | ⬜ |
| R1-6 | BR-F-104 | История изменения цен: покрывает `service_catalog` (`entity_type='service'`) и `spare_parts` (`entity_type='spare_part'`); дата, автор, старая/новая цена, валюта, причина (обязательна ≥ 5 символов) | Should | UC-101, UC-102 | `models/price_history.py`, `endpoints/pricelist.py` | T-1-006 | ⬜ |
| R1-8 | BR-F-122 | В формах акта и счёта при выборе позиции из каталога матценностей отображаются только `spare_parts` с `unit_price > 0` | Must | UC-102 | `endpoints/parts.py` (query param `has_price=true`) | T-1-008 | ⬜ |
| R1-7 | BR-F-102 | Поддержка валют PLN/EUR/USD/RUB; ручная установка курса в настройках | Must | — | `models/exchange_rate.py`, `endpoints/settings.py` | T-1-007 | ⬜ |
| R1-9 | BR-F-125 | Возобновление заявки (closed/completed → in_progress): доступно admin/svc_mgr/client_user; engineer запрещено; closed_at сбрасывается; история обновляется; email-уведомление участникам | Must | — | `endpoints/tickets.py` (`_TRANSITIONS`, `_REOPEN_ROLES`), `core/email.py` | `tests/test_ticket_reopen.py` | ✅ |

---

## Модуль 3 — CRM: клиенты и контакты

| # | Требование | Описание | Приоритет | UC | Компонент | Тест | Статус |
|---|-----------|----------|-----------|-----|-----------|------|--------|
| R3-1 | BR-F-300 | Карточка клиента: название, ИНН, тип договора, город, менеджер, контакты | Must | UC-301 | `models/__init__.py` (Client), `endpoints/clients.py` | T-3-001 | ✅ |
| R3-2 | BR-F-301 | Управление контактами клиента: CRUD, основной контакт (is_primary), soft delete | Must | UC-301 | `models/__init__.py` (ClientContact), `endpoints/clients.py` | T-3-002 | ✅ |
| R3-3 | BR-F-302 | Выдача доступа к порталу: создаёт User с ролью `client_user` и `client_id`; возвращает временный пароль | Must | UC-301 | `endpoints/clients.py` (grant_portal_access), `models/__init__.py` (User.client_id) | T-3-003 | ✅ |
| R3-4 | BR-F-303 | Отзыв доступа к порталу: деактивирует связанную учётную запись User | Must | UC-301 | `endpoints/clients.py` (revoke_portal_access) | T-3-004 | ✅ |
| R3-5 | BR-F-304 | Роль `client_user`: row-level фильтрация — видит только данные своей организации (tickets, clients, equipment, invoices, users) | Must | UC-301 | `api/deps.py` (get_client_scope), все list-эндпоинты | T-3-005 | ✅ |
| R3-6 | BR-F-305 | Роль `client_user`: склад запчастей недоступен (403) | Must | UC-301 | `endpoints/parts.py` | T-3-006 | ✅ |
| R3-7 | BR-F-306 | Роль `client_user`: может создавать заявки только для своей организации | Must | UC-301 | `endpoints/tickets.py` (create_ticket) | T-3-007 | ✅ |
| R3-8 | BR-R-009 | Soft delete клиентов и контактов (`is_deleted`, `is_active`) | Must | UC-301 | `models/__init__.py`, `endpoints/clients.py` | T-3-008 | ✅ |
| R3-9 | BR-R-010 | Аудит-лог операций с контактами (create, update, deactivate, portal_access_grant/revoke) | Must | UC-301 | `models/__init__.py` (AuditLog), `endpoints/clients.py` | T-3-009 | ✅ |
| R3-10 | BR-F-801 | 9 ролей системы включая `client_user`; матрица прав в RBAC_Matrix.md | Must | UC-301, UC-801 | `api/deps.py` (require_roles, get_client_scope) | T-3-010 | ✅ |

> Миграции: `007_client_contacts_portal.py`, `008_client_user_role.py`
> Тесты: `backend/tests/test_client_user_role.py` (15 тестов), `test_clients.py`

---

## Модуль 4 — Счета

| # | Требование | Описание | Приоритет | UC | Компонент | Тест | Статус |
|---|-----------|----------|-----------|-----|-----------|------|--------|
| R4-1 | BR-F-400 | Создание счёта: номер, клиент, дата, позиции, НДС | Must | UC-401 | `models/invoice.py`, `endpoints/invoices.py` | T-4-001 | ⬜ |
| R4-2 | BR-F-411 | Строки счёта: тип `service` / `part` / `manual`; ссылка на `service_catalog` или `spare_parts` (только с ценой); `manual` — без привязки к справочнику | Must | UC-401 | `models/invoice_items.py`, `endpoints/invoices.py` | T-4-002 | ⬜ |
| R4-3 | BR-F-118 | Создание счёта из акта только при наличии позиций | Must | UC-403 | `endpoints/invoices.py` (guard) | T-4-003 | ⬜ |
| R4-4 | BR-F-119 | Отображение ссылки на счёт рядом с актом в карточке заявки | Should | UC-401 | `endpoints/tickets.py` | T-4-004 | ⬜ |
| R4-5 | BR-F-120 | Статус оплаты счёта отображается рядом с актом | Must | UC-401 | `endpoints/invoices.py`, `endpoints/tickets.py` | T-4-005 | ⬜ |

---

## Модуль 8 — Учёт персонала

| # | Требование | Описание | Приоритет | UC | Компонент | Тест | Статус |
|---|-----------|----------|-----------|-----|-----------|------|--------|
| 1 | BR-F-800 | Карточка сотрудника: ФИО, роль, фото, контакты, статус, дата приёма | Must | UC-801 | `models/user.py`, `endpoints/users.py`, `schemas/user.py` | T-8-001 | ⬜ |
| 2 | BR-F-801 | 7 фиксированных ролей с матрицей прав доступа | Must | UC-801, UC-802 | `models/user.py`, `core/security.py`, `api/deps.py` | T-8-002 | ⬜ |
| 3 | BR-F-802 | Профиль компетенций инженера: модели оборудования, сертификаты, даты обучения | Must | UC-803 | `models/competency.py`, `endpoints/employees.py` | T-8-003 | ⬜ |
| 4 | BR-F-803 | Панель загрузки инженеров с индикаторами нагрузки (🟢🟡🔴⚫) | Must | UC-804 | `endpoints/requests.py`, `services/engineer_load.py` | T-8-004 | ⬜ |
| 5 | BR-F-804 | Фильтрация инженеров по компетенции и статусу при назначении заявки | Must | UC-803, UC-804, UC-902 | `services/engineer_load.py`, `models/competency.py` | T-8-005 | ⬜ |
| 6 | BR-F-806 | Управление ролями и правами: назначение, отзыв, аудит | Must | UC-802 | `endpoints/users.py`, `models/user.py`, `models/audit_log.py` | T-8-006 | ⬜ |
| 7 | BR-F-807 | Аудит-лог всех действий пользователей: хранение ≥ 2 лет, только чтение | Must | UC-806 | `models/audit_log.py`, `endpoints/audit.py`, `services/audit.py` | T-8-007 | ⬜ |
| 8 | BR-F-808 | Предупреждение при назначении заявки инженеру в отпуске (не блокирует) | Could | UC-805, UC-902 | `models/absence.py`, `services/ticket_service.py` | T-8-008 | ⬜ |
| 9 | BR-F-810 | Запрет редактирования отпусков для уволенных сотрудников | — | UC-805 | `models/absence.py`, `endpoints/employees.py` | T-8-009 | ⬜ |
| 10 | BR-R-009 | Soft delete: физическое удаление записей запрещено (`is_deleted = true`) | — | UC-801, UC-802, UC-803, UC-805 | Все модели с `is_deleted` | T-8-010 | ⬜ |
| 11 | BR-R-010 | Аудит-лог: каждое изменение фиксируется с timestamp, user, old/new | — | UC-801, UC-802, UC-803, UC-806 | `models/audit_log.py`, `services/audit.py` | T-8-011 | ⬜ |
| 12 | BR-NF-014 | Логи хранятся ≥ 2 лет; append-only; удаление через интерфейс/API запрещено | — | UC-806 | `models/audit_log.py` (append-only constraint) | T-8-012 | ⬜ |

---

## Модуль 9 — Заявки на обслуживание

| # | Требование | Описание | Приоритет | UC | Компонент | Тест | Статус |
|---|-----------|----------|-----------|-----|-----------|------|--------|
| 13 | BR-F-900 | Регистрация заявки: тип, клиент, оборудование, описание, SLA-таймер | Must | UC-901 | `models/ticket.py`, `endpoints/requests.py`, `services/ticket_service.py` | T-9-001 | ⬜ |
| 14 | BR-F-901 | Жизненный цикл заявки: Новая→Назначена→В работе→Ожидание→Выполнена→Проверка→Закрыта | Must | UC-903 | `models/ticket.py`, `services/ticket_service.py` | T-9-002 | ⬜ |
| 15 | BR-F-902 | Авто-расчёт приоритета по типу договора и типу оборудования | Should | UC-901 | `services/ticket_service.py`, `models/contract.py` | T-9-003 | ⬜ |
| 16 | BR-F-903 | SLA-контроль: таймеры реакции и решения; флаги нарушения | Must | UC-901, UC-902, UC-905 | `models/ticket.py` (`sla_*` поля), `services/sla_service.py` | T-9-004 | ⬜ |
| 17 | BR-F-904 | Авто-эскалация при приближении к нарушению SLA | Must | UC-905 | `services/sla_service.py`, `services/notification_service.py` | T-9-005 | ⬜ |
| 18 | BR-F-905 | Инженер заполняет акт выполненных работ (описание, время, запчасти, фото) | Must | UC-904 | `models/work_act.py`, `endpoints/requests.py` | T-9-006 | ⬜ |
| 19 | BR-F-906 | Авто-создание записи в истории ремонтов при закрытии заявки | Must | UC-901, UC-904 | `models/repair_history.py`, `services/ticket_service.py` | T-9-007 | ⬜ |
| 20 | BR-F-907 | Авто-списание запчастей со склада при сохранении акта | Must | UC-903, UC-904 | `models/spare_part.py`, `services/parts_service.py` | T-9-008 | ⬜ |
| 21 | BR-F-908 | Клиент подтверждает выполнение работ; без подтверждения перевод в «Выполнена» блокируется | Must | UC-903, UC-904 | `models/work_act.py` (`client_confirmed*` поля), `services/ticket_service.py` | T-9-009 | ⬜ |
| 22 | BR-F-909 | Авто-создание заявок на ТО за 7 дней до плановой даты | Should | UC-908 | `services/maintenance_service.py`, Celery task | T-9-010 | ⬜ |
| 23 | BR-F-910 | Email-уведомления клиенту при смене статуса (Назначена, В работе, Выполнена, Закрыта) | Should | UC-903, UC-906 | `services/notification_service.py` | T-9-011 | ⬜ |
| 24 | BR-F-911 | Два типа комментариев: `internal` (только сотрудники) и `external` (видны клиенту) | Must | UC-906 | `models/comment.py`, `endpoints/requests.py` | T-9-012 | ⬜ |
| 25 | BR-F-912 | Клиент видит `external` комментарии + свои; уведомление сотрудников при комментарии клиента | Must | UC-906 | `models/comment.py`, `services/notification_service.py` | T-9-013 | ⬜ |
| 26 | BR-F-913 | Шаблоны работ по моделям оборудования | Should | UC-901, UC-911 | `models/work_template.py`, `endpoints/requests.py` | T-9-014 | ⬜ |
| 27 | BR-F-914 | Уведомление инженера о назначении заявки (push + email) | Must | UC-902 | `services/notification_service.py` | T-9-015 | ⬜ |
| 28 | BR-F-915 | Прикрепление файлов к заявке (PDF, JPEG, PNG, DOCX, XLSX, ZIP; ≤ 20 МБ) | Must | UC-907 | `models/attachment.py`, `endpoints/requests.py` | T-9-016 | ⬜ |
| 29 | BR-F-916 | Тип инициатора (`client`/`engineer`/`system`) и канал обращения | — | UC-901 | `models/ticket.py` (`initiator_type`, `channel` поля) | T-9-017 | ⬜ |
| 30 | BR-F-917 | Авто-заполнение данных инициатора из сессии клиента | — | UC-901 | `services/ticket_service.py`, `api/deps.py` | T-9-018 | ⬜ |
| 31 | BR-R-004 | Закрытие заявки без акта выполненных работ технически невозможно | — | UC-903, UC-904 | `services/ticket_service.py` (guard) | T-9-019 | ⬜ |
| 32 | BR-R-005 | Списание запчастей только с привязкой к заявке; без заявки запрещено | — | UC-904 | `services/parts_service.py` | T-9-020 | ⬜ |
| 33 | BR-R-006 | Гарантийный ремонт не тарифицируется; данные идут в рекламацию вендору | — | UC-901, UC-904 | `models/ticket.py` (`is_warranty`), `services/ticket_service.py` | T-9-021 | ⬜ |
| 34 | BR-R-008 | Серийные номера оборудования глобально уникальны | — | UC-901, UC-1001 | `models/equipment.py` (UNIQUE constraint) | T-9-022 | ⬜ |
| 35 | BR-R-009 | Soft delete комментариев, вложений, шаблонов | — | UC-906, UC-907, UC-911 | `models/comment.py`, `models/attachment.py` | T-9-023 | ⬜ |
| 36 | BR-R-010 | Аудит-лог смен статусов с timestamp, user, old/new | — | UC-902, UC-903, UC-905 | `models/audit_log.py`, `services/audit.py` | T-9-024 | ⬜ |

---

## Модуль 10 — Учёт оборудования

| # | Требование | Описание | Приоритет | UC | Компонент | Тест | Статус |
|---|-----------|----------|-----------|-----|-----------|------|--------|
| 37 | BR-F-1000 | Паспорт оборудования: модель, серийный номер, даты гарантии, фото | Must | UC-1001 | `models/equipment.py`, `endpoints/equipment.py` | T-10-001 | ⬜ |
| 38 | BR-F-1001 | История ремонтов: дата, тип работ, инженер, запчасти | Must | UC-1002 | `models/repair_history.py`, `endpoints/equipment.py` | T-10-002 | ⬜ |
| 39 | BR-F-1002 | Авто-расчёт статуса гарантии: На гарантии / Истекает / Истекла | Must | UC-1001 | `services/equipment_service.py`, `models/equipment.py` | T-10-003 | ⬜ |
| 40 | BR-F-1003 | Конфигурация оборудования: модули, прошивка, компоненты | Should | UC-1001 | `models/equipment.py` (JSON-поле `configuration`) | T-10-004 | ⬜ |
| 41 | BR-F-1004 | Прикрепление документов к оборудованию: акты, гарантийные талоны, договоры | Must | UC-1004 | `models/equipment_document.py`, `endpoints/equipment.py` | T-10-005 | ⬜ |
| 42 | BR-F-1005 | Список оборудования в карточке клиента с колонками статуса | Must | UC-1005 | `endpoints/equipment.py`, `endpoints/clients.py` | T-10-006 | ⬜ |
| 43 | BR-F-1006 | Поиск оборудования по серийному номеру, модели, клиенту, статусу гарантии | Must | UC-1005 | `endpoints/equipment.py` (query params) | T-10-007 | ⬜ |
| 44 | BR-F-1007 | Статусы оборудования: Активно / На ремонте / Списано / Передано; авто-переключение при смене статуса заявки | Must | UC-1003 | `models/equipment.py`, `services/ticket_service.py` | T-10-008 | ⬜ |
| 45 | BR-F-1008 | Отчёт по парку оборудования: по моделям, клиентам, возрасту, топ-10 проблемных | Should | UC-1006 | `services/reports_service.py`, `endpoints/equipment.py` | T-10-009 | ⬜ |
| 46 | BR-F-1009 | Уведомления о приближающемся ТО и истечении гарантии | Should | UC-908 | `services/maintenance_service.py`, `services/notification_service.py` | T-10-010 | ⬜ |
| 47 | BR-F-1010 | Возврат оборудования: гарантийная замена или выкуп | Should | UC-1003, UC-1007 | `models/equipment.py`, `services/equipment_service.py` | T-10-011 | ⬜ |
| 48 | BR-F-1111 | Данные акта передаются в структуру рекламации вендору (Модуль 11) | — | UC-1007 | `models/vendor_claim.py`, `services/vendor_service.py` | T-10-012 | ⬜ |
| 49 | BR-R-008 | Серийный номер глобально уникален | — | UC-1001 | `models/equipment.py` (UNIQUE constraint) | T-10-013 | ⬜ |
| 50 | BR-R-009 | Soft delete для оборудования и документов | — | UC-1001, UC-1003, UC-1007 | `models/equipment.py`, `models/equipment_document.py` | T-10-014 | ⬜ |
| 51 | BR-R-010 | Аудит-лог изменений в карточке оборудования | — | UC-1001 | `models/audit_log.py`, `services/audit.py` | T-10-015 | ⬜ |

---

## Модуль 14 — Уведомления

| # | Требование | Описание | Приоритет | UC | Компонент | Тест | Статус |
|---|-----------|----------|-----------|-----|-----------|------|--------|
| 52 | BR-F-1400 | Три канала: Email, Push, In-app | — | UC-1401, UC-1402 | `services/notification_service.py` | T-14-001 | ⬜ |
| 53 | BR-F-1401 | Настройки уведомлений пользователя по типу события и каналу | Must | UC-1401 | `models/notification_settings.py`, `endpoints/users.py` | T-14-002 | ⬜ |
| 54 | BR-F-1402 | Push-доставка в течение 1 минуты после события | — | UC-1402 | `services/notification_service.py` (async/Celery) | T-14-003 | ⬜ |
| 55 | BR-F-1403 | История уведомлений in-app с фильтрами | Should | UC-1402 | `models/notification.py`, `endpoints/notifications.py` | T-14-004 | ⬜ |
| 56 | BR-F-1404 | Конфигурация SMTP для email-доставки | Must | UC-1403 | `core/config.py` (SMTP settings), `services/notification_service.py` | T-14-005 | ⬜ |

---

## Сводная статистика покрытия

| Модуль | Требований | UC | Тестов | Must | Should | Could | Реализовано |
|--------|-----------|-----|--------|------|--------|-------|-------------|
| Модуль 3 | 10 | UC-301 | 10 | 10 | 0 | 0 | ✅ 10/10 |
| Модуль 8 | 12 | UC-801–806 | 12 | 9 | 0 | 1 | ⬜ 0/12 |
| Модуль 9 | 24 | UC-901–911 | 24 | 17 | 4 | 0 | 🟡 частично |
| Модуль 10 | 15 | UC-1001–1007 | 15 | 8 | 5 | 0 | 🟡 частично |
| Модуль 14 | 5 | UC-1401–1403 | 5 | 2 | 1 | 0 | 🟡 частично |
| **Итого** | **66** | **28 UC** | **66** | **46** | **10** | **1** | — |

---

## Индекс компонентов

| Компонент | Требования |
|-----------|-----------|
| `models/user.py` | BR-F-800, BR-F-801 |
| `models/competency.py` | BR-F-802, BR-F-804 |
| `models/absence.py` | BR-F-808, BR-F-810 |
| `models/audit_log.py` | BR-F-807, BR-R-010, BR-NF-014 |
| `models/ticket.py` | BR-F-900, BR-F-901, BR-F-903, BR-F-916, BR-F-917 |
| `models/work_act.py` | BR-F-905, BR-F-908 |
| `models/comment.py` | BR-F-911, BR-F-912, BR-R-009 |
| `models/attachment.py` | BR-F-915, BR-R-009 |
| `models/spare_part.py` | BR-F-907, BR-R-005 |
| `models/repair_history.py` | BR-F-906, BR-F-1001 |
| `models/equipment.py` | BR-F-1000, BR-F-1002, BR-F-1003, BR-F-1007, BR-R-008 |
| `services/ticket_service.py` | BR-F-901, BR-F-902, BR-F-906, BR-F-907, BR-F-908, BR-R-004 |
| `services/sla_service.py` | BR-F-903, BR-F-904 |
| `services/engineer_load.py` | BR-F-803, BR-F-804 |
| `services/notification_service.py` | BR-F-910, BR-F-912, BR-F-914, BR-F-1400, BR-F-1402 |
| `services/parts_service.py` | BR-F-907, BR-R-005 |
| `services/maintenance_service.py` | BR-F-909, BR-F-1009 |
| `services/equipment_service.py` | BR-F-1002, BR-F-1010 |
| `services/audit.py` | BR-R-010, BR-NF-014 |
| `services/reports_service.py` | BR-F-1008 |
| `endpoints/users.py` | BR-F-800, BR-F-801, BR-F-806 |
| `endpoints/requests.py` | BR-F-900, BR-F-905, BR-F-911, BR-F-913, BR-F-915 |
| `endpoints/equipment.py` | BR-F-1000, BR-F-1004, BR-F-1005, BR-F-1006, BR-F-1008 |
| `endpoints/audit.py` | BR-F-807, BR-NF-014 |
| `core/security.py` | BR-F-801 |
| `api/deps.py` | BR-F-801, BR-F-917 |
