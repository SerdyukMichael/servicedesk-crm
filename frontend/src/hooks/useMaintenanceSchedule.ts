import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../api/endpoints'
import type { MaintenanceFrequency } from '../api/types'

export function useMaintenanceSchedule(equipmentId: number) {
  return useQuery({
    queryKey: ['maintenance-schedule', equipmentId],
    queryFn: () => api.getMaintenanceSchedule(equipmentId),
    enabled: !!equipmentId,
  })
}

export function useCreateMaintenanceSchedule(equipmentId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { frequency: MaintenanceFrequency; first_date: string }) =>
      api.createMaintenanceSchedule(equipmentId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['maintenance-schedule', equipmentId] }),
  })
}

export function useUpdateMaintenanceSchedule(equipmentId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { frequency?: MaintenanceFrequency; first_date?: string; next_date?: string; is_active?: boolean }) =>
      api.updateMaintenanceSchedule(equipmentId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['maintenance-schedule', equipmentId] }),
  })
}
