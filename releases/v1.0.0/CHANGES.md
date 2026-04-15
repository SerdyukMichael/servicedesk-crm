# v1.0.0 — Единый каталог материальных ценностей + история цен

## Backend

- **Удалена** сущность `product_catalog` (таблица, модель, схемы, эндпоинт `/api/v1/product-catalog`)
- `SparePart` — единый каталог материальных ценностей. Добавлены поля: `unit_price`, `currency`, `created_by`, `created_at`, `updated_at`
- **Новый эндпоинт** `PATCH /api/v1/parts/{id}/price` — установка/изменение цены (роли: admin, svc_mgr). Записывает историю изменений
- **Новый эндпоинт** `GET /api/v1/parts/{id}/price-history` — история цен позиции (недоступен client_user)
- **Фильтр** `GET /api/v1/parts?has_price=true` — только позиции с ценой > 0
- `PriceHistory` — новая модель с полиморфной ссылкой `entity_type` + `entity_id` (покрывает spare_parts и service_catalog)
- Схемы: добавлены `SparePartPriceUpdate`, `PriceHistoryResponse`; удалены `ProductCatalogCreate/Update/Response`
- Тесты: удалены `test_product_catalog.py`; добавлены `test_parts_price.py` (14 тестов). Итого: 378 тестов, все зелёные

## Frontend

- Удалены: `ProductCatalogPage.tsx`, `useProductCatalog.ts`, маршрут `/product-catalog`, пункт меню «Товары»
- `PartsPage` — полностью переработан:
  - Колонка «Цена» с валютой и ссылкой «история»
  - Кнопка «Уст. цену» / «Цена» (только admin, svc_mgr)
  - Модальное окно установки/изменения цены (с валидацией причины ≥ 5 символов)
  - Модальное окно «История цен» с таблицей изменений
- `TicketDetailPage` — выпадающий список запчастей при создании акта отфильтрован по `has_price=true` (BR-F-122)
- `types.ts` — `SparePart`: заменено поле `price: number` на `unit_price: string`, добавлено `currency: string`
- `endpoints.ts` — добавлены `setPartPrice`, `getPartPriceHistory`; удалены API методы product_catalog

## База данных

- Миграция `011_remove_product_catalog`:
  - Удалена таблица `product_catalog`
  - Удалены FK и колонки `product_id` из `work_act_items` и `invoice_items`
  - Откат enum: `work_act_item_type` → `service|part`, `invoice_item_type` → `service|part|manual`
  - `spare_parts`: добавлены `created_by`, `created_at`, `updated_at`
  - Создана таблица `price_history` с индексом `(entity_type, entity_id)`

## Документация

- `ER_DataModel.md` — обновлена схема БД (price_history, spare_parts)
- `RBAC_Matrix.md` — добавлены права на управление ценами
- `RTM.md` — добавлены BR-F-122, BR-P-006
- `docs/sa/` — обновлены API_Specification, Backend_Architecture, Frontend_Architecture
