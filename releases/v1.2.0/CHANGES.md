# v1.2.0 — Страница счёта, блокировка акта, НДС 22%, системная валюта

**Дата выпуска:** 2026-04-19

---

## Frontend

- **Страница детального просмотра счёта** (`/invoices/:id`) — позиции, итог, НДС "в т.ч.", статус оплаты, кнопки смены статуса
- **Блокировка редактирования акта** при наличии счёта (BR-F-126): кнопка «Редактировать акт» скрыта у не-admin, если счёт уже существует
- **Диалог INVOICE_PAID_MISMATCH** при попытке сохранить акт, сумма которого расходится с оплаченным счётом (BR-F-127)
- **НДС отображается "в т.ч."** на странице счёта (строка "Сумма без НДС" убрана)
- **Страница «Настройки»** (`/settings`) — системная валюта: код (ISO 4217) и наименование, доступна только администратору
- **Пункт меню «Настройки»** — виден только роли admin
- **Все денежные значения** заменены с hardcoded `₽` на системную валюту из контекста (`CurrencyContext`)
- **nginx**: добавлен `Cache-Control: no-cache, no-store` для SPA index.html

## Backend

- **`PUT /tickets/{id}/work-act`**: синхронизация неоплаченного счёта при изменении акта (BR-F-127); передача `new_act_items` вместо устаревшего ORM-объекта (BR-F-126 fix)
- **`GET /invoices`**: роль `engineer` добавлена в `_READ_ROLES`
- **`POST /tickets/{id}/invoice-from-act`**: ставка НДС hardcode исправлена с 20% на 22%
- **`_recalculate()`** в invoices: НДС считается "в т.ч." по формуле `total * 22/122`
- **`_sync_invoice_from_act()`** в tickets: та же формула НДС "в т.ч."
- **`GET /settings/currency`** — публичный эндпоинт системной валюты
- **`PUT /settings/currency`** — смена валюты (только admin)
- **Модель `SystemSetting`** — таблица `system_settings` (key-value)
- **Схемы** `CurrencySettingResponse`, `CurrencySettingUpdate` (валидация: код 3 заглавные буквы A-Z)
- Дефолтная ставка НДС в моделях и схемах: 20% → 22%

## Database

- **Миграция 010** (откат через 011): product_catalog — создание и удаление (экспериментальная фича откачена)
- **Миграция 011**: `price_history`, поля `created_by/created_at/updated_at` в `spare_parts`
- **Миграция b31f1f38108d**: пересчёт НДС существующих счетов от `invoice_items`
- **Миграция d20b1718df8a**: принудительная ставка 22% для всех счетов
- **Миграция 89b7f086cd94**: финальный пересчёт — total_amount, vat_amount, subtotal от invoice_items
- **Миграция 012_system_settings**: таблица `system_settings`, seed-данные `currency_code=RUB`, `currency_name=Российский рубль`

## Тесты

- **`test_work_act_invoice_lock.py`** — 8 тестов BR-F-126/127
- **`test_invoices.py`** — `test_engineer_can_list` (инженер имеет доступ к списку счетов)
- **`test_settings.py`** — 9 тестов эндпоинта `/settings/currency`
- Итого: **409/409 passed**
