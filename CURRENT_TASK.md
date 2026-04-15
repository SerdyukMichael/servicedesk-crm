# CURRENT TASK

**Последнее обновление:** 2026-04-15 (деплой v1.0.0 завершён)

## Последняя команда пользователя

> доведи реализацию MVP до описанной в документации. напиши новые тесты. выложи на тестовый стенд, прогои тесты в т.ч. сам через интерфейс. дай посмотреть мне

## Статус

READY FOR REVIEW — реализован Product Catalog MVP, локальный стенд поднят

## Что сделано (2026-04-12)

### Product Catalog MVP (ветка feat/product-catalog-mvp)

- Миграция `010_product_catalog.py` — таблица product_catalog, FK product_id в work_act_items/invoice_items, расширены enum
- Модель ProductCatalog + обновлены WorkActItem (product_id, enum +product) и InvoiceItem
- Схемы ProductCatalogCreate/Update/Response + product_id в WorkActItemCreate/Response, InvoiceItemCreate/Response
- Эндпоинт `/api/v1/product-catalog` — CRUD + BR-P-006 guard
- 16 новых тестов — все PASSED. Полный сьют 380/380 зелёных
- Frontend: ProductCatalogPage.tsx, useProductCatalog.ts, types, endpoints, App.tsx + Layout.tsx
- Боковое меню: «Услуги» 💼 + «Товары» 📦
- Фикс docker-compose.yml: nginx.conf по умолчанию (локальный стенд), nginx.prod.conf через NGINX_CONF env на prod

### Ручная проверка на локальном стенде (http://localhost/)
- ✅ Страница «Прайс-лист товаров» открывается
- ✅ Меню «Товары» отображается в боковой панели
- ✅ Создание товара PROD-001 «Картридж ATM»
- ✅ Деактивация — товар скрывается из списка по умолчанию
- ✅ «Показать неактивные» — товар виден со статусом «Неактивен»
- ✅ Активировать — статус возвращается в «Активен»

## Ожидает

Merge ветки `feat/product-catalog-mvp` в `main` и деплой на боевой сервер (188.120.243.122) — по явному ОК пользователя.

## Что было реализовано ранее (v0.9.0)

- BR-F-115: кнопка «Редактировать акт» скрыта после подписания
- BR-F-116: подписание только client_user
- BR-F-117: статус подписи виден с датой
- BR-F-118: кнопка «Создать счёт» disabled без позиций
- BR-F-119: ссылка на счёт рядом с актом
- BR-F-120: статус оплаты рядом с актом
- Багфикс: имя клиента в списке счетов
