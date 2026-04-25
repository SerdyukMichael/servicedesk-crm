import { useQuery } from '@tanstack/react-query'
import * as api from '../api/endpoints'

export function useTicketReport(params: {
  date_from: string
  date_to: string
  engineer_id?: number
  client_id?: number
}) {
  return useQuery({
    queryKey: ['ticket-report', params],
    queryFn: () => api.getTicketReport(params),
    enabled: !!params.date_from && !!params.date_to,
  })
}
