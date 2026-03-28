import type { TicketPriority } from '../api/types'

const PRIORITY_LABELS: Record<TicketPriority, string> = {
  critical: 'Критический',
  high: 'Высокий',
  medium: 'Средний',
  low: 'Низкий',
}

interface PriorityBadgeProps {
  priority: TicketPriority
}

export default function PriorityBadge({ priority }: PriorityBadgeProps) {
  return (
    <span className={`badge priority-${priority}`}>
      {PRIORITY_LABELS[priority] ?? priority}
    </span>
  )
}
