import { useQuery } from '@tanstack/react-query'
import * as api from '../api/endpoints'

export function useAuditLog(params: {
  user_id?: number
  action?: string
  entity_type?: string
  date_from?: string
  date_to?: string
  ip_address?: string
  page?: number
  size?: number
}) {
  return useQuery({
    queryKey: ['audit-log', params],
    queryFn: () => api.getAuditLog(params),
  })
}
