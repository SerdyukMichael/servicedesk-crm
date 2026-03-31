// ===== Enums / literals =====

export type UserRole = 'admin' | 'engineer' | 'manager' | 'svc_mgr' | 'director' | 'sales_mgr'

export type TicketStatus =
  | 'new'
  | 'assigned'
  | 'in_progress'
  | 'waiting_part'
  | 'on_review'
  | 'completed'
  | 'closed'
  | 'cancelled'

export type TicketPriority = 'critical' | 'high' | 'medium' | 'low'
export type TicketType = 'repair' | 'maintenance' | 'installation' | 'consultation' | 'other'

export type EquipmentStatus = 'active' | 'inactive' | 'decommissioned' | 'in_repair' | 'written_off' | 'transferred'
export type WarrantyStatus = 'on_warranty' | 'expiring' | 'expired' | 'unknown'
export type ContractType = 'full_service' | 'partial' | 'time_and_material' | 'warranty'
export type InvoiceStatus = 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled'
export type InvoiceType = 'service' | 'parts' | 'combined'
export type NotificationChannel = 'in_app' | 'email' | 'telegram'

// ===== Core models =====

export interface User {
  id: number
  email: string
  full_name: string
  phone?: string
  roles: UserRole[]
  is_active: boolean
  last_login?: string
  last_login_at?: string
  created_at: string
}

export interface Client {
  id: number
  name: string
  inn?: string
  contract_type?: ContractType
  contract_number?: string
  contract_start?: string
  contract_end?: string
  address?: string
  city?: string
  manager_id?: number
  manager?: User
  created_at: string
  contacts?: ClientContact[]
}

export interface ClientContact {
  id: number
  client_id: number
  name: string
  position?: string
  phone?: string
  email?: string
  is_primary: boolean
}

export interface EquipmentModel {
  id: number
  name: string
  manufacturer?: string
  category?: string
  description?: string
}

export interface Equipment {
  id: number
  serial_number: string
  model_id?: number
  model?: EquipmentModel
  client_id: number
  client?: Client
  location?: string
  address?: string
  status: EquipmentStatus
  installation_date?: string
  installed_at?: string
  warranty_end?: string
  warranty_until?: string
  warranty_start?: string
  manufacture_date?: string
  sale_date?: string
  firmware_version?: string
  warranty_status?: WarrantyStatus
  notes?: string
  created_at: string
}

export interface Ticket {
  id: number
  number: string
  title: string
  description?: string
  type: TicketType
  status: TicketStatus
  priority: TicketPriority
  client_id: number
  client?: Client
  equipment_id?: number
  equipment?: Equipment
  engineer_id?: number
  engineer?: User
  created_by_id: number
  created_by?: User
  sla_deadline?: string
  resolved_at?: string
  work_template_id?: number
  work_template?: WorkTemplate
  work_act?: WorkAct
  created_at: string
  updated_at: string
}

export interface TicketStatusHistoryEntry {
  id: number
  ticket_id: number
  from_status?: string
  to_status: string
  changed_by?: number
  changer?: User
  comment?: string
  changed_at: string
}

export interface TicketComment {
  id: number
  ticket_id: number
  author_id: number
  author?: User
  text: string
  is_internal: boolean
  created_at: string
}

export interface TicketAttachment {
  id: number
  ticket_id: number
  filename: string
  file_url: string
  uploaded_by_id: number
  uploaded_by?: User
  created_at: string
}

export interface WorkAct {
  id: number
  ticket_id: number
  act_number?: string
  description?: string
  work_performed?: string
  parts_used?: WorkActPart[]
  signed_by_engineer?: boolean
  signed_by_client?: boolean
  signed_at?: string
  created_at: string
}

export interface WorkActPart {
  part_id: number
  part?: SparePart
  quantity: number
  price: number
}

export interface WorkTemplate {
  id: number
  name: string
  description?: string
  default_priority: TicketPriority
  default_type: TicketType
  checklist?: WorkTemplateItem[]
  estimated_hours?: number
}

export interface WorkTemplateItem {
  id: number
  template_id: number
  step_order: number
  description: string
}

export interface SparePart {
  id: number
  sku: string
  name: string
  category?: string
  quantity: number
  min_quantity: number
  price: number
  vendor_id?: number
  vendor?: Vendor
  description?: string
  created_at: string
}

export interface Vendor {
  id: number
  name: string
  inn?: string
  contact_name?: string
  phone?: string
  email?: string
  address?: string
  notes?: string
  created_at: string
}

export interface Invoice {
  id: number
  number: string
  client_id: number
  client?: Client
  ticket_id?: number
  type: InvoiceType
  status: InvoiceStatus
  total_amount: number
  issued_date: string
  due_date?: string
  paid_date?: string
  notes?: string
  created_at: string
}

export interface Notification {
  id: number
  user_id: number
  title: string
  body?: string
  event_type: string
  is_read: boolean
  ticket_id?: number
  created_at: string
}

export interface NotificationSetting {
  id: number
  user_id: number
  event_type: string
  channel: NotificationChannel
  enabled: boolean
}

// ===== API wrappers =====

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export interface ErrorResponse {
  detail: string | { msg: string; type: string }[]
}
