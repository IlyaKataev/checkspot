import { api } from './client';

export interface Campaign {
  id: number;
  name: string;
  city: string;
  category: string;
  description: string | null;
  price_per_task: number;
  status: 'draft' | 'active' | 'completed';
  created_at: string;
  published_at: string | null;
  total_tasks: number;
  completed_tasks: number;
  pending_tasks: number;
  in_progress_tasks: number;
  rejected_tasks: number;
}

export interface TaskReport {
  id: number;
  task_id: number;
  address: string;
  status: 'available' | 'in_progress' | 'pending_review' | 'completed' | 'rejected';
  photo_url: string | null;
  photo_taken_at: string | null;
  check_result: Record<string, unknown> | null;
  client_confirmed: boolean | null;
  rejection_reason: string | null;
  executor_phone: string | null;
  created_at: string;
}

export const campaignsApi = {
  list: () => api.get<Campaign[]>('/campaigns').then((r) => r.data),
  get: (id: number) => api.get<Campaign>(`/campaigns/${id}`).then((r) => r.data),
  create: (data: {
    name: string;
    city: string;
    category: string;
    description?: string;
    price_per_task: number;
    addresses: string[];
  }) => api.post<Campaign>('/campaigns', data).then((r) => r.data),
  publish: (id: number) => api.post(`/campaigns/${id}/publish`).then((r) => r.data),
  reports: (id: number) =>
    api.get<TaskReport[]>(`/tasks/campaign/${id}/reports`).then((r) => r.data),
  moderate: (taskId: number, approved: boolean, rejectionReason?: string) => {
    const form = new FormData();
    form.append('approved', String(approved));
    if (rejectionReason) form.append('rejection_reason', rejectionReason);
    return api.post(`/tasks/${taskId}/moderate`, form).then((r) => r.data);
  },
};

export const authApi = {
  login: (email: string, password: string) =>
    api.post<{ access_token: string; user_id: number; name: string }>(
      '/auth/login',
      { email, password }
    ).then((r) => r.data),
  register: (data: {
    email: string;
    password: string;
    name: string;
    company_name?: string;
    phone?: string;
  }) =>
    api.post<{ access_token: string; user_id: number; name: string }>(
      '/auth/register',
      data
    ).then((r) => r.data),
};

export const notificationsApi = {
  list: () =>
    api.get<{ id: number; title: string; body: string; is_read: boolean; created_at: string }[]>(
      '/notifications'
    ).then((r) => r.data),
  readAll: () => api.post('/notifications/read-all').then((r) => r.data),
};
