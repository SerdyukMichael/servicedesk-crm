import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { formatDistanceToNow, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'
import {
  useNotifications,
  useMarkRead,
  useMarkAllRead,
  useNotificationSettings,
  useUpdateNotificationSetting,
} from '../hooks/useNotifications'
import type { NotificationChannel } from '../api/types'

type Tab = 'list' | 'settings'

const EVENT_TYPE_LABELS: Record<string, string> = {
  ticket_created: 'Создание заявки',
  ticket_assigned: 'Назначение инженера',
  ticket_assigned_to_me: 'Заявка назначена мне',
  ticket_status_changed: 'Изменение статуса заявки',
  ticket_closed: 'Заявка закрыта',
  ticket_comment: 'Новый комментарий',
  ticket_comment_added: 'Новый комментарий',
  new_comment_on_my_ticket: 'Комментарий к моей заявке',
  sla_warning: 'Предупреждение SLA',
  sla_breach: 'Нарушение SLA',
  sla_violation: 'Нарушение SLA',
  ticket_sla_warning: 'Предупреждение SLA',
  work_act_created: 'Создание акта',
  work_act_signed: 'Подписание акта',
  invoice_sent: 'Счёт отправлен',
  payment_due: 'Оплата просрочена',
  part_low_stock: 'Мало запчастей',
  maintenance_due: 'Плановое ТО',
  warranty_expiring: 'Истекает гарантия',
}

const CHANNEL_LABELS: Record<NotificationChannel, string> = {
  in_app: 'В приложении',
  email: 'Email',
  telegram: 'Telegram',
}

const CHANNELS: NotificationChannel[] = ['in_app', 'email', 'telegram']

export default function NotificationsPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<Tab>('list')

  const { data: notifData, isLoading } = useNotifications({ size: 50 })
  const { data: settings } = useNotificationSettings()
  const markRead = useMarkRead()
  const markAllRead = useMarkAllRead()
  const updateSetting = useUpdateNotificationSetting()

  const handleClickNotification = (id: number, ticketId?: number) => {
    if (!notifData?.items.find(n => n.id === id)?.is_read) {
      markRead.mutate(id)
    }
    if (ticketId) {
      navigate(`/tickets/${ticketId}`)
    }
  }

  const unreadCount = notifData?.items.filter(n => !n.is_read).length ?? 0

  // Build settings matrix: event_type × channel
  const eventTypes = settings
    ? [...new Set(settings.map(s => s.event_type))]
    : Object.keys(EVENT_TYPE_LABELS)

  const getSetting = (eventType: string, channel: NotificationChannel) =>
    settings?.find(s => s.event_type === eventType && s.channel === channel)

  return (
    <>
      <div className="page-header">
        <h1>
          Уведомления
          {unreadCount > 0 && (
            <span
              className="badge badge-new"
              style={{ marginLeft: 8, verticalAlign: 'middle' }}
            >
              {unreadCount} новых
            </span>
          )}
        </h1>
        {activeTab === 'list' && unreadCount > 0 && (
          <button
            className="btn btn-secondary"
            onClick={() => markAllRead.mutate()}
            disabled={markAllRead.isPending}
          >
            Отметить все прочитанными
          </button>
        )}
      </div>

      <div className="tabs">
        <button
          className={`tab-btn${activeTab === 'list' ? ' active' : ''}`}
          onClick={() => setActiveTab('list')}
        >
          Список
        </button>
        <button
          className={`tab-btn${activeTab === 'settings' ? ' active' : ''}`}
          onClick={() => setActiveTab('settings')}
        >
          Настройки
        </button>
      </div>

      {activeTab === 'list' && (
        <>
          {isLoading && (
            <div className="loading-center">
              <span className="spinner spinner-lg" />
            </div>
          )}

          {notifData && (
            <div className="card">
              {notifData.items.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-state-icon">🔔</div>
                  <p>Нет уведомлений</p>
                </div>
              ) : (
                notifData.items.map(notif => (
                  <div
                    key={notif.id}
                    className={`notification-item${!notif.is_read ? ' unread' : ''}`}
                    onClick={() => handleClickNotification(notif.id, notif.ticket_id)}
                  >
                    {!notif.is_read && <div className="notification-dot" />}
                    {notif.is_read && <div style={{ width: 8 }} />}
                    <div className="notification-content">
                      <div className="notification-title">{notif.title}</div>
                      {notif.body && (
                        <div className="notification-body">{notif.body}</div>
                      )}
                      <div className="notification-time">
                        {formatDistanceToNow(parseISO(notif.created_at), {
                          addSuffix: true,
                          locale: ru,
                        })}
                      </div>
                    </div>
                    {notif.ticket_id && (
                      <div style={{ color: 'var(--primary)', fontSize: 12, flexShrink: 0 }}>
                        →
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </>
      )}

      {activeTab === 'settings' && (
        <div className="card">
          <div className="card-header">
            <h3>Настройки уведомлений</h3>
          </div>
          <div className="card-body" style={{ overflowX: 'auto' }}>
            <table className="settings-table">
              <thead>
                <tr>
                  <th style={{ textAlign: 'left' }}>Событие</th>
                  {CHANNELS.map(ch => (
                    <th key={ch}>{CHANNEL_LABELS[ch]}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {eventTypes.map(eventType => (
                  <tr key={eventType}>
                    <td>{EVENT_TYPE_LABELS[eventType] ?? eventType}</td>
                    {CHANNELS.map(channel => {
                      const setting = getSetting(eventType, channel)
                      const isDisabled = channel === 'in_app'

                      return (
                        <td key={channel}>
                          <input
                            type="checkbox"
                            className="toggle-checkbox"
                            checked={setting?.enabled ?? false}
                            disabled={isDisabled || !setting}
                            onChange={e => {
                              if (setting) {
                                updateSetting.mutate({
                                  event_type: setting.event_type,
                                  channel: setting.channel,
                                  enabled: e.target.checked,
                                })
                              }
                            }}
                          />
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 12 }}>
              * Уведомления «В приложении» всегда включены
            </p>
          </div>
        </div>
      )}
    </>
  )
}
