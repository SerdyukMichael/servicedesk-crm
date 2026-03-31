import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../api/endpoints'
import type { TicketStatus } from '../api/types'

export function useTickets(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ['tickets', params],
    queryFn: () => api.getTickets(params),
    refetchInterval: 30_000,
  })
}

export function useTicket(id: number) {
  return useQuery({
    queryKey: ['ticket', id],
    queryFn: () => api.getTicket(id),
    refetchInterval: 30_000,
    enabled: !!id,
  })
}

export function useCreateTicket() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.createTicket,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tickets'] }),
  })
}

export function useUpdateTicket(id: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof api.updateTicket>[1]) =>
      api.updateTicket(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ticket', id] })
      qc.invalidateQueries({ queryKey: ['tickets'] })
    },
  })
}

export function useAssignEngineer(ticketId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (engineerId: number) => api.assignEngineer(ticketId, engineerId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ticket', ticketId] })
      qc.invalidateQueries({ queryKey: ['tickets'] })
      qc.invalidateQueries({ queryKey: ['ticket-status-history', ticketId] })
    },
  })
}

export function useChangeTicketStatus(ticketId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (status: TicketStatus) => api.changeTicketStatus(ticketId, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ticket', ticketId] })
      qc.invalidateQueries({ queryKey: ['tickets'] })
      qc.invalidateQueries({ queryKey: ['ticket-status-history', ticketId] })
    },
  })
}

export function useTicketStatusHistory(ticketId: number) {
  return useQuery({
    queryKey: ['ticket-status-history', ticketId],
    queryFn: () => api.getTicketStatusHistory(ticketId),
    enabled: !!ticketId,
  })
}

export function useTicketComments(ticketId: number) {
  return useQuery({
    queryKey: ['ticket-comments', ticketId],
    queryFn: () => api.getTicketComments(ticketId),
    refetchInterval: 30_000,
    enabled: !!ticketId,
  })
}

export function useAddComment(ticketId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ text, isInternal }: { text: string; isInternal?: boolean }) =>
      api.addTicketComment(ticketId, text, isInternal),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ticket-comments', ticketId] }),
  })
}

export function useTicketAttachments(ticketId: number) {
  return useQuery({
    queryKey: ['ticket-attachments', ticketId],
    queryFn: () => api.getTicketAttachments(ticketId),
    enabled: !!ticketId,
  })
}

export function useUploadAttachment(ticketId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => api.uploadTicketAttachment(ticketId, file),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['ticket-attachments', ticketId] }),
  })
}

export function useWorkAct(ticketId: number) {
  return useQuery({
    queryKey: ['work-act', ticketId],
    queryFn: () => api.getWorkAct(ticketId),
    enabled: !!ticketId,
    retry: false,
  })
}

export function useCreateWorkAct(ticketId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof api.createWorkAct>[1]) =>
      api.createWorkAct(ticketId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-act', ticketId] })
      qc.invalidateQueries({ queryKey: ['ticket', ticketId] })
    },
  })
}

export function useSignWorkAct(ticketId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (role: 'engineer' | 'client') => api.signWorkAct(ticketId, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['work-act', ticketId] }),
  })
}

export function useWorkTemplates() {
  return useQuery({
    queryKey: ['work-templates'],
    queryFn: api.getWorkTemplates,
  })
}

export function useClientTickets(clientId: number) {
  return useQuery({
    queryKey: ['client-tickets', clientId],
    queryFn: () => api.getClientTickets(clientId),
    enabled: !!clientId,
  })
}
