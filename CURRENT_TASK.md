# CURRENT TASK

**Последнее обновление:** 2026-04-27

## Последняя команда пользователя

> продолжай (реализация Модуля 5 «Склад запчастей», Features 1–4)

## Статус

DONE (pending review) — Модуль 5 «Склад запчастей» реализован полностью

## Что реализовано

| Фича | Описание | Статус |
|---|---|---|
| 1 | Приходный ордер (StockReceipt) | ✅ Backend + тесты + Frontend |
| 2 | Мультисклад: Warehouse + WarehouseStock, фильтр | ✅ Backend + тесты + Frontend |
| 3 | Передача на склад банка (PartsTransfer) | ✅ Backend + тесты + Frontend |
| 4 | Акт выполненных работ v1.4: warehouse_id, BR-P-010 | ✅ Backend (склад в позициях акта, списание, цена 0 в счёте) |

## Артефакты

| Артефакт | Результат |
|---|---|
| `backend/alembic/versions/013_module5_warehouse.py` | Миграция: 6 новых таблиц + warehouse_id в work_act_items |
| `backend/app/models/__init__.py` | 6 новых ORM-моделей + поле warehouse в WorkActItem |
| `backend/app/schemas/__init__.py` | Схемы Warehouse, WarehouseStock, StockReceipt, PartsTransfer + warehouse_id в WorkActItem |
| `backend/app/api/endpoints/warehouses.py` | CRUD складов + GET /warehouses/stock/list |
| `backend/app/api/endpoints/stock_receipts.py` | Полный жизненный цикл приходного ордера |
| `backend/app/api/endpoints/parts_transfers.py` | Полный жизненный цикл передачи запчастей |
| `backend/app/api/endpoints/tickets.py` | Feature 4: `_deduct_act_stock`, `_restore_act_stock`, BR-P-010 в `_sync_invoice_from_act` |
| `backend/app/api/endpoints/invoices.py` | Feature 4: BR-P-010 в create_invoice_from_act |
| `backend/app/api/router.py` | Зарегистрированы 3 новых роутера |
| `backend/tests/test_warehouse.py` | 25 тестов (Warehouses, Stock, Receipts, Transfers) |
| `frontend/src/api/types.ts` | Типы: Warehouse, WarehouseStock, StockReceipt, PartsTransfer и их производные |
| `frontend/src/api/endpoints.ts` | API-функции для складов, приходов, передач |
| `frontend/src/pages/PartsPage.tsx` | 4 вкладки: Запчасти / Остатки / Приходы / Передачи |

## Тесты

499 passed, 0 failed (включая 25 новых тестов Модуля 5)

## Ветка

`feature/module5-warehouse` — ожидает проверки на стенде → merge в main → деплой

## Предыдущая задача (UC-901 v1.4 — серийный номер)

Реализована ранее. Ожидает коммита и деплоя вместе с Модулем 5.

## Следующие шаги

1. Проверить на локальном стенде: /parts → 4 вкладки
2. Создать приходный ордер → провести → проверить остатки
3. Создать передачу → провести → проверить остатки по складам
4. Дать ОК → коммит + merge + деплой
