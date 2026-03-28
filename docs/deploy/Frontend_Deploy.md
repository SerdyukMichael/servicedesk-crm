# Frontend Deployment Guide

ServiceDesk CRM — React 18 + TypeScript SPA, собирается с помощью Vite.

---

## 1. Локальная разработка

### Установка зависимостей

```bash
cd frontend
npm install
```

### Запуск dev-сервера

```bash
npm run dev
```

Dev-сервер запустится на `http://localhost:5173`.

### Прокси для API

В режиме разработки Vite проксирует все запросы `/api/*` на `http://localhost:8000`.
Это настроено в `vite.config.ts`:

```ts
server: {
  proxy: {
    '/api': 'http://localhost:8000'
  }
}
```

Убедитесь, что backend запущен локально (или через Docker) перед запуском frontend.

---

## 2. Production-сборка

### Сборка статических файлов

```bash
cd frontend
npm run build
```

Команда выполняет:
1. `tsc` — проверка TypeScript без ошибок
2. `vite build` — оптимизированная сборка в директорию `dist/`

После успешной сборки в `dist/` будут:
- `index.html` — точка входа SPA
- `assets/` — хешированные JS/CSS/изображения (кешируются браузером на 1 год)

### Предварительный просмотр production-сборки

```bash
npm run preview
```

Запустит статический HTTP-сервер на `http://localhost:4173` для проверки собранного приложения.

---

## 3. Docker-сборка

Сборка производится в два этапа (multi-stage build):

```dockerfile
# Stage 1: Node 20 Alpine — сборка
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: nginx 1.27 Alpine — раздача статики
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### Сборка Docker-образа вручную

```bash
cd frontend
docker build -t servicedesk-frontend:latest .
```

### Запуск через Docker Compose

```bash
# Запуск всего стека
docker-compose up -d --build

# Только frontend
docker-compose up -d --build frontend
```

Frontend будет доступен на `http://localhost/`.

---

## 4. Конфигурация nginx

Файл: `frontend/nginx.conf`

Ключевые блоки:

### React Router (SPA fallback)

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

Все неизвестные пути (например `/tickets/42`) отдают `index.html`, и React Router
обрабатывает маршрут на стороне клиента. Без этого директивы обновление страницы
дало бы 404.

### Проксирование API

```nginx
location /api/ {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_read_timeout 120s;
    proxy_buffering off;
}
```

nginx принимает запросы `/api/*` на порту 80 и проксирует их к FastAPI-бэкенду
в Docker-сети по имени `backend:8000`. Это позволяет избежать CORS, так как
frontend и API живут на одном домене/порту.

### Кеширование статических ассетов

```nginx
location ~* \.(js|css|png|jpg|svg|ico|woff|woff2)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

Vite генерирует файлы с content-hash в имени (например `index-Dz3f1a2b.js`),
что позволяет безопасно кешировать их на год.

### Health check

```nginx
location /nginx-health {
    return 200 "ok";
}
```

Используется для Docker healthcheck контейнера nginx.

---

## 5. Переменные окружения

Frontend — статическое SPA, оно не читает переменные окружения в runtime.
Все настройки задаются на этапе сборки через Vite.

### Vite env-переменные (опционально)

Если потребуется вынести URL API или другие настройки, создайте файл `.env`:

```
VITE_API_BASE_URL=/api/v1
VITE_APP_TITLE=ServiceDesk CRM
```

Доступ в коде:

```ts
const base = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'
```

**Важно**: только переменные с префиксом `VITE_` попадают в bundle.
Переменные без префикса недоступны в браузере.

### В docker-compose.yml

```yaml
services:
  frontend:
    build: ./frontend
    environment:
      - VITE_APP_TITLE=ServiceDesk CRM  # используется только при сборке
```

Для runtime-конфигурации (без пересборки) можно использовать конфигурационный
файл `/usr/share/nginx/html/config.js`, монтируемый как volume, и подключать его
в `index.html` через `<script>`.

---

## 6. Структура src/

```
frontend/src/
├── api/
│   ├── axios.ts         # Axios instance + interceptors (JWT, 401 redirect)
│   ├── endpoints.ts     # Все API-функции (auth, tickets, clients, ...)
│   └── types.ts         # TypeScript интерфейсы для API
├── components/
│   ├── ConfirmDialog.tsx
│   ├── Layout.tsx        # App shell: sidebar + topbar
│   ├── Pagination.tsx
│   ├── PriorityBadge.tsx
│   ├── PrivateRoute.tsx
│   └── StatusBadge.tsx
├── context/
│   └── AuthContext.tsx   # JWT + user state, hasRole()
├── hooks/
│   ├── useClients.ts
│   ├── useEquipment.ts
│   ├── useNotifications.ts
│   ├── useParts.ts
│   ├── useTickets.ts
│   └── useUsers.ts
├── pages/
│   ├── ClientDetailPage.tsx
│   ├── ClientsPage.tsx
│   ├── EquipmentPage.tsx
│   ├── InvoicesPage.tsx
│   ├── LoginPage.tsx
│   ├── NotificationsPage.tsx
│   ├── PartsPage.tsx
│   ├── TicketDetailPage.tsx
│   ├── TicketFormPage.tsx
│   ├── TicketsPage.tsx
│   └── UsersPage.tsx
├── App.tsx               # Маршрутизация
├── index.css             # Глобальные стили (без UI-библиотек)
└── main.tsx              # Точка входа (ReactDOM + QueryClient)
```
