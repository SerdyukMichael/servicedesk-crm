# CURRENT TASK

**Последнее обновление:** 2026-04-20

## Последняя команда пользователя

> выкладываем все в гит и на прод

## Статус

DONE — v1.3.0 закоммичена, тег создан, пуш выполнен. CI/CD задеплоит на прод автоматически.

## Что сделано (2026-04-20)

### v1.3.0 — Удаление repair_history, UI/UX улучшения

**Frontend:**
- Удалена вкладка «История ремонтов» из карточки оборудования
- Добавлена кнопка «← Назад» на страницы: заявки, клиента, оборудования
- EquipmentModelsPage: исправлены CSS-классы формы (form-control → form-input/select/textarea), добавлены маркеры обязательных полей

**Backend:**
- Удалён эндпоинт `GET /equipment/{id}/history`
- Удалена ORM-модель `RepairHistory`, схема `RepairHistoryResponse`
- Удалён BR-F-906 (авто-создание записей repair_history при завершении заявки)
- Удалён словарь `_TICKET_TYPE_TO_WORK_TYPE`

**БД:**
- Миграция `403d0220d2a5`: `DROP TABLE repair_history`

**Тесты:**
- Удалён `test_repair_history.py` (9 тестов)
- Удалены 2 теста из `test_equipment.py` и `test_row_level_detail.py`
- Итого: 388/388 passed

**Документы:**
- BRD, RTM, AC_MVP_Requirements, AppendixD, CHANGELOG, ER_Diagram.puml
- ER_DataModel.md, RBAC_Matrix.md, UC-1001, UC-1002 (упразднён), API_Specification.yaml, DB_Migrations.md

**Git:**
- Коммит: `daa1ecf`
- Тег: `v1.3.0`
- Пуш: выполнен, CI/CD деплоит на https://mikes1.fvds.ru

## Что было реализовано ранее

### НДС "в т.ч." 22% (2026-04-17)

DONE — исправлено на тесте и проде, подтверждено пользователем.

### BR-F-126 / BR-F-127 — блокировка редактирования акта (2026-04-16)

DONE — реализовано и задеплоено.
