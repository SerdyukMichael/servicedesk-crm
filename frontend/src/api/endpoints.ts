import api from './axios'
import type {
  User,
  Client,
  ClientContact,
  Equipment,
  EquipmentModel,
  Ticket,
  TicketStatusHistoryEntry,
  TicketComment,
  TicketAttachment,
  WorkAct,
  WorkTemplate,
  SparePart,
  Vendor,
  Invoice,
  Notification,
  NotificationSetting,
  PaginatedResponse,
  LoginResponse,
} from './types'

// ===== Auth =====

export const login = (email: string, password: string): Promise<LoginResponse> =>
  api
    .post<LoginResponse>('/auth/login', { email, password })
    .then(r => r.data)

export const getMe = (): Promise<User> =>
  api.get<User>('/auth/me').then(r => r.data)

// ===== Users =====

export const getUsers = (params?: Record<string, unknown>): Promise<PaginatedResponse<User>> =>
  api.get<PaginatedResponse<User>>('/users', { params }).then(r => r.data)

export const getUser = (id: number): Promise<User> =>
  api.get<User>(`/users/${id}`).then(r => r.data)

export const createUser = (data: Partial<User> & { password: string }): Promise<User> =>
  api.post<User>('/users', data).then(r => r.data)

export const updateUser = (id: number, data: Partial<User>): Promise<User> =>
  api.put<User>(`/users/${id}`, data).then(r => r.data)

export const deleteUser = (id: number): Promise<void> =>
  api.delete(`/users/${id}`).then(() => undefined)

// ===== Clients =====

export const getClients = (params?: Record<string, unknown>): Promise<PaginatedResponse<Client>> =>
  api.get<PaginatedResponse<Client>>('/clients', { params }).then(r => r.data)

export const getClient = (id: number): Promise<Client> =>
  api.get<Client>(`/clients/${id}`).then(r => r.data)

export const createClient = (data: Partial<Client>): Promise<Client> =>
  api.post<Client>('/clients', data).then(r => r.data)

export const updateClient = (id: number, data: Partial<Client>): Promise<Client> =>
  api.put<Client>(`/clients/${id}`, data).then(r => r.data)

export const deleteClient = (id: number): Promise<void> =>
  api.delete(`/clients/${id}`).then(() => undefined)

export const getClientContacts = (clientId: number): Promise<ClientContact[]> =>
  api.get<ClientContact[]>(`/clients/${clientId}/contacts`).then(r => r.data)

export const createClientContact = (
  clientId: number,
  data: Partial<ClientContact>
): Promise<ClientContact> =>
  api.post<ClientContact>(`/clients/${clientId}/contacts`, data).then(r => r.data)

// ===== Equipment =====

export const getEquipment = (params?: Record<string, unknown>): Promise<PaginatedResponse<Equipment>> =>
  api.get<PaginatedResponse<Equipment>>('/equipment', { params }).then(r => r.data)

export const getEquipmentItem = (id: number): Promise<Equipment> =>
  api.get<Equipment>(`/equipment/${id}`).then(r => r.data)

export const createEquipment = (data: Partial<Equipment>): Promise<Equipment> =>
  api.post<Equipment>('/equipment', data).then(r => r.data)

export const updateEquipment = (id: number, data: Partial<Equipment>): Promise<Equipment> =>
  api.put<Equipment>(`/equipment/${id}`, data).then(r => r.data)

export const getEquipmentModels = (): Promise<EquipmentModel[]> =>
  api.get<EquipmentModel[]>('/equipment/models').then(r => r.data)

export const getClientEquipment = (clientId: number): Promise<Equipment[]> =>
  api.get<Equipment[]>(`/clients/${clientId}/equipment`).then(r => r.data)

// ===== Tickets =====

export const getTickets = (params?: Record<string, unknown>): Promise<PaginatedResponse<Ticket>> =>
  api.get<PaginatedResponse<Ticket>>('/tickets', { params }).then(r => r.data)

export const getTicket = (id: number): Promise<Ticket> =>
  api.get<Ticket>(`/tickets/${id}`).then(r => r.data)

export const createTicket = (data: Partial<Ticket>): Promise<Ticket> =>
  api.post<Ticket>('/tickets', data).then(r => r.data)

export const updateTicket = (id: number, data: Partial<Ticket>): Promise<Ticket> =>
  api.put<Ticket>(`/tickets/${id}`, data).then(r => r.data)

export const assignEngineer = (
  ticketId: number,
  engineerId: number
): Promise<Ticket> =>
  api
    .patch<Ticket>(`/tickets/${ticketId}/assign`, { engineer_id: engineerId })
    .then(r => r.data)

export const changeTicketStatus = (
  ticketId: number,
  status: string
): Promise<Ticket> =>
  api
    .patch<Ticket>(`/tickets/${ticketId}/status`, { status })
    .then(r => r.data)

export const getTicketStatusHistory = (ticketId: number): Promise<TicketStatusHistoryEntry[]> =>
  api.get<TicketStatusHistoryEntry[]>(`/tickets/${ticketId}/status-history`).then(r => r.data)

export const getTicketComments = (ticketId: number): Promise<TicketComment[]> =>
  api.get<TicketComment[]>(`/tickets/${ticketId}/comments`).then(r => r.data)

export const addTicketComment = (
  ticketId: number,
  text: string,
  isInternal = false
): Promise<TicketComment> =>
  api
    .post<TicketComment>(`/tickets/${ticketId}/comments`, {
      text,
      is_internal: isInternal,
    })
    .then(r => r.data)

export const getTicketAttachments = (ticketId: number): Promise<TicketAttachment[]> =>
  api.get<TicketAttachment[]>(`/tickets/${ticketId}/attachments`).then(r => r.data)

export const uploadTicketAttachment = (
  ticketId: number,
  file: File
): Promise<TicketAttachment> => {
  const formData = new FormData()
  formData.append('file', file)
  return api
    .post<TicketAttachment>(`/tickets/${ticketId}/attachments`, formData)
    .then(r => r.data)
}

export const getWorkAct = (ticketId: number): Promise<WorkAct> =>
  api.get<WorkAct>(`/tickets/${ticketId}/work-act`).then(r => r.data)

export const createWorkAct = (
  ticketId: number,
  data: Partial<WorkAct>
): Promise<WorkAct> =>
  api.post<WorkAct>(`/tickets/${ticketId}/work-act`, data).then(r => r.data)

export const signWorkAct = (
  ticketId: number,
  role: 'engineer' | 'client'
): Promise<WorkAct> =>
  api
    .post<WorkAct>(`/tickets/${ticketId}/work-act/sign`, { role })
    .then(r => r.data)

export const getClientTickets = (clientId: number): Promise<Ticket[]> =>
  api.get<Ticket[]>(`/clients/${clientId}/tickets`).then(r => r.data)

// ===== Work Templates =====

export const getWorkTemplates = (): Promise<WorkTemplate[]> =>
  api.get<WorkTemplate[]>('/work-templates').then(r => r.data)

export const getWorkTemplate = (id: number): Promise<WorkTemplate> =>
  api.get<WorkTemplate>(`/work-templates/${id}`).then(r => r.data)

// ===== Spare Parts =====

export const getParts = (params?: Record<string, unknown>): Promise<PaginatedResponse<SparePart>> =>
  api.get<PaginatedResponse<SparePart>>('/parts', { params }).then(r => r.data)

export const getPart = (id: number): Promise<SparePart> =>
  api.get<SparePart>(`/parts/${id}`).then(r => r.data)

export const createPart = (data: Partial<SparePart>): Promise<SparePart> =>
  api.post<SparePart>('/parts', data).then(r => r.data)

export const updatePart = (id: number, data: Partial<SparePart>): Promise<SparePart> =>
  api.put<SparePart>(`/parts/${id}`, data).then(r => r.data)

export const adjustPartQuantity = (
  id: number,
  delta: number,
  reason?: string
): Promise<SparePart> =>
  api
    .post<SparePart>(`/parts/${id}/adjust`, { delta, reason })
    .then(r => r.data)

// ===== Vendors =====

export const getVendors = (params?: Record<string, unknown>): Promise<PaginatedResponse<Vendor>> =>
  api.get<PaginatedResponse<Vendor>>('/vendors', { params }).then(r => r.data)

export const getVendor = (id: number): Promise<Vendor> =>
  api.get<Vendor>(`/vendors/${id}`).then(r => r.data)

export const createVendor = (data: Partial<Vendor>): Promise<Vendor> =>
  api.post<Vendor>('/vendors', data).then(r => r.data)

export const updateVendor = (id: number, data: Partial<Vendor>): Promise<Vendor> =>
  api.put<Vendor>(`/vendors/${id}`, data).then(r => r.data)

// ===== Invoices =====

export const getInvoices = (params?: Record<string, unknown>): Promise<PaginatedResponse<Invoice>> =>
  api.get<PaginatedResponse<Invoice>>('/invoices', { params }).then(r => r.data)

export const getInvoice = (id: number): Promise<Invoice> =>
  api.get<Invoice>(`/invoices/${id}`).then(r => r.data)

export const createInvoice = (data: Partial<Invoice>): Promise<Invoice> =>
  api.post<Invoice>('/invoices', data).then(r => r.data)

export const updateInvoice = (id: number, data: Partial<Invoice>): Promise<Invoice> =>
  api.put<Invoice>(`/invoices/${id}`, data).then(r => r.data)

// ===== Notifications =====

export const getNotifications = (params?: Record<string, unknown>): Promise<PaginatedResponse<Notification>> =>
  api.get<PaginatedResponse<Notification>>('/notifications', { params }).then(r => r.data)

export const getUnreadCount = (): Promise<{ count: number }> =>
  api.get<{ count: number }>('/notifications/unread-count').then(r => r.data)

export const markNotificationRead = (id: number): Promise<Notification> =>
  api.post<Notification>(`/notifications/${id}/read`).then(r => r.data)

export const markAllNotificationsRead = (): Promise<void> =>
  api.post('/notifications/read-all').then(() => undefined)

export const getNotificationSettings = (): Promise<NotificationSetting[]> =>
  api.get<NotificationSetting[]>('/notifications/settings').then(r => r.data)

export const updateNotificationSetting = (
  event_type: string,
  channel: string,
  enabled: boolean
): Promise<NotificationSetting> =>
  api
    .put<NotificationSetting>('/notifications/settings', { event_type, channel, enabled })
    .then(r => r.data)
