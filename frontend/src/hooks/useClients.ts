import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../api/endpoints'

export function useClients(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ['clients', params],
    queryFn: () => api.getClients(params),
  })
}

export function useClient(id: number) {
  return useQuery({
    queryKey: ['client', id],
    queryFn: () => api.getClient(id),
    enabled: !!id,
  })
}

export function useCreateClient() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.createClient,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['clients'] }),
  })
}

export function useUpdateClient(id: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof api.updateClient>[1]) =>
      api.updateClient(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['client', id] })
      qc.invalidateQueries({ queryKey: ['clients'] })
    },
  })
}

export function useClientContacts(clientId: number) {
  return useQuery({
    queryKey: ['client-contacts', clientId],
    queryFn: () => api.getClientContacts(clientId),
    enabled: !!clientId,
  })
}

export function useCreateClientContact(clientId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof api.createClientContact>[1]) =>
      api.createClientContact(clientId, data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['client-contacts', clientId] }),
  })
}
