# CURRENT TASK

**Последнее обновление:** 2026-04-17

## Последняя команда пользователя

> НДС "в т.ч." 22%, исправить на тесте и проде

## Статус

DONE — НДС исправлен на тесте и проде, подтверждено пользователем.

## Что сделано (2026-04-17)

### Фикс расчёта НДС "в т.ч." (ставка 22%)

- `backend/app/api/endpoints/invoices.py` — `_recalculate()`: НДС считается из суммы (не сверху), формула `vat = total * 22/122`
- `backend/app/api/endpoints/tickets.py` — `_sync_invoice_from_act()`: та же формула
- `backend/app/api/endpoints/invoices.py` — hardcode `20.00` → `22.00` в эндпоинте создания счёта из акта
- `backend/app/models/__init__.py` — default vat_rate 20 → 22
- `backend/app/schemas/__init__.py` — default vat_rate 20 → 22
- `frontend/src/pages/InvoiceDetailPage.tsx` — убрана строка "Сумма без НДС", НДС показывается как "в т.ч." под итогом
- Миграции БД для прода:
  - `b31f1f38108d` — пересчёт от invoice_items
  - `d20b1718df8a` — ставка 22%
  - `89b7f086cd94` — принудительно 22% для всех счетов (финальный рабочий)

## Что сделано (2026-04-16, финальный фикс)

### Фикс синхронизации неоплаченного счёта при редактировании акта (BR-F-127)

- `backend/app/api/endpoints/tickets.py` — убрано условие `and paid_invoice is None` из строки 781: неоплаченный счёт теперь синхронизируется **всегда** при изменении позиций акта, независимо от наличия оплаченного счёта
- Пересборка backend-контейнера: `docker compose up -d --build backend`
- `pytest tests/ -q` → **397/397 passed**

## Что сделано (2026-04-16, дополнение)

### Фикс диалога INVOICE_PAID_MISMATCH

- `frontend/src/pages/TicketDetailPage.tsx` — переход с `mutate(data, { onError })` на `mutateAsync` + try/catch (per-mutation callbacks не вызываются в TanStack Query v5.95.2)
- `frontend/src/pages/TicketDetailPage.tsx` — то же для `createWorkAct`
- `frontend/nginx.conf` — добавлен `Cache-Control: no-cache, no-store` для `location /` (SPA index.html не кешируется браузером)
- Playwright-тест: диалог «Внимание: оплаченный счёт» подтверждён работающим

### Полный прогон тестов после финальных правок

- `docker compose exec backend pytest tests/ -q` → **397/397 passed**

## Что сделано (2026-04-16)

### BR-F-126 / BR-F-127 — блокировка редактирования акта при наличии счёта

- `backend/app/api/endpoints/tickets.py` — эндпоинт `PUT /tickets/{id}/work-act`:
  - **Фикс 1**: передавать `new_act_items` вместо `act.items` в `_sync_invoice_from_act` (ORM объект устаревает после bulk delete)
  - **Фикс 2 (по результатам ручного теста)**: убрана внешняя проверка `if act_total != inv_subtotal` — неоплаченный счёт теперь всегда синхронизируется при изменении позиций акта (BR-F-127)
- `backend/app/api/endpoints/invoices.py` — добавлен `"engineer"` в `_READ_ROLES` (чтобы фронтенд мог проверить наличие счёта)
- `backend/app/schemas/__init__.py` — добавлен `force_save: bool = False` в `WorkActUpdate`
- `backend/tests/test_work_act_invoice_lock.py` — 8 новых тестов (все pass)
- `backend/tests/test_invoices.py` — `test_engineer_can_list` (было `cannot`, ожидало 403)
- `frontend/src/pages/TicketDetailPage.tsx` — кнопка «Редактировать акт» скрыта у не-admin если счёт существует; диалог INVOICE_PAID_MISMATCH при 409
- `frontend/src/api/endpoints.ts` — `force_save?: boolean` в `updateWorkAct`
- Документация: `docs/DocSpec_WorkAct.md`, `docs/RBAC_Matrix.md`, `docs/RTM.md`, `docs/CHANGELOG.md`

### Справочник услуг на тестовом стенде

- Скопированы 29 услуг с прода на тестовый стенд

### Полный прогон тестов

- `docker compose exec backend pytest tests/ -v` → **396/396 passed**

## Ожидает

Явного ОК пользователя на коммит и пуш ветки `feat/product-catalog-mvp`.

## Что было реализовано ранее

### Product Catalog MVP (2026-04-12)

- Миграция `010_product_catalog.py` — таблица product_catalog
- Модель/схемы/эндпоинт `/api/v1/product-catalog`
- Frontend: ProductCatalogPage, меню «Товары»

### v0.9.0 (Work Act / Invoice features)

- BR-F-115..BR-F-120: подписание акта, статусы, ссылка на счёт, статус оплаты
