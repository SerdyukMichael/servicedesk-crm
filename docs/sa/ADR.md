# ADR: Architecture Decision Records — ServiceDesk CRM

**Версия:** 1.0 | **Дата:** 27.03.2026 | **Автор:** Solution Architect

> Документ фиксирует ключевые архитектурные решения с обоснованием.
> Каждое решение содержит: контекст, варианты, выбор, последствия, условие пересмотра.

---

## ADR-001: Хранение файлов в MySQL BLOB

**Статус:** Принято

### Контекст
Система работает с файлами: фото в актах (JPEG/PNG, ≤ 10 МБ), документы к оборудованию (PDF/DOCX/XLSX/ZIP, ≤ 20 МБ), вложения заявок (все типы, ≤ 20 МБ).

### Рассматривались варианты
| Вариант | Плюсы | Минусы |
| --- | --- | --- |
| MySQL BLOB | Нет новых сервисов, транзакционность, простота backup | Рост размера БД, нагрузка на MySQL при выдаче файлов, нужна настройка `max_allowed_packet` |
| MinIO (S3-совместимый) | Масштабируемо, не нагружает СУБД | Новый контейнер, новая зависимость |
| Облачный S3 | Готов к масштабированию | Внешняя зависимость, стоимость |

### Решение
**MySQL BLOB** — хранить файлы в таблицах `file_data LONGBLOB`.

### Обязательные настройки MySQL
```ini
# my.cnf / mysql конфиг
[mysqld]
max_allowed_packet  = 25M
innodb_buffer_pool_size = 256M
```
В `docker-compose.yml` MySQL запускается с `--max-allowed-packet=26214400`.

### Реализация
- Таблицы `equipment_documents` и `ticket_attachments` содержат поле `file_data LONGBLOB NN`
- Поле `file_url` из ER удалить — заменено на `GET /api/v1/files/{id}` (стримит BLOB)
- `FileService.get(file_id)` → `StreamingResponse(content=row.file_data, media_type=row.mime_type)`
- Лимиты валидируются в Pydantic перед сохранением (≤ 20 МБ)

### Условие пересмотра
При объёме файлов > 10 ГБ или при необходимости CDN-доставки — мигрировать на MinIO.

---

## ADR-002: Фоновые задачи — Celery + Redis

**Статус:** Принято

### Контекст
Требуются периодические и отложенные задачи:
- Проверка нарушений SLA (каждые 5 минут)
- Авто-создание заявок ТО за 7 дней (ежедневно в 08:00)
- Пересчёт `warranty_status` (ежедневно в 03:00)
- Отправка email-уведомлений (асинхронно, без блокировки API)
- Отправка Telegram-сообщений (асинхронно)

### Рассматривались варианты
| Вариант | Плюсы | Минусы |
| --- | --- | --- |
| **Celery + Redis** | Надёжный, battle-tested, retry, мониторинг (Flower) | Нужен Redis |
| APScheduler (встроенный) | Без Redis, всё в одном процессе | Ненадёжен при перезапуске, нет retry |
| FastAPI BackgroundTasks | Без зависимостей | Только пост-запросные задачи, нет крон |

### Решение
**Celery 5.x + Redis 7** как брокер и бэкенд результатов.

### Структура
```
backend/app/
├── celery_app.py          # Celery instance, конфиг
├── tasks/
│   ├── sla.py             # check_sla_violations (cron: */5 * * * *)
│   ├── maintenance.py     # create_scheduled_tickets (cron: 0 8 * * *)
│   ├── warranty.py        # recalc_warranty_status (cron: 0 3 * * *)
│   └── notifications.py   # send_email, send_telegram (async задачи)
```

### Конфигурация
```python
# celery_app.py
CELERY_BROKER_URL = "redis://redis:6379/0"
CELERY_RESULT_BACKEND = "redis://redis:6379/1"
CELERY_BEAT_SCHEDULE = {
    "check-sla": {"task": "tasks.sla.check_sla_violations", "schedule": 300},      # каждые 5 мин
    "auto-maintenance": {"task": "tasks.maintenance.create_scheduled_tickets", "schedule": crontab(hour=8, minute=0)},
    "warranty-recalc": {"task": "tasks.warranty.recalc_warranty_status", "schedule": crontab(hour=3, minute=0)},
}
```

### Условие пересмотра
При необходимости горизонтального масштабирования — добавить Celery workers.

---

## ADR-003: Каналы уведомлений — Email + In-app + Telegram

**Статус:** Принято

### Контекст
UC-1401 определяет 3 канала: Email, Push, In-app. Push в MVP = Telegram Bot (Phase 5 — FCM).

### Решение
| Канал | MVP | Технология |
| --- | --- | --- |
| Email | ✅ | `smtplib` + `email.mime` (stdlib Python, без зависимостей) |
| In-app | ✅ | Запись в таблицу `notifications`, polling 30 сек |
| Telegram | ✅ (вместо мобильного Push) | `httpx.post()` к Telegram Bot API |
| Mobile Push (FCM) | ❌ Phase 5 | — |

### Telegram Bot API
- Пользователь указывает `telegram_chat_id` в своём профиле (поле в таблице `users`)
- `NotificationService.send_telegram(chat_id, text)`:
  ```python
  httpx.post(
      f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
      json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
  )
  ```
- `TELEGRAM_BOT_TOKEN` — переменная окружения в `.env`
- Если `telegram_chat_id` не заполнен — канал пропускается без ошибки
- Отправка через Celery-задачу (`tasks.notifications.send_telegram.delay(...)`)

### In-app polling
- `GET /api/v1/notifications/unread` — количество непрочитанных (для бейджа)
- `GET /api/v1/notifications/` — полный список с пагинацией
- `POST /api/v1/notifications/{id}/read` — отметить прочитанным
- Frontend: `useQuery({ queryKey: ['notifications-unread'], refetchInterval: 30_000 })`

### Условие пересмотра
При добавлении мобильного приложения (Phase 5) — добавить FCM. Telegram остаётся как дополнительный канал.

---

## ADR-004: Real-time — Polling вместо WebSocket

**Статус:** Принято

### Контекст
Нужна «живая» лента уведомлений и обновление статуса заявок.

### Решение
**HTTP Polling** каждые 30 секунд.

### Обоснование
- WebSocket требует stateful соединений и усложняет деплой за Nginx
- SSE проще, но всё равно требует долгоживущих соединений и настройки Nginx (`proxy_buffering off`)
- Polling достаточен для сервис-деска: критичность задержки в 30 сек — низкая
- React Query делает polling одной строкой: `refetchInterval: 30_000`

### Условие пересмотра
Если пользователи жалуются на задержку уведомлений или нагрузка от polling > 5% общего трафика — мигрировать на SSE.

---

## ADR-005: Frontend State — React Query без Redux

**Статус:** Принято

### Решение
**TanStack Query v5** (React Query) для серверного стейта. Локальный UI-стейт — `useState` / `useReducer`.

### Обоснование
- 95% стейта в сервис-деске — данные с сервера (списки, карточки)
- Redux добавляет boilerplate без ощутимой выгоды
- React Query: автоматический cache, background refetch, optimistic updates, devtools

### Паттерн
```typescript
// Запросы
const { data, isLoading } = useQuery({ queryKey: ['tickets', filters], queryFn: () => api.getTickets(filters) })

// Мутации с инвалидацией кэша
const mutation = useMutation({ mutationFn: api.updateTicket, onSuccess: () => queryClient.invalidateQueries(['tickets']) })
```

### Условие пересмотра
При необходимости сложного cross-component UI-стейта (drag-and-drop Kanban, мультишаговые визарды) — добавить Zustand.

---

## ADR-006: JWT без refresh-токена в MVP

**Статус:** Принято

### Контекст
FastAPI + PyJWT. ACCESS_TOKEN_EXPIRE_MINUTES = 480 (8 часов).

### Решение
Только access-токен. Refresh-токен — не в MVP.

### Обоснование
- Рабочая смена = 8 часов. По истечении — перелогин.
- Упрощает реализацию: нет таблицы refresh_tokens, нет эндпоинта `/token/refresh`
- Риск: при компрометации токена отзыв невозможен (нет blacklist). Допустимо для внутренней системы.

### Реализация
```python
# core/security.py
def create_access_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({**data, "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

### Условие пересмотра
При требовании security audit или добавлении публичного API — реализовать refresh-токены с хранением в `user_tokens` таблице.

---

## ADR-007: Soft Delete везде

**Статус:** Принято (BR-R-009)

### Решение
Все сущности используют `is_deleted BOOLEAN NOT NULL DEFAULT FALSE`. Физический DELETE запрещён.

### Реализация
```python
# Базовый класс для всех моделей
class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

# Базовый запрос всегда добавляет фильтр
def get_active(session, model):
    return session.query(model).filter(model.is_deleted == False)
```

### Исключение
`audit_log` — append-only, не имеет `is_deleted`. Запись в этой таблице не удаляется никогда.

---

## ADR-008: Стандарт HTTP-ошибок

**Статус:** Принято

### Формат ответа при ошибке
```json
{
  "error": "TICKET_NOT_FOUND",
  "message": "Заявка #SD-2026-000042 не найдена",
  "details": {}
}
```

### Таблица кодов
| Код | Когда использовать |
| --- | --- |
| 400 | Бизнес-правило нарушено (попытка закрыть без акта, дублирование SN) |
| 401 | Токен отсутствует или истёк |
| 403 | Недостаточно прав (роль не позволяет действие) |
| 404 | Запись не найдена или soft-deleted |
| 409 | Конфликт уникальности (дублирование email, serial_number) |
| 422 | Ошибка валидации Pydantic (автоматически FastAPI) |
| 500 | Необработанное исключение (логируется в stderr) |

### Реализация
```python
# core/exceptions.py
class AppException(HTTPException):
    def __init__(self, status_code: int, error_code: str, message: str):
        super().__init__(status_code=status_code, detail={"error": error_code, "message": message})

class TicketNotFoundError(AppException):
    def __init__(self, ticket_id: int):
        super().__init__(404, "TICKET_NOT_FOUND", f"Заявка #{ticket_id} не найдена")
```
