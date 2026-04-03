# CHANGELOG

## [Unreleased] — 2026-04-03

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

## [0.4.0] — 2026-04-02

### Модели оборудования (UC-1007)
- Справочник моделей с CRUD, активация/деактивация
- Страница `/equipment-models`

### Другие улучшения
- Bat-скрипт `scripts/start.bat` для запуска локального стенда
- UC-1008, UC-1009, UC-912 — документация

---

## [0.3.0] — 2026-03-xx

### Паспорт оборудования (UC-1001, UC-1002)
- Страница `/equipment/:id` — карточка с историей ремонтов
- История ремонтов: список работ по единице оборудования

---

## [0.2.0] — ранее

### CRM — клиенты, заявки, уведомления, пользователи
- Клиентская база с контактами
- Заявки на ремонт/ТО
- Система уведомлений
- Управление пользователями
