import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { format, isPast, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'
import {
  useTicket,
  useTicketComments,
  useTicketAttachments,
  useWorkAct,
  useAddComment,
  useAssignEngineer,
  useChangeTicketStatus,
  useCreateWorkAct,
  useSignWorkAct,
  useUploadAttachment,
} from '../hooks/useTickets'
import { useUsers } from '../hooks/useUsers'
import { useAuth } from '../context/AuthContext'
import StatusBadge from '../components/StatusBadge'
import PriorityBadge from '../components/PriorityBadge'
import type { TicketStatus } from '../api/types'

const STATUS_TRANSITIONS: Record<TicketStatus, TicketStatus[]> = {
  new: ['assigned', 'cancelled'],
  assigned: ['in_progress', 'cancelled'],
  in_progress: ['waiting_part', 'on_review', 'cancelled'],
  waiting_part: ['in_progress', 'cancelled'],
  on_review: ['completed', 'in_progress'],
  completed: ['closed'],
  closed: [],
  cancelled: [],
}

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

  const { data: ticket, isLoading, isError } = useTicket(ticketId)
  const { data: comments } = useTicketComments(ticketId)
  const { data: attachments } = useTicketAttachments(ticketId)
  const { data: workAct } = useWorkAct(ticketId)
  const { data: usersData } = useUsers({ role: 'engineer', size: 100 })

  const assignMutation = useAssignEngineer(ticketId)
  const statusMutation = useChangeTicketStatus(ticketId)
  const addComment = useAddComment(ticketId)
  const createWorkAct = useCreateWorkAct(ticketId)
  const signWorkAct = useSignWorkAct(ticketId)
  const uploadAttachment = useUploadAttachment(ticketId)

  const [selectedEngineer, setSelectedEngineer] = useState<string>('')
  const [commentText, setCommentText] = useState('')
  const [isInternal, setIsInternal] = useState(false)
  const [workActDesc, setWorkActDesc] = useState('')
  const [workActPerformed, setWorkActPerformed] = useState('')
  const [showWorkActForm, setShowWorkActForm] = useState(false)

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

  const transitions = STATUS_TRANSITIONS[ticket.status] ?? []
  const engineers = usersData?.items ?? []

  const isOverdue =
    ticket.sla_deadline &&
    isPast(parseISO(ticket.sla_deadline)) &&
    !['completed', 'closed', 'cancelled'].includes(ticket.status)

  const canAssign = hasRole('admin', 'svc_mgr')
  const canChangeStatus = hasRole('admin', 'svc_mgr', 'engineer')
  const canCreateAct = hasRole('engineer', 'svc_mgr', 'admin')
  const canSignAct = hasRole('svc_mgr', 'admin')

  const handleAssign = () => {
    if (!selectedEngineer) return
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

  const handleCreateWorkAct = () => {
    createWorkAct.mutate(
      { description: workActDesc, work_performed: workActPerformed },
      { onSuccess: () => setShowWorkActForm(false) }
    )
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
                {ticket.sla_deadline && (
                  <li>
                    <span className="info-list-label">Дедлайн SLA</span>
                    <span
                      className={`info-list-value${isOverdue ? ' sla-overdue' : ''}`}
                    >
                      {format(parseISO(ticket.sla_deadline), 'dd.MM.yyyy HH:mm', { locale: ru })}
                      {isOverdue && ' — просрочено!'}
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
                  onClick={() => setShowWorkActForm(v => !v)}
                >
                  {showWorkActForm ? 'Отмена' : '+ Создать акт'}
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
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={handleCreateWorkAct}
                    disabled={createWorkAct.isPending}
                  >
                    {createWorkAct.isPending ? 'Создание...' : 'Создать акт'}
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
                      <span className="info-list-label">Подпись инженера</span>
                      <span className="info-list-value">
                        {workAct.signed_by_engineer ? '✓ Подписан' : 'Не подписан'}
                      </span>
                    </li>
                    <li>
                      <span className="info-list-label">Подпись клиента</span>
                      <span className="info-list-value">
                        {workAct.signed_by_client ? '✓ Подписан' : 'Не подписан'}
                      </span>
                    </li>
                  </ul>
                  {workAct.description && (
                    <p style={{ fontSize: 13, marginTop: 12 }}>{workAct.description}</p>
                  )}
                  {canSignAct && !workAct.signed_by_client && (
                    <button
                      className="btn btn-success btn-sm"
                      style={{ marginTop: 12 }}
                      onClick={() => signWorkAct.mutate('client')}
                      disabled={signWorkAct.isPending}
                    >
                      Подписать акт
                    </button>
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
                  {attachments.map(att => (
                    <li key={att.id} style={{ fontSize: 13 }}>
                      <a href={att.file_url} target="_blank" rel="noopener noreferrer">
                        📎 {att.filename}
                      </a>
                    </li>
                  ))}
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
          {canChangeStatus && transitions.length > 0 && (
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
                      → {STATUS_LABELS[s]}
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
                    onChange={e => setSelectedEngineer(e.target.value)}
                  >
                    <option value="">— Выберите инженера —</option>
                    {engineers.map(eng => (
                      <option key={eng.id} value={eng.id}>
                        {eng.full_name}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  className="btn btn-primary"
                  style={{ width: '100%' }}
                  onClick={handleAssign}
                  disabled={!selectedEngineer || assignMutation.isPending}
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
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
