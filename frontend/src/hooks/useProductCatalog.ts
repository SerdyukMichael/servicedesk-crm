import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { productCatalogApi } from '../api/endpoints'
import type { ProductCatalogCreate, ProductCatalogUpdate } from '../api/types'

const QK = 'product-catalog'

export function useProductCatalog(params?: {
  include_inactive?: boolean
  category?: string
  page?: number
  size?: number
}) {
  return useQuery({
    queryKey: [QK, params],
    queryFn: () => productCatalogApi.list(params).then(r => r.data),
  })
}

export function useCreateProductCatalogItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ProductCatalogCreate) =>
      productCatalogApi.create(data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: [QK] }),
  })
}

export function useUpdateProductCatalogItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ProductCatalogUpdate }) =>
      productCatalogApi.update(id, data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: [QK] }),
  })
}

export function useDeleteProductCatalogItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => productCatalogApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: [QK] }),
  })
}
