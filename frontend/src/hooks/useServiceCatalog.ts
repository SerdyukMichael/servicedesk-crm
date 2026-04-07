import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../api/endpoints'
import type { ServiceCatalogItem } from '../api/types'

export function useServiceCatalog(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ['service-catalog', params],
    queryFn: () => api.getServiceCatalog(params),
  })
}

export function useServiceCatalogItem(id: number) {
  return useQuery({
    queryKey: ['service-catalog-item', id],
    queryFn: () => api.getServiceCatalogItem(id),
    enabled: !!id,
  })
}

export function useCreateServiceCatalogItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<ServiceCatalogItem>) => api.createServiceCatalogItem(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['service-catalog'] }),
  })
}

export function useUpdateServiceCatalogItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<ServiceCatalogItem> }) =>
      api.updateServiceCatalogItem(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['service-catalog'] }),
  })
}

export function useDeleteServiceCatalogItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.deleteServiceCatalogItem(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['service-catalog'] }),
  })
}
