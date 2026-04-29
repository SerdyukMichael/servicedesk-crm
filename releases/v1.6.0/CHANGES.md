# v1.6.0 — Склад запчастей (Модуль 5) + Серийный номер в заявке

## Frontend

- **UC-901 Серийный номер**: поле «Серийный номер» в форме создания заявки с debounce-поиском оборудования (400 мс) и автоподстановкой клиента/оборудования
- **Модуль 5 — Склад**: страница `/parts` получила 4 вкладки: Запчасти / Остатки / Приходы / Передачи
- Таблицы остатков по складам, журнал приходных ордеров, журнал передач

## Backend

- **UC-901**: поле `serial_number` в `TicketCreate`/`TicketUpdate`; эндпоинт `GET /equipment/lookup?serial=...` для поиска оборудования по серийному номеру
- **Warehouses**: CRUD складов (`GET/POST/PUT /warehouses`), остатки по складу (`GET /warehouses/stock/list`)
- **StockReceipt**: приходные ордера — создание, проведение, отмена (`/stock-receipts`)
- **PartsTransfer**: передачи запчастей между складами (`/parts-transfers`)
- **WorkAct (Feature 4)**: при проведении акта выполненных работ запчасти списываются со склада (`warehouse_id` в позициях); BR-P-010 — позиции со склада в счёт идут по цене 0
- Новые роуты зарегистрированы в `router.py`

## Database

- Миграция `013_module5_warehouse`: 6 новых таблиц (`warehouses`, `warehouse_stock`, `stock_receipts`, `stock_receipt_items`, `parts_transfers`, `parts_transfer_items`) + колонка `warehouse_id` в `work_act_items`

## Тесты

- 499 passed (25 новых тестов складского модуля)
