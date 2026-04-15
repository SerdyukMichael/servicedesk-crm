# v1.1.0 — Возобновление заявок + Email-уведомления

**Дата:** 2026-04-16
**Ветка:** main
**Тег:** v1.1.0

---

## Backend

### Новые возможности

- **BR-F-125: Возобновление заявки** (`endpoints/tickets.py`)
  - Переходы `closed → in_progress` и `completed → in_progress`
  - RBAC-охрана: admin, svc_mgr, client_user могут возобновлять; engineer — запрещено (403)
  - `closed_at` сбрасывается в `NULL` при возобновлении
  - Запись перехода в историю статусов (from_status, to_status, comment)

- **Email-уведомления** (`core/email.py` — новый файл)
  - SMTP-клиент на smtplib с STARTTLS
  - Graceful no-op если SMTP не настроен (логирует DEBUG)
  - При возобновлении отправляется письмо инициатору заявки, менеджеру (svc_mgr) и назначенному инженеру

### Тесты

- `tests/test_ticket_reopen.py` — 10 новых тестов:
  - admin/svc_mgr/client_user могут возобновить из closed
  - engineer не может возобновить из closed (403)
  - closed_at очищается после возобновления
  - Переход фиксируется в истории
  - admin/svc_mgr могут возобновить из completed
  - engineer не может возобновить из completed (403)
  - cancelled → in_progress запрещено (400)
- Полный прогон: **388/388 PASSED**

### Конфигурация SMTP (`backend/.env`)

```
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USER=<brevo_login>
SMTP_PASSWORD=<brevo_api_key>
```

---

## Frontend

- **`TicketDetailPage.tsx`**: кнопка «→ Возобновить» для заявок со статусом «Закрыта» и «Выполнена»
  - Видна только ролям admin, svc_mgr, client_user
  - Метка перехода: «Возобновить» вместо стандартного «В работе»

---

## Database

Новых миграций нет. Все изменения — на уровне бизнес-логики.

---

## Документация

- `docs/ServiceDesk_CRM_BRD_v1.1.md` — добавлен BR-F-125
- `docs/RTM.md` — добавлена строка R1-9 (BR-F-125, тест ✅)
- `docs/sa/API_Specification.yaml` — обновлено описание `POST /tickets/{id}/status` (полная матрица переходов)
