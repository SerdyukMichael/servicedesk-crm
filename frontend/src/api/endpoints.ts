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
  WorkActItemCreate,
  WorkTemplate,
  SparePart,
  SparePartPriceUpdate,
  PriceHistoryEntry,
  Vendor,
  Invoice,
  ServiceCatalogItem,
  Notification,
  NotificationSetting,
  PaginatedResponse,
  LoginResponse,
  CurrencySetting,
  CurrencySettingUpdate,
  ExchangeRate,
  ExchangeRateHistoryItem,
  ExchangeRateCreate,
  AuditLogEntry,
  TicketReport,
  MaintenanceSchedule,
  MaintenanceFrequency,
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

export const getClientContacts = (clientId: number, includeInactive = false): Promise<ClientContact[]> =>
  api
    .get<ClientContact[]>(`/clients/${clientId}/contacts`, { params: { include_inactive: includeInactive } })
    .then(r => r.data)

export const createClientContact = (
  clientId: number,
  data: Partial<ClientContact>
): Promise<ClientContact> =>
  api.post<ClientContact>(`/clients/${clientId}/contacts`, data).then(r => r.data)

export const updateClientContact = (
  clientId: number,
  contactId: number,
  data: Partial<ClientContact>
): Promise<ClientContact> =>
  api.put<ClientContact>(`/clients/${clientId}/contacts/${contactId}`, data).then(r => r.data)

export const deactivateClientContact = (clientId: number, contactId: number): Promise<void> =>
  api.delete(`/clients/${clientId}/contacts/${contactId}`).then(() => undefined)

export const grantPortalAccess = (
  clientId: number,
  contactId: number,
  data: { email?: string; portal_role: string }
): Promise<ClientContact> =>
  api
    .post<ClientContact>(`/clients/${clientId}/contacts/${contactId}/portal-access`, data)
    .then(r => r.data)

export const revokePortalAccess = (clientId: number, contactId: number): Promise<ClientContact> =>
  api
    .delete<ClientContact>(`/clients/${clientId}/contacts/${contactId}/portal-access`)
    .then(r => r.data)

// ===== Equipment =====

export const getEquipment = (params?: Record<string, unknown>): Promise<PaginatedResponse<Equipment>> =>
  api.get<PaginatedResponse<Equipment>>('/equipment', { params }).then(r => r.data)

export const getEquipmentItem = (id: number): Promise<Equipment> =>
  api.get<Equipment>(`/equipment/${id}`).then(r => r.data)

export const createEquipment = (data: Partial<Equipment>): Promise<Equipment> =>
  api.post<Equipment>('/equipment', data).then(r => r.data)

export const updateEquipment = (id: number, data: Partial<Equipment>): Promise<Equipment> =>
  api.put<Equipment>(`/equipment/${id}`, data).then(r => r.data)

export const getEquipmentModels = (includeInactive = false): Promise<EquipmentModel[]> =>
  api
    .get<EquipmentModel[]>('/equipment/models', { params: { include_inactive: includeInactive } })
    .then(r => r.data)

export const createEquipmentModel = (data: Partial<EquipmentModel>): Promise<EquipmentModel> =>
  api.post<EquipmentModel>('/equipment/models', data).then(r => r.data)

export const updateEquipmentModel = (id: number, data: Partial<EquipmentModel>): Promise<EquipmentModel> =>
  api.put<EquipmentModel>(`/equipment/models/${id}`, data).then(r => r.data)

export const deactivateEquipmentModel = (id: number): Promise<EquipmentModel> =>
  api.patch<EquipmentModel>(`/equipment/models/${id}/deactivate`).then(r => r.data)

export const activateEquipmentModel = (id: number): Promise<EquipmentModel> =>
  api.patch<EquipmentModel>(`/equipment/models/${id}/activate`).then(r => r.data)

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
  data: { work_description?: string; description?: string; work_performed?: string; items?: WorkActItemCreate[] }
): Promise<WorkAct> =>
  api.post<WorkAct>(`/tickets/${ticketId}/work-act`, data).then(r => r.data)

export const updateWorkAct = (
  ticketId: number,
  data: { work_description?: string; total_time_minutes?: number; items?: WorkActItemCreate[]; force_save?: boolean }
): Promise<WorkAct> =>
  api.patch<WorkAct>(`/tickets/${ticketId}/work-act`, data).then(r => r.data)

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
  api.get<PaginatedResponse<WorkTemplate>>('/work-templates', { params: { size: 200 } }).then(r => r.data.items)

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

export const createInvoiceFromAct = (ticketId: number): Promise<Invoice> =>
  api.post<Invoice>(`/invoices/from-act/${ticketId}`).then(r => r.data)

export const getInvoicesByTicket = (ticketId: number): Promise<Invoice[]> =>
  api.get<PaginatedResponse<Invoice>>('/invoices', { params: { ticket_id: ticketId, size: 10 } })
    .then(r => r.data.items)

export const sendInvoice = (id: number): Promise<Invoice> =>
  api.post<Invoice>(`/invoices/${id}/send`).then(r => r.data)

export const payInvoice = (id: number): Promise<Invoice> =>
  api.post<Invoice>(`/invoices/${id}/pay`).then(r => r.data)

// ===== Service Catalog =====

export const getServiceCatalog = (params?: Record<string, unknown>): Promise<PaginatedResponse<ServiceCatalogItem>> =>
  api.get<PaginatedResponse<ServiceCatalogItem>>('/service-catalog', { params }).then(r => r.data)

export const getServiceCatalogItem = (id: number): Promise<ServiceCatalogItem> =>
  api.get<ServiceCatalogItem>(`/service-catalog/${id}`).then(r => r.data)

export const createServiceCatalogItem = (data: Partial<ServiceCatalogItem>): Promise<ServiceCatalogItem> =>
  api.post<ServiceCatalogItem>('/service-catalog', data).then(r => r.data)

export const updateServiceCatalogItem = (id: number, data: Partial<ServiceCatalogItem>): Promise<ServiceCatalogItem> =>
  api.patch<ServiceCatalogItem>(`/service-catalog/${id}`, data).then(r => r.data)

export const deleteServiceCatalogItem = (id: number): Promise<void> =>
  api.delete(`/service-catalog/${id}`).then(() => undefined)

// ===== Parts Price Management =====

export const setPartPrice = (id: number, data: SparePartPriceUpdate): Promise<SparePart> =>
  api.patch<SparePart>(`/parts/${id}/price`, data).then(r => r.data)

export const getPartPriceHistory = (id: number): Promise<PriceHistoryEntry[]> =>
  api.get<PriceHistoryEntry[]>(`/parts/${id}/price-history`).then(r => r.data)

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

// ===== Settings =====

export const getCurrency = (): Promise<CurrencySetting> =>
  api.get<CurrencySetting>('/settings/currency').then(r => r.data)

export const updateCurrency = (data: CurrencySettingUpdate): Promise<CurrencySetting> =>
  api.put<CurrencySetting>('/settings/currency', data).then(r => r.data)

export const getExchangeRates = (): Promise<ExchangeRate[]> =>
  api.get<ExchangeRate[]>('/settings/exchange-rates').then(r => r.data)

export const createExchangeRate = (data: ExchangeRateCreate): Promise<ExchangeRate> =>
  api.post<ExchangeRate>('/settings/exchange-rates', data).then(r => r.data)

export const getExchangeRateHistory = (
  currency: string,
  page = 1,
  size = 20,
): Promise<PaginatedResponse<ExchangeRateHistoryItem>> =>
  api
    .get<PaginatedResponse<ExchangeRateHistoryItem>>(`/settings/exchange-rates/${currency}`, {
      params: { page, size },
    })
    .then(r => r.data)

// ===== Audit Log =====

export const getAuditLog = (params: {
  user_id?: number
  action?: string
  entity_type?: string
  date_from?: string
  date_to?: string
  ip_address?: string
  page?: number
  size?: number
}): Promise<PaginatedResponse<AuditLogEntry>> =>
  api.get<PaginatedResponse<AuditLogEntry>>('/audit-log', { params }).then(r => r.data)

export const getAuditLogExportUrl = (params: Record<string, string | number | undefined>): string => {
  const base = api.defaults.baseURL || '/api/v1'
  const q = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== '')
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
    .join('&')
  return `${base}/audit-log/export${q ? '?' + q : ''}`
}

// ===== Reports =====

export const getTicketReport = (params: {
  date_from: string
  date_to: string
  engineer_id?: number
  client_id?: number
}): Promise<TicketReport> =>
  api.get<TicketReport>('/reports/tickets', { params }).then(r => r.data)

export const getTicketReportExportUrl = (params: Record<string, string | number | undefined>): string => {
  const base = api.defaults.baseURL || '/api/v1'
  const q = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== '')
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
    .join('&')
  return `${base}/reports/tickets/export/xlsx${q ? '?' + q : ''}`
}

// ===== Maintenance Schedule =====

export const getMaintenanceSchedule = (equipmentId: number): Promise<MaintenanceSchedule | null> =>
  api.get<MaintenanceSchedule | null>(`/equipment/${equipmentId}/maintenance-schedule`).then(r => r.data)

export const createMaintenanceSchedule = (
  equipmentId: number,
  data: { frequency: MaintenanceFrequency; first_date: string }
): Promise<MaintenanceSchedule> =>
  api.post<MaintenanceSchedule>(`/equipment/${equipmentId}/maintenance-schedule`, data).then(r => r.data)

export const updateMaintenanceSchedule = (
  equipmentId: number,
  data: { frequency?: MaintenanceFrequency; first_date?: string; next_date?: string; is_active?: boolean }
): Promise<MaintenanceSchedule> =>
  api.put<MaintenanceSchedule>(`/equipment/${equipmentId}/maintenance-schedule`, data).then(r => r.data)
