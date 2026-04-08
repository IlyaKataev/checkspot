import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckCircle, XCircle, Clock, RefreshCw } from 'lucide-react';
import { adminApi, Payout } from '../api/admin';

const tabs = [
  { key: 'pending', label: 'Ожидают' },
  { key: 'completed', label: 'Выплачено' },
  { key: 'failed', label: 'Отклонено' },
];

export function PayoutsPage() {
  const [tab, setTab] = useState<'pending' | 'completed' | 'failed'>('pending');
  const [rejectModal, setRejectModal] = useState<{ id: number } | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const queryClient = useQueryClient();

  const { data: payouts = [], isLoading, refetch } = useQuery({
    queryKey: ['payouts', tab],
    queryFn: () => adminApi.payouts(tab),
  });

  const completeMutation = useMutation({
    mutationFn: adminApi.completePayout,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['payouts'] }),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason?: string }) =>
      adminApi.rejectPayout(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payouts'] });
      setRejectModal(null);
      setRejectReason('');
    },
  });

  const totalPending = payouts.reduce((s, p) => s + p.amount, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Выплаты исполнителям</h2>
          {tab === 'pending' && payouts.length > 0 && (
            <p className="text-sm text-gray-500 mt-0.5">
              {payouts.length} заявок на сумму{' '}
              <span className="font-semibold text-gray-900">{totalPending.toLocaleString()} ₽</span>
            </p>
          )}
        </div>
        <button
          onClick={() => refetch()}
          className="p-2 text-gray-400 hover:text-gray-700"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key as typeof tab)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              tab === t.key
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Загрузка...</div>
      ) : payouts.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <div className="text-4xl mb-3">💸</div>
          <p className="text-gray-500">Нет заявок в этом статусе</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {['Исполнитель', 'Telegram', 'Телефон', 'Сумма', 'Заданий', 'Дата', 'Действия'].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {payouts.map((p) => (
                <PayoutRow
                  key={p.id}
                  payout={p}
                  onComplete={() => completeMutation.mutate(p.id)}
                  onReject={() => setRejectModal({ id: p.id })}
                  loading={completeMutation.isPending || rejectMutation.isPending}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Reject modal */}
      {rejectModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-2xl">
            <h3 className="font-semibold text-gray-900 mb-3">Отклонить выплату</h3>
            <p className="text-sm text-gray-500 mb-3">
              Средства вернутся на баланс исполнителя. Он получит уведомление в Telegram.
            </p>
            <textarea
              rows={2}
              placeholder="Причина (необязательно)"
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-red-400 resize-none"
            />
            <div className="flex gap-2">
              <button
                onClick={() => { setRejectModal(null); setRejectReason(''); }}
                className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-lg text-sm"
              >
                Отмена
              </button>
              <button
                onClick={() =>
                  rejectMutation.mutate({ id: rejectModal.id, reason: rejectReason || undefined })
                }
                disabled={rejectMutation.isPending}
                className="flex-1 bg-red-600 hover:bg-red-700 text-white py-2 rounded-lg text-sm disabled:opacity-60"
              >
                Отклонить
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function PayoutRow({
  payout: p,
  onComplete,
  onReject,
  loading,
}: {
  payout: Payout;
  onComplete: () => void;
  onReject: () => void;
  loading: boolean;
}) {
  const statusIcon = {
    pending: <Clock className="w-4 h-4 text-yellow-500" />,
    completed: <CheckCircle className="w-4 h-4 text-green-500" />,
    failed: <XCircle className="w-4 h-4 text-red-500" />,
  }[p.status];

  const date = p.completed_at || p.created_at;

  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-3 font-medium text-gray-900">
        <div className="flex items-center gap-2">
          {statusIcon}
          {p.executor_name || '—'}
        </div>
      </td>
      <td className="px-4 py-3 text-gray-500">
        {p.executor_tg ? `@${p.executor_tg}` : '—'}
      </td>
      <td className="px-4 py-3 text-gray-900 font-mono">{p.phone || '—'}</td>
      <td className="px-4 py-3 font-semibold text-gray-900">{p.amount.toLocaleString()} ₽</td>
      <td className="px-4 py-3 text-gray-500">{p.completed_tasks}</td>
      <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
        {new Date(date).toLocaleString('ru-RU', {
          day: 'numeric',
          month: 'short',
          hour: '2-digit',
          minute: '2-digit',
        })}
      </td>
      <td className="px-4 py-3">
        {p.status === 'pending' && (
          <div className="flex gap-1.5">
            <button
              onClick={onComplete}
              disabled={loading}
              className="bg-green-100 hover:bg-green-200 text-green-700 px-3 py-1 rounded-lg text-xs font-medium flex items-center gap-1 disabled:opacity-60"
            >
              <CheckCircle className="w-3.5 h-3.5" />
              Выплатить
            </button>
            <button
              onClick={onReject}
              disabled={loading}
              className="bg-red-100 hover:bg-red-200 text-red-700 px-3 py-1 rounded-lg text-xs font-medium flex items-center gap-1 disabled:opacity-60"
            >
              <XCircle className="w-3.5 h-3.5" />
              Отклонить
            </button>
          </div>
        )}
      </td>
    </tr>
  );
}
