# Frontend Architecture — ServiceDesk CRM

**Версия:** 1.0 | **Дата:** 27.03.2026 | **Автор:** Solution Architect

> Документ описывает архитектуру React SPA: структура каталогов, маршрутизация, управление состоянием,
> HTTP-клиент, аутентификация, паттерны работы с данными.
> Стек: React 18 + TypeScript + Vite + React Router v6 + TanStack Query v5 + Axios + React Hook Form + Zod.

---

## 1. Структура каталогов

```
frontend/
├── public/
├── src/
│   ├── main.tsx                  # точка входа, QueryClient, BrowserRouter
│   ├── App.tsx                   # маршруты верхнего уровня
│   ├── api/
│   │   ├── client.ts             # axios instance + JWT interceptor
│   │   └── endpoints/
│   │       ├── auth.ts
│   │       ├── users.ts
│   │       ├── clients.ts
│   │       ├── equipment.ts
│   │       ├── tickets.ts
│   │       ├── workTemplates.ts
│   │       ├── parts.ts
│   │       ├── notifications.ts
│   │       ├── reports.ts
│   │       └── files.ts
│   ├── auth/
│   │   ├── AuthContext.tsx        # контекст текущего пользователя
│   │   ├── useAuth.ts             # хук доступа к контексту
│   │   ├── ProtectedRoute.tsx     # guard: redirect на /login если нет токена
│   │   └── RoleGuard.tsx          # guard: 403-страница если роль не подходит
│   ├── hooks/
│   │   ├── useTickets.ts          # React Query хуки для заявок
│   │   ├── useEquipment.ts
│   │   ├── useNotifications.ts    # включает polling 30s
│   │   ├── useClients.ts
│   │   └── useUsers.ts
│   ├── pages/
│   │   ├── Login/
│   │   │   └── LoginPage.tsx
│   │   ├── Dashboard/
│   │   │   └── DashboardPage.tsx
│   │   ├── Tickets/
│   │   │   ├── TicketListPage.tsx
│   │   │   ├── TicketDetailPage.tsx
│   │   │   └── TicketCreatePage.tsx
│   │   ├── Equipment/
│   │   │   ├── EquipmentListPage.tsx
│   │   │   └── EquipmentDetailPage.tsx
│   │   ├── Clients/
│   │   │   ├── ClientListPage.tsx
│   │   │   └── ClientDetailPage.tsx
│   │   ├── Parts/
│   │   │   └── PartsPage.tsx
│   │   ├── PriceList/
│   │   │   ├── PriceListPage.tsx        # вкладки «Услуги» / «Матценности» (UC-101, UC-102)
│   │   │   ├── ServiceCatalogTab.tsx    # список услуг + управление ценами + история цен
│   │   │   └── MaterialCatalogTab.tsx   # список spare_parts + установка/изменение цен + история цен (BR-F-121, BR-F-122)
│   │   ├── WorkTemplates/
│   │   │   └── WorkTemplatesPage.tsx
│   │   ├── Reports/
│   │   │   └── ReportsPage.tsx
│   │   ├── Notifications/
│   │   │   └── NotificationsPage.tsx
│   │   ├── Users/
│   │   │   └── UsersPage.tsx
│   │   └── NotFound/
│   │       └── NotFoundPage.tsx
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppLayout.tsx      # sidebar + topbar + outlet
│   │   │   ├── Sidebar.tsx
│   │   │   └── TopBar.tsx         # NotificationBadge + UserMenu
│   │   ├── ui/                    # переиспользуемые примитивы
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Select.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Table.tsx
│   │   │   ├── Pagination.tsx
│   │   │   ├── Badge.tsx          # статус заявки / warranty_status
│   │   │   ├── FileUpload.tsx     # drag-drop + size validation
│   │   │   └── EmptyState.tsx
│   │   ├── tickets/
│   │   │   ├── TicketCard.tsx
│   │   │   ├── TicketFilters.tsx
│   │   │   ├── TicketStatusBadge.tsx
│   │   │   └── WorkTemplateSelector.tsx
│   │   ├── notifications/
│   │   │   ├── NotificationBadge.tsx  # бейдж с числом непрочитанных
│   │   │   └── NotificationList.tsx
│   │   └── forms/
│   │       ├── TicketForm.tsx
│   │       ├── EquipmentForm.tsx
│   │       └── ClientForm.tsx
│   ├── types/
│   │   ├── api.ts                 # типы ответов API (зеркало OpenAPI schemas)
│   │   └── auth.ts
│   ├── utils/
│   │   ├── formatters.ts          # даты, статусы, числа
│   │   ├── validators.ts          # Zod схемы для форм
│   │   └── constants.ts           # TICKET_STATUS_LABELS, PRIORITY_COLORS
│   └── vite-env.d.ts
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── Dockerfile
```

---

## 2. Точка входа (main.tsx)

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './auth/AuthContext'
import App from './App'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,      // данные свежие 30 секунд
      refetchOnWindowFocus: true,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </QueryClientProvider>
    </BrowserRouter>
  </React.StrictMode>
)
```

---

## 3. Маршрутизация (App.tsx)

```tsx
import { Routes, Route, Navigate } from 'react-router-dom'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { AppLayout } from './components/layout/AppLayout'
import LoginPage from './pages/Login/LoginPage'
import DashboardPage from './pages/Dashboard/DashboardPage'
import TicketListPage from './pages/Tickets/TicketListPage'
import TicketDetailPage from './pages/Tickets/TicketDetailPage'
import TicketCreatePage from './pages/Tickets/TicketCreatePage'
import EquipmentListPage from './pages/Equipment/EquipmentListPage'
import EquipmentDetailPage from './pages/Equipment/EquipmentDetailPage'
import ClientListPage from './pages/Clients/ClientListPage'
import ClientDetailPage from './pages/Clients/ClientDetailPage'
import PartsPage from './pages/Parts/PartsPage'
import PriceListPage from './pages/PriceList/PriceListPage'
import WorkTemplatesPage from './pages/WorkTemplates/WorkTemplatesPage'
import ReportsPage from './pages/Reports/ReportsPage'
import NotificationsPage from './pages/Notifications/NotificationsPage'
import UsersPage from './pages/Users/UsersPage'
import NotFoundPage from './pages/NotFound/NotFoundPage'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />

          {/* Module 9 — Заявки */}
          <Route path="tickets" element={<TicketListPage />} />
          <Route path="tickets/new" element={<TicketCreatePage />} />
          <Route path="tickets/:id" element={<TicketDetailPage />} />

          {/* Module 10 — Оборудование */}
          <Route path="equipment" element={<EquipmentListPage />} />
          <Route path="equipment/:id" element={<EquipmentDetailPage />} />

          {/* CRM */}
          <Route path="clients" element={<ClientListPage />} />
          <Route path="clients/:id" element={<ClientDetailPage />} />

          {/* Склад */}
          <Route path="parts" element={<PartsPage />} />

          {/* Прайс-листы (UC-101, UC-102) */}
          <Route path="price-list" element={<PriceListPage />} />

          {/* Шаблоны работ */}
          <Route path="work-templates" element={<WorkTemplatesPage />} />

          {/* Отчёты */}
          <Route path="reports" element={<ReportsPage />} />

          {/* Module 14 — Уведомления */}
          <Route path="notifications" element={<NotificationsPage />} />

          {/* Module 8 — Пользователи (admin only) */}
          <Route path="users" element={<UsersPage />} />

          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  )
}
```

---

## 4. Аутентификация

### 4.1 AuthContext (auth/AuthContext.tsx)

```tsx
import { createContext, useState, useEffect, ReactNode } from 'react'
import { api } from '../api/client'
import type { User } from '../types/auth'

interface AuthState {
  user: User | null
  token: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  isLoading: boolean
}

export const AuthContext = createContext<AuthState>(null!)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'))
  const [isLoading, setIsLoading] = useState(true)

  // При старте — загрузить текущего пользователя по сохранённому токену
  useEffect(() => {
    if (token) {
      api.get('/auth/me')
        .then(res => setUser(res.data))
        .catch(() => { setToken(null); localStorage.removeItem('token') })
        .finally(() => setIsLoading(false))
    } else {
      setIsLoading(false)
    }
  }, [])

  const login = async (email: string, password: string) => {
    const res = await api.post('/auth/login', { email, password })
    const { access_token } = res.data
    localStorage.setItem('token', access_token)
    setToken(access_token)
    const meRes = await api.get('/auth/me')
    setUser(meRes.data)
  }

  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  )
}
```

### 4.2 ProtectedRoute (auth/ProtectedRoute.tsx)

```tsx
import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from './useAuth'

export function ProtectedRoute() {
  const { user, isLoading } = useAuth()

  if (isLoading) return <div>Загрузка...</div>
  if (!user) return <Navigate to="/login" replace />

  return <Outlet />
}
```

### 4.3 RoleGuard (auth/RoleGuard.tsx)

```tsx
import { ReactNode } from 'react'
import { useAuth } from './useAuth'

interface Props {
  roles: string[]
  children: ReactNode
  fallback?: ReactNode
}

export function RoleGuard({ roles, children, fallback = null }: Props) {
  const { user } = useAuth()
  if (!user || !roles.includes(user.role)) return <>{fallback}</>
  return <>{children}</>
}
```

**Использование:**
```tsx
<RoleGuard roles={['admin', 'svc_mgr']}>
  <Button onClick={handleDelete}>Удалить шаблон</Button>
</RoleGuard>
```

---

## 5. HTTP-клиент (api/client.ts)

```typescript
import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

// Автоматически добавляет Bearer токен
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Обработка 401 — редирект на /login
api.interceptors.response.use(
  res => res,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
```

---

## 6. Слой API-функций (api/endpoints/)

```typescript
// api/endpoints/tickets.ts
import { api } from '../client'
import type { Ticket, TicketCreate, TicketFilters, PaginatedResponse } from '../../types/api'

export const ticketsApi = {
  getList: (filters: TicketFilters, skip = 0, limit = 20) =>
    api.get<PaginatedResponse<Ticket>>('/tickets', { params: { ...filters, skip, limit } }),

  getById: (id: number) =>
    api.get<Ticket>(`/tickets/${id}`),

  create: (data: TicketCreate) =>
    api.post<Ticket>('/tickets', data),

  update: (id: number, data: Partial<TicketCreate>) =>
    api.put<Ticket>(`/tickets/${id}`, data),

  assign: (id: number, engineerId: number) =>
    api.patch<Ticket>(`/tickets/${id}/assign`, { engineer_id: engineerId }),

  updateStatus: (id: number, status: string, comment?: string) =>
    api.patch<Ticket>(`/tickets/${id}/status`, { status, comment }),

  delete: (id: number) =>
    api.delete(`/tickets/${id}`),

  addComment: (ticketId: number, text: string) =>
    api.post(`/tickets/${ticketId}/comments`, { text }),

  getComments: (ticketId: number) =>
    api.get(`/tickets/${ticketId}/comments`),

  uploadAttachment: (ticketId: number, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post(`/tickets/${ticketId}/attachments`, form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  signWorkAct: (ticketId: number) =>
    api.post(`/tickets/${ticketId}/work-act/sign`),
}
```

---

## 7. React Query хуки (hooks/)

### 7.1 Запросы (useQuery)

```typescript
// hooks/useTickets.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ticketsApi } from '../api/endpoints/tickets'
import type { TicketFilters } from '../types/api'

// Ключи запросов — централизованно
export const ticketKeys = {
  all: ['tickets'] as const,
  list: (filters: TicketFilters) => ['tickets', 'list', filters] as const,
  detail: (id: number) => ['tickets', 'detail', id] as const,
  comments: (id: number) => ['tickets', id, 'comments'] as const,
}

export function useTickets(filters: TicketFilters, skip = 0, limit = 20) {
  return useQuery({
    queryKey: ticketKeys.list(filters),
    queryFn: () => ticketsApi.getList(filters, skip, limit).then(r => r.data),
    placeholderData: prev => prev,  // не мигать при смене фильтров
  })
}

export function useTicket(id: number) {
  return useQuery({
    queryKey: ticketKeys.detail(id),
    queryFn: () => ticketsApi.getById(id).then(r => r.data),
    enabled: !!id,
  })
}

export function useTicketComments(ticketId: number) {
  return useQuery({
    queryKey: ticketKeys.comments(ticketId),
    queryFn: () => ticketsApi.getComments(ticketId).then(r => r.data),
  })
}
```

### 7.2 Мутации (useMutation)

```typescript
// hooks/useTickets.ts (продолжение)
export function useCreateTicket() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ticketsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ticketKeys.all })
    },
  })
}

export function useAssignEngineer() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, engineerId }: { id: number; engineerId: number }) =>
      ticketsApi.assign(id, engineerId),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ticketKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: ticketKeys.all })
    },
  })
}

export function useUpdateTicketStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status, comment }: { id: number; status: string; comment?: string }) =>
      ticketsApi.updateStatus(id, status, comment),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ticketKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: ticketKeys.all })
    },
  })
}
```

### 7.3 Уведомления — polling (hooks/useNotifications.ts)

```typescript
// hooks/useNotifications.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { notificationsApi } from '../api/endpoints/notifications'

export const notificationKeys = {
  unread: ['notifications', 'unread'] as const,
  list: ['notifications', 'list'] as const,
  settings: ['notifications', 'settings'] as const,
}

// Polling каждые 30 секунд — реализация ADR-004
export function useUnreadCount() {
  return useQuery({
    queryKey: notificationKeys.unread,
    queryFn: () => notificationsApi.getUnreadCount().then(r => r.data.count),
    refetchInterval: 30_000,         // 30 секунд
    refetchIntervalInBackground: false,  // не опрашивать в фоне если вкладка неактивна
  })
}

export function useNotifications(skip = 0, limit = 20) {
  return useQuery({
    queryKey: [...notificationKeys.list, skip, limit],
    queryFn: () => notificationsApi.getList(skip, limit).then(r => r.data),
  })
}

export function useMarkRead() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: notificationsApi.markRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.unread })
      queryClient.invalidateQueries({ queryKey: notificationKeys.list })
    },
  })
}

export function useMarkAllRead() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.unread })
      queryClient.invalidateQueries({ queryKey: notificationKeys.list })
    },
  })
}

export function useResetNotificationSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: notificationsApi.resetSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.settings })
    },
  })
}
```

---

## 8. Формы — React Hook Form + Zod

```typescript
// utils/validators.ts
import { z } from 'zod'

export const ticketCreateSchema = z.object({
  title: z.string().min(3, 'Минимум 3 символа').max(300),
  description: z.string().optional(),
  priority: z.enum(['critical', 'high', 'medium', 'low']),
  ticket_type: z.enum(['repair', 'maintenance', 'consultation']),
  client_id: z.number({ required_error: 'Выберите клиента' }),
  equipment_id: z.number().optional(),
  work_template_id: z.number().optional(),
})

export type TicketCreateInput = z.infer<typeof ticketCreateSchema>
```

```tsx
// components/forms/TicketForm.tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { ticketCreateSchema, type TicketCreateInput } from '../../utils/validators'
import { useCreateTicket } from '../../hooks/useTickets'
import { useNavigate } from 'react-router-dom'

export function TicketForm() {
  const navigate = useNavigate()
  const { mutate: createTicket, isPending, error } = useCreateTicket()

  const { register, handleSubmit, formState: { errors } } = useForm<TicketCreateInput>({
    resolver: zodResolver(ticketCreateSchema),
    defaultValues: { priority: 'medium', ticket_type: 'repair' },
  })

  const onSubmit = (data: TicketCreateInput) => {
    createTicket(data, {
      onSuccess: ticket => navigate(`/tickets/${ticket.id}`),
    })
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('title')} placeholder="Описание проблемы" />
      {errors.title && <span>{errors.title.message}</span>}

      {/* ... остальные поля ... */}

      {error && (
        <div className="error">
          {(error as any).response?.data?.message ?? 'Ошибка при создании заявки'}
        </div>
      )}

      <button type="submit" disabled={isPending}>
        {isPending ? 'Сохранение...' : 'Создать заявку'}
      </button>
    </form>
  )
}
```

---

## 9. Компонент NotificationBadge

```tsx
// components/notifications/NotificationBadge.tsx
import { useUnreadCount } from '../../hooks/useNotifications'
import { Link } from 'react-router-dom'

export function NotificationBadge() {
  const { data: count = 0 } = useUnreadCount()  // polling каждые 30s

  return (
    <Link to="/notifications" className="notification-badge-wrapper">
      <span className="bell-icon">🔔</span>
      {count > 0 && (
        <span className="badge">{count > 99 ? '99+' : count}</span>
      )}
    </Link>
  )
}
```

---

## 10. Загрузка файлов

```tsx
// components/ui/FileUpload.tsx
import { useRef } from 'react'

const MAX_SIZE_MB = 20

interface Props {
  onFile: (file: File) => void
  accept?: string
}

export function FileUpload({ onFile, accept }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      alert(`Файл превышает ${MAX_SIZE_MB} МБ`)
      return
    }

    onFile(file)
  }

  return (
    <div onClick={() => inputRef.current?.click()}>
      <input ref={inputRef} type="file" accept={accept} onChange={handleChange} hidden />
      <span>Выберите файл (макс. {MAX_SIZE_MB} МБ)</span>
    </div>
  )
}
```

**Использование хука для загрузки вложения:**
```tsx
const uploadAttachment = useMutation({
  mutationFn: (file: File) => ticketsApi.uploadAttachment(ticketId, file),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tickets', ticketId, 'attachments'] }),
})
```

---

## 11. Переменные окружения

```env
# frontend/.env (или .env.local)
VITE_API_URL=/api/v1
```

В docker-compose Nginx проксирует `/api/v1` → `http://backend:8000/api/v1`, поэтому в production достаточно относительного пути.

Для локальной разработки (без Docker):
```env
VITE_API_URL=http://localhost:8000/api/v1
```

---

## 12. Конфигурация Vite (vite.config.ts)

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
})
```

---

## 13. Dockerfile (frontend/Dockerfile)

```dockerfile
# Stage 1: build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: serve via Nginx
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**nginx.conf:**
```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Проксирование API к backend
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 14. Зависимости (package.json — основные)

```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.22.0",
    "@tanstack/react-query": "^5.28.0",
    "axios": "^1.6.0",
    "react-hook-form": "^7.51.0",
    "@hookform/resolvers": "^3.3.0",
    "zod": "^3.22.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.4.0",
    "vite": "^5.1.0"
  }
}
```

---

## 15. Паттерн добавления нового модуля UI

1. **Типы**: добавить в `types/api.ts`
2. **API-функции**: `api/endpoints/newModule.ts`
3. **Хуки**: `hooks/useNewModule.ts` — `useQuery` + `useMutation` + ключи
4. **Страница**: `pages/NewModule/NewModulePage.tsx`
5. **Маршрут**: добавить в `App.tsx`
6. **Пункт меню**: добавить в `components/layout/Sidebar.tsx`
7. **Форма (если нужна)**: `utils/validators.ts` + `components/forms/NewModuleForm.tsx`
