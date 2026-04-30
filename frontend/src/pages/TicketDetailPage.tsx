import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { format, isPast, parseISO, differenceInSeconds } from 'date-fns'
import { ru } from 'date-fns/locale'
import {
  useTicket,
  useTicketComments,
  useTicketAttachments,
  useTicketStatusHistory,
  useWorkAct,
  useAddComment,
  useAssignEngineer,
  useChangeTicketStatus,
  useCreateWorkAct,
  useUpdateWorkAct,
  useSignWorkAct,
  useUploadAttachment,
} from '../hooks/useTickets'
import { useUsers } from '../hooks/useUsers'
import { useAuth } from '../context/AuthContext'
import { useCurrency } from '../context/CurrencyContext'
import { useServiceCatalog } from '../hooks/useServiceCatalog'
import { useParts } from '../hooks/useParts'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createInvoiceFromAct, getInvoicesByTicket } from '../api/endpoints'
import StatusBadge from '../components/StatusBadge'
import PriorityBadge from '../components/PriorityBadge'
import type { TicketStatus, WorkActItemCreate, WorkActItemType } from '../api/types'

function SlaCountdown({ deadline }: { deadline: string }) {
  const [secs, setSecs] = useState(() => differenceInSeconds(parseISO(deadline), new Date()))
  useEffect(() => {
    const id = setInterval(() => setSecs(differenceInSeconds(parseISO(deadline), new Date())), 1000)
    return () => clearInterval(id)
  }, [deadline])
  if (secs <= 0) return null
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  const color = secs < 3600 ? '#e74c3c' : secs < 14400 ? '#e67e22' : '#27ae60'
  return (
    <span style={{ marginLeft: 8, fontFamily: 'monospace', fontSize: 12, color, fontWeight: 600 }}>
      ({h.toString().padStart(2, '0')}:{m.toString().padStart(2, '0')}:{s.toString().padStart(2, '0')})
    </span>
  )
}

const STATUS_TRANSITIONS: Record<TicketStatus, TicketStatus[]> = {
  new: ['cancelled'],
  assigned: ['in_progress', 'cancelled'],
  in_progress: ['waiting_part', 'on_review', 'cancelled'],
  waiting_part: ['in_progress', 'cancelled'],
  on_review: ['completed', 'in_progress'],
  completed: ['closed', 'in_progress'],   // BR-F-125: возобновление
  closed: ['in_progress'],                // BR-F-125: возобновление
  cancelled: [],
}

const REOPEN_SOURCES: TicketStatus[] = ['closed', 'completed']

const STATUS_LABELS: Record<TicketStatus, string> = {
  new: 'Новая',
  assigned: 'Назначена',
  in_progress: 'В работе',
  waiting_part: 'Ожидание запчасти',
  on_review: 'На проверке',
  completed: 'Завершена',
  closed: 'Закрыта',
  cancelled: 'Отменена',
}

const TYPE_LABELS: Record<string, string> = {
  repair: 'Ремонт',
  maintenance: 'ТО',
  installation: 'Установка',
  consultation: 'Консультация',
  other: 'Прочее',
}

export default function TicketDetailPage() {
  const { id } = useParams<{ id: string }>()
  const ticketId = parseInt(id ?? '0', 10)
  const navigate = useNavigate()
  const { hasRole } = useAuth()
  const { currency } = useCurrency()

  const { data: ticket, isLoading, isError } = useTicket(ticketId)
  const { data: comments } = useTicketComments(ticketId)
  const { data: attachments } = useTicketAttachments(ticketId)
  const { data: statusHistory } = useTicketStatusHistory(ticketId)
  const { data: workAct } = useWorkAct(ticketId)
  const { data: ticketInvoices } = useQuery({
    queryKey: ['invoices', 'by-ticket', ticketId],
    queryFn: () => getInvoicesByTicket(ticketId),
    enabled: !!ticketId,
  })
  const ticketInvoice = ticketInvoices?.[0] ?? null
  const { data: usersData } = useUsers({ role: 'engineer', size: 100 })
  const { data: serviceCatalog } = useServiceCatalog({ size: 200 })
  const { data: partsData } = useParts({ size: 200, has_price: true })
  const qc = useQueryClient()
  const createInvoiceFromActMutation = useMutation({
    mutationFn: () => createInvoiceFromAct(ticketId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['invoices'] })
      qc.invalidateQueries({ queryKey: ['invoices', 'by-ticket', ticketId] })
      setInvoiceFromActError(null)
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: { message?: string } | string } } })
        ?.response?.data?.detail
      const msg = typeof detail === 'object' ? detail?.message : detail
      setInvoiceFromActError(msg ?? 'Ошибка создания счёта')
    },
  })

  const assignMutation = useAssignEngineer(ticketId)
  const statusMutation = useChangeTicketStatus(ticketId)
  const addComment = useAddComment(ticketId)
  const createWorkAct = useCreateWorkAct(ticketId)
  const updateWorkAct = useUpdateWorkAct(ticketId)
  const signWorkAct = useSignWorkAct(ticketId)
  const uploadAttachment = useUploadAttachment(ticketId)

  const [selectedEngineer, setSelectedEngineer] = useState<string>('')
  const [assignError, setAssignError] = useState<string | null>(null)
  const [commentText, setCommentText] = useState('')
  const [isInternal, setIsInternal] = useState(false)
  const [workActDesc, setWorkActDesc] = useState('')
  const [workActPerformed, setWorkActPerformed] = useState('')
  const [showWorkActForm, setShowWorkActForm] = useState(false)
  const [isEditingAct, setIsEditingAct] = useState(false)
  const [actItems, setActItems] = useState<WorkActItemCreate[]>([])
  const [invoiceFromActError, setInvoiceFromActError] = useState<string | null>(null)
  const [paidMismatch, setPaidMismatch] = useState<{ actTotal: string; invoiceTotal: string } | null>(null)

  if (isLoading)
    return (
      <div className="loading-center">
        <span className="spinner spinner-lg" />
      </div>
    )
  if (isError || !ticket)
    return (
      <div className="alert alert-error">Ошибка загрузки заявки</div>
    )

  const isOverdue =
    ticket.sla_deadline &&
    isPast(parseISO(ticket.sla_deadline)) &&
    !['completed', 'closed', 'cancelled'].includes(ticket.status)

  const isUnderWarranty = ticket.equipment?.warranty_until
    ? new Date(ticket.equipment.warranty_until) >= new Date(new Date().toISOString().split('T')[0])
    : false

  const isClientUser = hasRole('client_user')
  const canAssign = hasRole('admin', 'svc_mgr')
  const canChangeStatus = hasRole('admin', 'svc_mgr', 'engineer')
  // BR-F-125: роли, которым разрешено возобновлять заявку
  const canReopen = hasRole('admin', 'svc_mgr', 'client_user')

  // Фильтруем переходы: reopen (→ in_progress из closed/completed) — только canReopen
  const transitions = (STATUS_TRANSITIONS[ticket.status] ?? []).filter(s => {
    if (s === 'in_progress' && REOPEN_SOURCES.includes(ticket.status as TicketStatus)) {
      return canReopen
    }
    return canChangeStatus
  })

  const engineers = usersData?.items ?? []

  const getTransitionLabel = (to: TicketStatus): string => {
    if (to === 'in_progress' && REOPEN_SOURCES.includes(ticket.status as TicketStatus)) {
      return 'Возобновить'
    }
    return STATUS_LABELS[to]
  }
  const canCreateAct = hasRole('engineer', 'svc_mgr', 'admin')
  const canSignAct = hasRole('client_user')

  const handleAssign = () => {
    if (!selectedEngineer) {
      setAssignError('Необходимо назначить инженера на заявку')
      return
    }
    setAssignError(null)
    assignMutation.mutate(parseInt(selectedEngineer, 10), {
      onSuccess: () => setSelectedEngineer(''),
    })
  }

  const handleStatusChange = (newStatus: TicketStatus) => {
    statusMutation.mutate(newStatus)
  }

  const handleAddComment = () => {
    if (!commentText.trim()) return
    addComment.mutate(
      { text: commentText.trim(), isInternal },
      { onSuccess: () => setCommentText('') }
    )
  }

  const handleSubmitWorkAct = async () => {
    const closeForm = () => {
      setShowWorkActForm(false)
      setIsEditingAct(false)
      setActItems([])
      setWorkActDesc('')
    }
    if (isEditingAct) {
      try {
        await updateWorkAct.mutateAsync({ work_description: workActDesc, items: actItems })
        closeForm()
      } catch (err: unknown) {
        const data = (err as { response?: { data?: Record<string, string> } })
          ?.response?.data
        if (data?.error === 'INVOICE_PAID_MISMATCH') {
          setPaidMismatch({ actTotal: data.act_total, invoiceTotal: data.invoice_total })
        }
      }
    } else {
      try {
        await createWorkAct.mutateAsync(
          { work_description: workActDesc, work_performed: workActPerformed, items: actItems }
        )
        closeForm()
      } catch {
        // ошибка создания — ничего не делаем (хук уже в isError)
      }
    }
  }

  const handleEditWorkAct = () => {
    if (!workAct) return
    setWorkActDesc(workAct.work_description ?? '')
    setActItems(
      (workAct.items ?? []).map(item => ({
        item_type: item.item_type as WorkActItemType,
        service_id: item.service_id ?? undefined,
        part_id: item.part_id ?? undefined,
        name: item.name,
        quantity: item.quantity,
        unit: item.unit,
        unit_price: item.unit_price,
        sort_order: item.sort_order,
      }))
    )
    setIsEditingAct(true)
    setShowWorkActForm(true)
  }

  const handleForceSaveAct = () => {
    const onSuccess = () => {
      setShowWorkActForm(false)
      setIsEditingAct(false)
      setActItems([])
      setWorkActDesc('')
      setPaidMismatch(null)
    }
    updateWorkAct.mutate(
      { work_description: workActDesc, items: actItems, force_save: true },
      { onSuccess }
    )
  }

  const addActItem = () => {
    setActItems(prev => [...prev, {
      item_type: 'service' as WorkActItemType,
      name: '',
      quantity: '1',
      unit: 'шт',
      unit_price: '0',
    }])
  }

  const removeActItem = (idx: number) => {
    setActItems(prev => prev.filter((_, i) => i !== idx))
  }

  const updateActItem = (idx: number, patch: Partial<WorkActItemCreate>) => {
    setActItems(prev => prev.map((item, i) => i === idx ? { ...item, ...patch } : item))
  }

  const selectServiceForItem = (idx: number, serviceId: number) => {
    const svc = serviceCatalog?.items.find(s => s.id === serviceId)
    if (!svc) return
    updateActItem(idx, {
      service_id: serviceId,
      part_id: undefined,
      name: svc.name,
      unit: svc.unit === 'pcs' ? 'шт' : svc.unit === 'hour' ? 'час' : svc.unit === 'visit' ? 'визит' : 'компл.',
      unit_price: svc.unit_price,
    })
  }

  const selectPartForItem = (idx: number, partId: number) => {
    const part = partsData?.items.find(p => p.id === partId)
    if (!part) return
    updateActItem(idx, {
      part_id: partId,
      service_id: undefined,
      name: part.name,
      unit: 'шт',
      unit_price: String(part.unit_price ?? 0),
    })
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) uploadAttachment.mutate(file)
  }

  const getInitials = (name: string) =>
    name
      .split(' ')
      .slice(0, 2)
      .map(w => w[0])
      .join('')
      .toUpperCase()

  return (
    <>
      <div className="page-header">
        <div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
            <span
              style={{ cursor: 'pointer' }}
              onClick={() => navigate('/tickets')}
            >
              Заявки
            </span>{' '}
            / {ticket.number}
          </div>
          <h1 style={{ fontSize: '1.25rem' }}>{ticket.title}</h1>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <StatusBadge status={ticket.status} />
          <PriorityBadge priority={ticket.priority} />
        </div>
      </div>

      <div className="detail-grid">
        {/* Left column: main info */}
        <div>
          {/* Main info card */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header">
              <h3>Информация о заявке</h3>
            </div>
            <div className="card-body">
              <ul className="info-list">
                <li>
                  <span className="info-list-label">Номер</span>
                  <span className="info-list-value">{ticket.number}</span>
                </li>
                <li>
                  <span className="info-list-label">Тип</span>
                  <span className="info-list-value">
                    {TYPE_LABELS[ticket.type] ?? ticket.type}
                  </span>
                </li>
                <li>
                  <span className="info-list-label">Клиент</span>
                  <span className="info-list-value">
                    {ticket.client?.name ?? '—'}
                  </span>
                </li>
                <li>
                  <span className="info-list-label">Оборудование</span>
                  <span className="info-list-value">
                    {ticket.equipment
                      ? `${ticket.equipment.model?.name ?? 'Модель не указана'} (s/n: ${ticket.equipment.serial_number})`
                      : '—'}
                  </span>
                </li>
                <li>
                  <span className="info-list-label">Инженер</span>
                  <span className="info-list-value">
                    {ticket.engineer?.full_name ?? 'Не назначен'}
                  </span>
                </li>
                <li>
                  <span className="info-list-label">Создана</span>
                  <span className="info-list-value">
                    {format(parseISO(ticket.created_at), 'dd.MM.yyyy HH:mm', { locale: ru })}
                  </span>
                </li>
                {ticket.sla_deadline && !ticket.sla_reaction_deadline && (
                  <li>
                    <span className="info-list-label">SLA дедлайн</span>
                    <span className={`info-list-value${isOverdue ? ' sla-overdue' : ''}`}>
                      {format(parseISO(ticket.sla_deadline), 'dd.MM.yyyy HH:mm', { locale: ru })}
                      {isOverdue && ' — просрочено!'}
                    </span>
                  </li>
                )}
                {ticket.sla_reaction_deadline && (
                  <li>
                    <span className="info-list-label">SLA реакции</span>
                    <span className={`info-list-value${ticket.sla_reaction_violated ? ' sla-overdue' : ''}`}>
                      {format(parseISO(ticket.sla_reaction_deadline), 'dd.MM.yyyy HH:mm', { locale: ru })}
                      {ticket.sla_reaction_violated
                        ? <span style={{ marginLeft: 6, color: '#e74c3c', fontWeight: 600 }}>— нарушен</span>
                        : !isPast(parseISO(ticket.sla_reaction_deadline))
                          ? <SlaCountdown deadline={ticket.sla_reaction_deadline} />
                          : null}
                    </span>
                  </li>
                )}
                {ticket.sla_resolution_deadline && (
                  <li>
                    <span className="info-list-label">SLA решения</span>
                    <span className={`info-list-value${ticket.sla_resolution_violated ? ' sla-overdue' : ''}`}>
                      {format(parseISO(ticket.sla_resolution_deadline), 'dd.MM.yyyy HH:mm', { locale: ru })}
                      {ticket.sla_resolution_violated
                        ? <span style={{ marginLeft: 6, color: '#e74c3c', fontWeight: 600 }}>— нарушен</span>
                        : !isPast(parseISO(ticket.sla_resolution_deadline))
                          ? <SlaCountdown deadline={ticket.sla_resolution_deadline} />
                          : null}
                    </span>
                  </li>
                )}
                {ticket.resolved_at && (
                  <li>
                    <span className="info-list-label">Решена</span>
                    <span className="info-list-value">
                      {format(parseISO(ticket.resolved_at), 'dd.MM.yyyy HH:mm', { locale: ru })}
                    </span>
                  </li>
                )}
              </ul>

              {ticket.description && (
                <div style={{ marginTop: 16 }}>
                  <div
                    style={{
                      fontSize: 12,
                      fontWeight: 600,
                      color: 'var(--text-muted)',
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                      marginBottom: 8,
                    }}
                  >
                    Описание
                  </div>
                  <p style={{ fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                    {ticket.description}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Work act */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header">
              <h3>Акт выполненных работ</h3>
              {canCreateAct && !workAct && (
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => {
                    if (showWorkActForm) {
                      setShowWorkActForm(false)
                      setIsEditingAct(false)
                      setActItems([])
                      setWorkActDesc('')
                    } else {
                      setIsEditingAct(false)
                      setShowWorkActForm(true)
                    }
                  }}
                >
                  {showWorkActForm ? 'Отмена' : '+ Создать акт'}
                </button>
              )}
              {canCreateAct && workAct && !workAct.signed_by && (!ticketInvoice || hasRole('admin')) && (
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => {
                    if (showWorkActForm && isEditingAct) {
                      setShowWorkActForm(false)
                      setIsEditingAct(false)
                      setActItems([])
                      setWorkActDesc('')
                    } else {
                      handleEditWorkAct()
                    }
                  }}
                >
                  {showWorkActForm && isEditingAct ? 'Отмена' : 'Редактировать акт'}
                </button>
              )}
            </div>
            <div className="card-body">
              {showWorkActForm && (
                <div style={{ marginBottom: 16 }}>
                  <div className="form-group">
                    <label className="form-label">Описание работ</label>
                    <textarea
                      className="form-textarea"
                      value={workActDesc}
                      onChange={e => setWorkActDesc(e.target.value)}
                      placeholder="Опишите проведённые работы..."
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Выполненные работы</label>
                    <textarea
                      className="form-textarea"
                      value={workActPerformed}
                      onChange={e => setWorkActPerformed(e.target.value)}
                      placeholder="Детали выполненных работ..."
                    />
                  </div>

                  {/* Act items */}
                  <div style={{ marginBottom: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <label className="form-label" style={{ margin: 0 }}>Позиции акта</label>
                      <button className="btn btn-secondary btn-sm" type="button" onClick={addActItem}>
                        + Добавить позицию
                      </button>
                    </div>
                    {actItems.length > 0 && (
                      <div style={{ border: '1px solid var(--border)', borderRadius: 6, overflow: 'hidden' }}>
                        {actItems.map((item, idx) => (
                          <div key={idx} style={{ padding: 10, borderBottom: idx < actItems.length - 1 ? '1px solid var(--border)' : 'none', background: idx % 2 === 0 ? 'var(--surface)' : 'transparent' }}>
                            <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                              <select
                                className="form-select"
                                style={{ width: 110, flex: 'none' }}
                                value={item.item_type}
                                onChange={e => updateActItem(idx, { item_type: e.target.value as WorkActItemType, service_id: undefined, part_id: undefined, name: '' })}
                              >
                                <option value="service">Услуга</option>
                                <option value="part">Запчасть</option>
                              </select>

                              {item.item_type === 'service' ? (
                                <select
                                  className="form-select"
                                  style={{ flex: 1, minWidth: 160 }}
                                  value={item.service_id ?? ''}
                                  onChange={e => e.target.value ? selectServiceForItem(idx, parseInt(e.target.value)) : updateActItem(idx, { service_id: undefined, name: '' })}
                                >
                                  <option value="">— выбрать услугу —</option>
                                  {serviceCatalog?.items.filter(s => s.is_active).map(s => (
                                    <option key={s.id} value={s.id}>{s.name} ({parseFloat(s.unit_price).toLocaleString('ru-RU')} {currency.currency_code})</option>
                                  ))}
                                </select>
                              ) : (
                                <select
                                  className="form-select"
                                  style={{ flex: 1, minWidth: 160 }}
                                  value={item.part_id ?? ''}
                                  onChange={e => e.target.value ? selectPartForItem(idx, parseInt(e.target.value)) : updateActItem(idx, { part_id: undefined, name: '' })}
                                >
                                  <option value="">— выбрать запчасть —</option>
                                  {partsData?.items.map(p => (
                                    <option key={p.id} value={p.id}>{p.name} (SKU: {p.sku}, {p.quantity} шт)</option>
                                  ))}
                                </select>
                              )}

                              <input
                                type="text"
                                className="form-input"
                                style={{ width: 130 }}
                                placeholder="Название"
                                value={item.name}
                                onChange={e => updateActItem(idx, { name: e.target.value })}
                              />
                              <input
                                type="number"
                                className="form-input"
                                style={{ width: 70 }}
                                placeholder="Кол-во"
                                min="0"
                                step="0.001"
                                value={item.quantity}
                                onChange={e => updateActItem(idx, { quantity: e.target.value })}
                              />
                              <input
                                type="text"
                                className="form-input"
                                style={{ width: 60 }}
                                placeholder="Ед."
                                value={item.unit}
                                onChange={e => updateActItem(idx, { unit: e.target.value })}
                              />
                              <input
                                type="number"
                                className="form-input"
                                style={{ width: 90 }}
                                placeholder="Цена"
                                min="0"
                                step="0.01"
                                value={item.unit_price}
                                onChange={e => updateActItem(idx, { unit_price: e.target.value })}
                              />
                              <span style={{ fontSize: 13, color: 'var(--text-muted)', alignSelf: 'center', whiteSpace: 'nowrap' }}>
                                = {(parseFloat(item.quantity || '0') * parseFloat(item.unit_price || '0')).toLocaleString('ru-RU', { minimumFractionDigits: 2 })} {currency.currency_code}
                              </span>
                              <button
                                type="button"
                                className="btn btn-danger btn-sm"
                                style={{ flex: 'none' }}
                                onClick={() => removeActItem(idx)}
                              >
                                ×
                              </button>
                            </div>
                          </div>
                        ))}
                        <div style={{ padding: '8px 12px', background: 'var(--surface-alt, var(--surface))', fontSize: 13, fontWeight: 600, textAlign: 'right' }}>
                          Итого: {actItems.reduce((s, i) => s + parseFloat(i.quantity || '0') * parseFloat(i.unit_price || '0'), 0).toLocaleString('ru-RU', { minimumFractionDigits: 2 })} {currency.currency_code}
                        </div>
                      </div>
                    )}
                  </div>

                  <button
                    className="btn btn-primary btn-sm"
                    onClick={handleSubmitWorkAct}
                    disabled={createWorkAct.isPending || updateWorkAct.isPending}
                  >
                    {(createWorkAct.isPending || updateWorkAct.isPending)
                      ? 'Сохранение...'
                      : isEditingAct ? 'Сохранить изменения' : 'Создать акт'}
                  </button>
                </div>
              )}

              {workAct ? (
                <div className="work-act-card">
                  <ul className="info-list">
                    {workAct.act_number && (
                      <li>
                        <span className="info-list-label">Номер акта</span>
                        <span className="info-list-value">{workAct.act_number}</span>
                      </li>
                    )}
                    <li>
                      <span className="info-list-label">Дата создания</span>
                      <span className="info-list-value">
                        {format(parseISO(workAct.created_at), 'dd.MM.yyyy', { locale: ru })}
                      </span>
                    </li>
                    <li>
                      <span className="info-list-label">Подпись клиента</span>
                      <span className="info-list-value" style={{ color: workAct.signed_by ? 'var(--color-success, #22c55e)' : undefined }}>
                        {workAct.signed_by ? '✓ Подписан' : 'Не подписан'}
                        {workAct.signed_at && (
                          <span style={{ color: 'var(--text-muted)', marginLeft: 6, fontSize: 11 }}>
                            {format(parseISO(workAct.signed_at), 'dd.MM.yyyy', { locale: ru })}
                          </span>
                        )}
                      </span>
                    </li>
                    {ticketInvoices && ticketInvoices.length > 0 && (
                      <li>
                        <span className="info-list-label">
                          {ticketInvoices.length === 1 ? 'Счёт' : `Счета (${ticketInvoices.length})`}
                        </span>
                        <span className="info-list-value">
                          {ticketInvoices.map(inv => {
                            const statusLabel: Record<string, string> = {
                              draft: 'Черновик', sent: 'Выставлен', paid: 'Оплачен',
                              overdue: 'Просрочен', cancelled: 'Отменён',
                            }
                            const statusColor: Record<string, string> = {
                              draft: '#475569', sent: '#1d4ed8', paid: '#166534',
                              overdue: '#991b1b', cancelled: '#64748b',
                            }
                            const statusBg: Record<string, string> = {
                              draft: '#f1f5f9', sent: '#dbeafe', paid: '#dcfce7',
                              overdue: '#fecaca', cancelled: '#f1f5f9',
                            }
                            const isOverdue = inv.due_date && isPast(parseISO(inv.due_date)) && inv.status !== 'paid'
                            return (
                              <div key={inv.id} style={{ marginBottom: ticketInvoices.length > 1 ? 6 : 0 }}>
                                <Link to={`/invoices/${inv.id}`} style={{ fontWeight: 500 }}>
                                  {inv.number}
                                </Link>
                                {' '}
                                <span style={{
                                  fontSize: 11, padding: '2px 7px', borderRadius: 4,
                                  background: statusBg[inv.status] ?? '#f1f5f9',
                                  color: statusColor[inv.status] ?? '#475569',
                                }}>
                                  {statusLabel[inv.status] ?? inv.status}
                                </span>
                                {' '}
                                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                  {parseFloat(String(inv.total_amount)).toLocaleString('ru-RU')} {currency.currency_code}
                                </span>
                                {inv.issue_date && (
                                  <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 6 }}>
                                    · выставлен {format(parseISO(inv.issue_date), 'dd.MM.yyyy', { locale: ru })}
                                  </span>
                                )}
                                {inv.due_date && (
                                  <span style={{ fontSize: 11, color: isOverdue ? 'var(--danger)' : 'var(--text-muted)', marginLeft: 4 }}>
                                    · срок {format(parseISO(inv.due_date), 'dd.MM.yyyy', { locale: ru })}
                                  </span>
                                )}
                                {inv.paid_at && (
                                  <span style={{ fontSize: 11, color: '#166534', marginLeft: 4 }}>
                                    · оплачен {format(parseISO(inv.paid_at), 'dd.MM.yyyy', { locale: ru })}
                                  </span>
                                )}
                              </div>
                            )
                          })}
                        </span>
                      </li>
                    )}
                  </ul>
                  {workAct.description && (
                    <p style={{ fontSize: 13, marginTop: 12 }}>{workAct.description}</p>
                  )}
                  {workAct.work_description && (
                    <p style={{ fontSize: 13, marginTop: 12 }}>{workAct.work_description}</p>
                  )}

                  {/* Act items table */}
                  {workAct.items && workAct.items.length > 0 && (
                    <div style={{ marginTop: 16 }}>
                      <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Позиции акта</div>
                      <div className="table-wrap" style={{ marginBottom: 0 }}>
                        <table className="table" style={{ fontSize: 12 }}>
                          <thead>
                            <tr>
                              <th>Тип</th>
                              <th>Название</th>
                              <th>Кол-во</th>
                              <th>Ед.</th>
                              <th>Цена</th>
                              <th>Сумма</th>
                            </tr>
                          </thead>
                          <tbody>
                            {workAct.items.map(item => (
                              <tr key={item.id}>
                                <td>
                                  <span className="badge" style={{ fontSize: 10 }}>
                                    {item.item_type === 'service' ? 'Услуга' : 'Запчасть'}
                                  </span>
                                </td>
                                <td>{item.name}</td>
                                <td>{parseFloat(item.quantity)}</td>
                                <td>{item.unit}</td>
                                <td>{parseFloat(item.unit_price).toLocaleString('ru-RU')} {currency.currency_code}</td>
                                <td style={{ fontWeight: 600 }}>{parseFloat(item.total).toLocaleString('ru-RU')} {currency.currency_code}</td>
                              </tr>
                            ))}
                          </tbody>
                          <tfoot>
                            <tr>
                              <td colSpan={5} style={{ textAlign: 'right', fontWeight: 600, fontSize: 13 }}>Итого:</td>
                              <td style={{ fontWeight: 700 }}>
                                {workAct.items.reduce((s, i) => s + parseFloat(i.total), 0).toLocaleString('ru-RU', { minimumFractionDigits: 2 })} {currency.currency_code}
                              </td>
                            </tr>
                          </tfoot>
                        </table>
                      </div>
                    </div>
                  )}

                  <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
                    {canSignAct && !workAct.signed_by && (
                      <button
                        className="btn btn-success btn-sm"
                        onClick={() => signWorkAct.mutate('client')}
                        disabled={signWorkAct.isPending}
                      >
                        Подписать акт
                      </button>
                    )}
                    {hasRole('admin', 'accountant', 'svc_mgr') && !ticketInvoice && (
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={() => createInvoiceFromActMutation.mutate()}
                        disabled={
                          createInvoiceFromActMutation.isPending ||
                          !(workAct.items && workAct.items.length > 0) ||
                          isUnderWarranty
                        }
                        title={
                          isUnderWarranty
                            ? 'Оборудование на гарантии — выставление счёта недоступно'
                            : !(workAct.items && workAct.items.length > 0)
                              ? 'Добавьте позиции в акт перед созданием счёта'
                              : 'Создать счёт на основе позиций акта'
                        }
                      >
                        {createInvoiceFromActMutation.isPending ? 'Создание...' : '📄 Создать счёт из акта'}
                      </button>
                    )}
                  </div>
                  {createInvoiceFromActMutation.isSuccess && (
                    <div className="alert alert-success" style={{ marginTop: 8, fontSize: 13 }}>
                      Счёт создан. <a href="/invoices" style={{ textDecoration: 'underline' }}>Перейти к счетам</a>
                    </div>
                  )}
                  {invoiceFromActError && (
                    <div className="alert alert-error" style={{ marginTop: 8, fontSize: 13 }}>
                      {invoiceFromActError}
                    </div>
                  )}
                </div>
              ) : (
                !showWorkActForm && (
                  <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                    Акт не создан
                  </p>
                )
              )}
            </div>
          </div>

          {/* Attachments */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header">
              <h3>Вложения</h3>
              <label className="btn btn-secondary btn-sm" style={{ cursor: 'pointer' }}>
                + Добавить файл
                <input
                  type="file"
                  style={{ display: 'none' }}
                  onChange={handleFileUpload}
                />
              </label>
            </div>
            <div className="card-body">
              {uploadAttachment.isPending && (
                <div style={{ marginBottom: 8, color: 'var(--text-muted)', fontSize: 13 }}>
                  Загрузка...
                </div>
              )}
              {attachments && attachments.length > 0 ? (
                <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {attachments.map(att => {
                    const handleOpen = async (e: React.MouseEvent) => {
                      e.preventDefault()
                      const tok = localStorage.getItem('token')
                      try {
                        const res = await fetch(att.file_url, {
                          headers: tok ? { Authorization: `Bearer ${tok}` } : {}
                        })
                        if (!res.ok) throw new Error('fetch failed')
                        const blob = await res.blob()
                        const url = URL.createObjectURL(blob)
                        window.open(url, '_blank')
                        setTimeout(() => URL.revokeObjectURL(url), 60_000)
                      } catch {
                        alert('Не удалось открыть файл')
                      }
                    }
                    return (
                      <li key={att.id} style={{ fontSize: 13 }}>
                        <a href={att.file_url} onClick={handleOpen} style={{ cursor: 'pointer' }}>
                          📎 {att.filename}
                        </a>
                      </li>
                    )
                  })}
                </ul>
              ) : (
                <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                  Нет вложений
                </p>
              )}
            </div>
          </div>

          {/* Comments */}
          <div className="card">
            <div className="card-header">
              <h3>Комментарии</h3>
            </div>
            <div className="card-body">
              <div className="comment-list">
                {comments && comments.length > 0 ? (
                  comments.map(c => (
                    <div key={c.id} className="comment-item">
                      <div className="comment-avatar">
                        {c.author ? getInitials(c.author.full_name) : '?'}
                      </div>
                      <div className="comment-body">
                        <div className="comment-meta">
                          <span className="comment-author">
                            {c.author?.full_name ?? 'Пользователь'}
                            {c.author?.email && (
                              <span style={{ fontWeight: 400, color: 'var(--text-muted)', marginLeft: 6 }}>
                                {c.author.email}
                              </span>
                            )}
                          </span>
                          {c.is_internal && (
                            <span className="badge badge-assigned" style={{ fontSize: 10 }}>
                              внутренний
                            </span>
                          )}
                          <span>
                            {format(parseISO(c.created_at), 'dd.MM.yyyy HH:mm', { locale: ru })}
                          </span>
                        </div>
                        <div className="comment-text">{c.text}</div>
                      </div>
                    </div>
                  ))
                ) : (
                  <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                    Комментариев пока нет
                  </p>
                )}
              </div>

              {/* Add comment form */}
              <div style={{ borderTop: '1px solid var(--border)', paddingTop: 16 }}>
                <textarea
                  className="form-textarea"
                  placeholder="Добавить комментарий..."
                  value={commentText}
                  onChange={e => setCommentText(e.target.value)}
                  style={{ marginBottom: 8 }}
                />
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 10,
                  }}
                >
                  {!isClientUser ? (
                    <label
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        fontSize: 13,
                        color: 'var(--text-muted)',
                        cursor: 'pointer',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={isInternal}
                        onChange={e => setIsInternal(e.target.checked)}
                      />
                      Внутренний комментарий
                    </label>
                  ) : (
                    <span />
                  )}
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={handleAddComment}
                    disabled={!commentText.trim() || addComment.isPending}
                  >
                    {addComment.isPending ? 'Отправка...' : 'Отправить'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right column: actions */}
        <div>
          {/* Status change */}
          {transitions.length > 0 && (
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="card-header">
                <h3>Изменить статус</h3>
              </div>
              <div className="card-body">
                <div
                  style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
                >
                  {transitions.map(s => (
                    <button
                      key={s}
                      className="btn btn-secondary"
                      onClick={() => handleStatusChange(s)}
                      disabled={statusMutation.isPending}
                    >
                      → {getTransitionLabel(s)}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Assign engineer */}
          {canAssign && (
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="card-header">
                <h3>Назначить инженера</h3>
              </div>
              <div className="card-body">
                <div className="form-group" style={{ marginBottom: 10 }}>
                  <select
                    className="form-select"
                    value={selectedEngineer}
                    onChange={e => {
                      setSelectedEngineer(e.target.value)
                      if (e.target.value) setAssignError(null)
                    }}
                  >
                    <option value="">— Выберите инженера —</option>
                    {engineers.map(eng => (
                      <option key={eng.id} value={eng.id}>
                        {eng.full_name}
                      </option>
                    ))}
                  </select>
                </div>
                {assignError && (
                  <div style={{ color: 'var(--color-danger, #e53e3e)', fontSize: 13, marginBottom: 8 }}>
                    {assignError}
                  </div>
                )}
                <button
                  className="btn btn-primary"
                  style={{ width: '100%' }}
                  onClick={handleAssign}
                  disabled={assignMutation.isPending}
                >
                  {assignMutation.isPending ? 'Назначение...' : 'Назначить'}
                </button>
              </div>
            </div>
          )}

          {/* Ticket meta */}
          <div className="card">
            <div className="card-header">
              <h3>Детали</h3>
            </div>
            <div className="card-body">
              <ul className="info-list">
                <li>
                  <span className="info-list-label">Приоритет</span>
                  <span className="info-list-value">
                    <PriorityBadge priority={ticket.priority} />
                  </span>
                </li>
                <li>
                  <span className="info-list-label">Шаблон</span>
                  <span className="info-list-value">
                    {ticket.work_template?.name ?? '—'}
                  </span>
                </li>
                <li>
                  <span className="info-list-label">Создал</span>
                  <span className="info-list-value">
                    {ticket.created_by?.full_name ?? '—'}
                  </span>
                </li>
                <li>
                  <span className="info-list-label">Обновлена</span>
                  <span className="info-list-value">
                    {format(parseISO(ticket.updated_at), 'dd.MM.yyyy HH:mm', { locale: ru })}
                  </span>
                </li>
              </ul>

              {statusHistory && statusHistory.length > 0 && (
                <div style={{ marginTop: 20 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>
                    История статусов
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {statusHistory.map(entry => (
                      <div key={entry.id} style={{ fontSize: 12, display: 'flex', flexDirection: 'column', gap: 2, borderLeft: '2px solid var(--border)', paddingLeft: 10 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                          {entry.from_status ? (
                            <>
                              <span style={{ color: 'var(--text-muted)' }}>{STATUS_LABELS[entry.from_status as TicketStatus] ?? entry.from_status}</span>
                              <span style={{ color: 'var(--text-muted)' }}>→</span>
                            </>
                          ) : null}
                          <span style={{ fontWeight: 600 }}>{STATUS_LABELS[entry.to_status as TicketStatus] ?? entry.to_status}</span>
                        </div>
                        <div style={{ color: 'var(--text-muted)', display: 'flex', gap: 6 }}>
                          <span>{format(parseISO(entry.changed_at), 'dd.MM.yyyy HH:mm', { locale: ru })}</span>
                          {entry.changer && <span>· {entry.changer.full_name}</span>}
                        </div>
                        {entry.comment && (
                          <div style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>{entry.comment}</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* INVOICE_PAID_MISMATCH dialog */}
      {paidMismatch && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
        }}>
          <div style={{
            background: 'var(--surface)', borderRadius: 8, padding: 24,
            maxWidth: 480, width: '90%', boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
          }}>
            <h3 style={{ margin: '0 0 12px', color: 'var(--text-primary)' }}>Внимание: оплаченный счёт</h3>
            <p style={{ color: 'var(--text-secondary)', margin: '0 0 16px' }}>
              Сумма акта (<strong>{paidMismatch.actTotal} {currency.currency_code}</strong>) отличается от суммы
              уже оплаченного счёта (<strong>{paidMismatch.invoiceTotal} {currency.currency_code}</strong>).
            </p>
            <p style={{ color: 'var(--text-secondary)', margin: '0 0 20px' }}>
              Счёт не будет изменён. Сохранить акт с новыми данными?
            </p>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setPaidMismatch(null)}
              >
                Отмена
              </button>
              <button
                className="btn btn-danger"
                onClick={handleForceSaveAct}
                disabled={updateWorkAct.isPending}
              >
                {updateWorkAct.isPending ? 'Сохранение...' : 'Сохранить принудительно'}
              </button>
            </div>
          </div>
        </div>
      )}

      <div style={{ marginTop: 24 }}>
        <button className="btn btn-secondary btn-sm" onClick={() => navigate(-1)}>
          ← Назад
        </button>
      </div>
    </>
  )
}
