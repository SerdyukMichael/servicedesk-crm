# CHANGELOG

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
