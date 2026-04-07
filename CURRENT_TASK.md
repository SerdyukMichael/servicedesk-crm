# CURRENT TASK

**Последнее обновление:** 2026-04-07

## Последняя команда пользователя

> "делаем реализацию" — реализация прайс-листов и позиций акта

## Что сделано (2026-04-07)

### Backend реализован полностью

#### Новые модели (`backend/app/models/__init__.py`)

- `ServiceCatalog` — справочник услуг и работ
- `WorkActItem` — структурированные позиции акта (тип, услуга/запчасть, цена, итог)
- `InvoiceItem` расширен: добавлены `item_type`, `service_id`, `part_id`
- `WorkAct` расширен: добавлен relationship `items`

#### Новые схемы (`backend/app/schemas/__init__.py`)

- `ServiceCatalogCreate`, `ServiceCatalogUpdate`, `ServiceCatalogResponse`
- `WorkActItemCreate`, `WorkActItemResponse`
- `WorkActCreate/Response` расширены полем `items: List[WorkActItemCreate]`
- `InvoiceItemCreate/Response` расширены полями `item_type`, `service_id`, `part_id`

#### Новый эндпоинт (`backend/app/api/endpoints/service_catalog.py`)

- `GET /api/v1/service-catalog` — список (с фильтром `include_inactive`, `category`)
- `POST /api/v1/service-catalog` — создание (admin/svc_mgr)
- `GET /api/v1/service-catalog/{id}` — деталь
- `PATCH /api/v1/service-catalog/{id}` — обновление
- `DELETE /api/v1/service-catalog/{id}` — удаление с проверкой BR-P-006

#### Обновлены эндпоинты

- `POST /api/v1/tickets/{id}/work-act` — принимает `items[]` и сохраняет `WorkActItem`
- `GET /api/v1/tickets/{id}/work-act` — возвращает `items[]` через `joinedload`
- `POST /api/v1/invoices/from-act/{ticket_id}` — создаёт счёт из акта (BR-F-410)

#### Тесты (все зелёные)

- `tests/test_service_catalog.py` — 13 тестов
- `tests/test_work_act_items.py` — 5 тестов
- `tests/test_invoice_from_act.py` — 6 тестов
- Итого: **355 passed** (1 pre-existing fail — test_upload_svg_xss_rejected, только в Docker)

### Миграция

Миграция 010 нужна при деплое:

```bash
docker compose exec backend alembic revision --autogenerate -m "service_catalog_and_act_items"
docker compose exec backend alembic upgrade head
```

## Следующий шаг

**Frontend** — страницы:
1. `/service-catalog` — справочник услуг (таблица + CRUD)
2. Обновить форму акта выполненных работ — добавить секцию позиций (услуги + запчасти)
3. Обновить форму создания счёта — добавить кнопку "Создать из акта"
