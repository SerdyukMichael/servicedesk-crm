import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../api/endpoints'

export function useEquipment(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ['equipment', params],
    queryFn: () => api.getEquipment(params),
  })
}

export function useEquipmentItem(id: number) {
  return useQuery({
    queryKey: ['equipment-item', id],
    queryFn: () => api.getEquipmentItem(id),
    enabled: !!id,
  })
}

export function useEquipmentModels() {
  return useQuery({
    queryKey: ['equipment-models'],
    queryFn: api.getEquipmentModels,
    staleTime: 60_000,
  })
}

export function useClientEquipment(clientId: number) {
  return useQuery({
    queryKey: ['client-equipment', clientId],
    queryFn: () => api.getClientEquipment(clientId),
    enabled: !!clientId,
  })
}

export function useCreateEquipment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.createEquipment,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['equipment'] }),
  })
}

export function useUpdateEquipment(id: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof api.updateEquipment>[1]) =>
      api.updateEquipment(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['equipment-item', id] })
      qc.invalidateQueries({ queryKey: ['equipment'] })
    },
  })
}
