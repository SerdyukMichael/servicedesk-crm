import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../api/endpoints'

export function useParts(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ['parts', params],
    queryFn: () => api.getParts(params),
  })
}

export function usePart(id: number) {
  return useQuery({
    queryKey: ['part', id],
    queryFn: () => api.getPart(id),
    enabled: !!id,
  })
}

export function useCreatePart() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.createPart,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['parts'] }),
  })
}

export function useUpdatePart(id: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof api.updatePart>[1]) =>
      api.updatePart(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['part', id] })
      qc.invalidateQueries({ queryKey: ['parts'] })
    },
  })
}

export function useAdjustQuantity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      delta,
      reason,
    }: {
      id: number
      delta: number
      reason?: string
    }) => api.adjustPartQuantity(id, delta, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['parts'] }),
  })
}
