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

export function useEquipmentModels(includeInactive = false) {
  return useQuery({
    queryKey: ['equipment-models', includeInactive],
    queryFn: () => api.getEquipmentModels(includeInactive),
    staleTime: 60_000,
  })
}

export function useCreateEquipmentModel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.createEquipmentModel,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['equipment-models'] }),
  })
}

export function useUpdateEquipmentModel(id: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof api.updateEquipmentModel>[1]) =>
      api.updateEquipmentModel(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['equipment-models'] }),
  })
}

export function useDeactivateEquipmentModel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.deactivateEquipmentModel,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['equipment-models'] }),
  })
}

export function useActivateEquipmentModel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.activateEquipmentModel,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['equipment-models'] }),
  })
}

export function useClientEquipment(clientId: number) {
  return useQuery({
    queryKey: ['client-equipment', clientId],
    queryFn: () => api.getClientEquipment(clientId),
    enabled: !!clientId,
  })
}

export function useEquipmentLookup(serial: string) {
  return useQuery({
    queryKey: ['equipment-lookup', serial],
    queryFn: () => api.lookupEquipment(serial),
    enabled: serial.trim().length >= 3,
    retry: false,
    staleTime: 30_000,
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
