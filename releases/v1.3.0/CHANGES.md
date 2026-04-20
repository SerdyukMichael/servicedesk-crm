# v1.3.0 — Удаление истории ремонтов, UI/UX улучшения

**Дата выпуска:** 2026-04-20

---

## Frontend

- **Удалена вкладка «История ремонтов»** из карточки оборудования (`/equipment/:id`) — история обслуживания доступна через заявки с фильтрацией по оборудованию
- **Кнопка «← Назад»** добавлена на страницы: заявки (`/tickets/:id`), клиента (`/clients/:id`), оборудования (`/equipment/:id`) — по аналогии с формой счёта
- **EquipmentModelsPage** — исправлены CSS-классы формы редактирования (`form-control` → `form-input`, `form-select`, `form-textarea`), добавлены индикаторы обязательных полей

## Backend

- **Удалён эндпоинт** `GET /equipment/{id}/history`
- **Удалена модель** `RepairHistory` (SQLAlchemy ORM)
- **Удалена схема** `RepairHistoryResponse` (Pydantic)
- **Удалён блок BR-F-906** из `PUT /tickets/{id}/status` — авто-создание записей в `repair_history` при завершении заявки
- **Удалён словарь** `_TICKET_TYPE_TO_WORK_TYPE` из `tickets.py`

## Database

- **Миграция `403d0220d2a5`**: `DROP TABLE repair_history`

## Документы BA/SA

- **UC-1002** — упразднён (таблица `repair_history` удалена)
- **ER_DataModel.md** — удалена секция `repair_history`, обновлён граф связей
- **RBAC_Matrix.md** — раздел «История ремонтов / Графики ТО» → «Графики ТО»; убрана строка просмотра истории ремонтов
- **UC-1001.md** — убрана ссылка на `GET /equipment/{id}/history`
- **BRD v1.1** — переформулирован BR-F-906, удалён BR-F-1001, обновлена BG-002
- **RTM** — удалены строки BR-F-906 (repair history) и BR-F-1001
- **AC_MVP_Requirements** — удалены Feature-блоки BR-F-906 и BR-F-1001
- **CHANGELOG** — убрана ссылка на UC-1002
- **AppendixD** — убрана строка «Автозапись в историю ремонтов»
- **ER_Diagram.puml** — удалена entity `repair_history` и 2 связи
- **SA/API_Specification.yaml** — удалён эндпоинт `GET /equipment/{id}/history`
- **SA/DB_Migrations.md** — удалена миграция M013 и `CREATE TABLE repair_history`

## Тесты

- **Удалён файл** `backend/tests/test_repair_history.py` (9 тестов)
- **Удалены 2 теста** из `test_equipment.py` и `test_row_level_detail.py`
- Итого: **388/388 passed**
