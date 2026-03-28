import type { TicketStatus } from '../api/types'

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

interface StatusBadgeProps {
  status: TicketStatus
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span className={`badge badge-${status}`}>
      {STATUS_LABELS[status] ?? status}
    </span>
  )
}
