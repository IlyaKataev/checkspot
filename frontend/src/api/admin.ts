import { api } from './client';

export interface Payout {
  id: number;
  amount: number;
  phone: string | null;
  status: 'pending' | 'completed' | 'failed';
  executor_name: string | null;
  executor_tg: string | null;
  completed_tasks: number;
  created_at: string;
  completed_at: string | null;
}

export const adminApi = {
  payouts: (status = 'pending') =>
    api.get<Payout[]>('/admin/payouts', { params: { status } }).then((r) => r.data),
  completePayout: (id: number) =>
    api.post(`/admin/payouts/${id}/complete`).then((r) => r.data),
  rejectPayout: (id: number, reason?: string) => {
    const form = new FormData();
    if (reason) form.append('reason', reason);
    return api.post(`/admin/payouts/${id}/reject`, form).then((r) => r.data);
  },
};
