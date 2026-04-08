import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Plus, Eye, Send } from 'lucide-react';
import { campaignsApi, Campaign } from '../api/campaigns';

export function CampaignsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: campaigns = [], isLoading } = useQuery({
    queryKey: ['campaigns'],
    queryFn: campaignsApi.list,
  });

  const publishMutation = useMutation({
    mutationFn: campaignsApi.publish,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaigns'] }),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="text-gray-400">Загрузка...</div>
      </div>
    );
  }

  const totalTasks = campaigns.reduce((s, c) => s + c.total_tasks, 0);
  const totalCompleted = campaigns.reduce((s, c) => s + c.completed_tasks, 0);
  const totalSpent = campaigns.reduce((s, c) => s + c.completed_tasks * c.price_per_task, 0);

  return (
    <div className="space-y-6">
      {/* Stats */}
      {campaigns.length > 0 && (
        <div className="grid grid-cols-2 gap-4">
          {[
            { label: 'Кампаний', value: campaigns.length },
            { label: 'Точек', value: totalTasks },
            { label: 'Выполнено', value: totalCompleted },
            { label: 'Потрачено', value: `${totalSpent.toLocaleString()} ₽` },
          ].map(({ label, value }) => (
            <div key={label} className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-sm text-gray-500">{label}</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">Мои кампании</h2>
        <button
          onClick={() => navigate('/campaigns/new')}
          className="bg-[#0088cc] hover:bg-[#0077b3] text-white text-sm font-medium px-4 py-2 rounded-lg flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Создать
        </button>
      </div>

      {/* List */}
      {campaigns.length === 0 ? (
        <div className="text-center py-20 bg-white rounded-xl border border-gray-200">
          <div className="text-5xl mb-4">📋</div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Нет кампаний</h3>
          <p className="text-gray-500 mb-6">Создайте первую кампанию для аудита полок</p>
          <button
            onClick={() => navigate('/campaigns/new')}
            className="bg-[#0088cc] hover:bg-[#0077b3] text-white text-sm font-medium px-5 py-2.5 rounded-lg"
          >
            Создать кампанию
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {campaigns.map((c) => (
            <CampaignCard
              key={c.id}
              campaign={c}
              onView={() => navigate(`/campaigns/${c.id}`)}
              onPublish={() => publishMutation.mutate(c.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function CampaignCard({
  campaign: c,
  onView,
  onPublish,
}: {
  campaign: Campaign;
  onView: () => void;
  onPublish: () => void;
}) {
  const pct = c.total_tasks > 0 ? Math.round((c.completed_tasks / c.total_tasks) * 100) : 0;
  const statusLabel = { draft: 'Черновик', active: 'Активна', completed: 'Завершена' }[c.status];
  const statusColor = {
    draft: 'bg-gray-100 text-gray-700',
    active: 'bg-blue-100 text-blue-700',
    completed: 'bg-green-100 text-green-700',
  }[c.status];

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-semibold text-gray-900">{c.name}</h3>
          <p className="text-sm text-gray-500 mt-0.5">Категория: {c.category}</p>
        </div>
        <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${statusColor}`}>
          {statusLabel}
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4 text-center">
        {[
          { label: 'Всего', value: c.total_tasks, cls: 'bg-gray-50' },
          { label: 'Выполнено', value: c.completed_tasks, cls: 'bg-green-50 text-green-700' },
          { label: 'В работе', value: c.in_progress_tasks + c.pending_tasks, cls: 'bg-yellow-50 text-yellow-700' },
          { label: 'Осталось', value: c.pending_tasks, cls: 'bg-orange-50 text-orange-700' },
        ].map(({ label, value, cls }) => (
          <div key={label} className={`${cls} rounded-lg p-2`}>
            <div className="text-xl font-bold">{value}</div>
            <div className="text-xs text-gray-500">{label}</div>
          </div>
        ))}
      </div>

      {c.total_tasks > 0 && (
        <div className="mb-4">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>Прогресс</span>
            <span>{pct}%</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-1.5">
            <div
              className="bg-[#0088cc] h-1.5 rounded-full transition-all"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}

      <div className="flex flex-col sm:flex-row sm:items-center justify-between pt-3 border-t border-gray-100 gap-3">
        <span className="text-sm text-gray-500">
          {c.price_per_task} ₽ / точка ·{' '}
          <span className="font-medium text-gray-900">
            {(c.completed_tasks * c.price_per_task).toLocaleString()} ₽ итого
          </span>
        </span>
        <div className="flex gap-2 shrink-0">
          {c.status === 'draft' && c.total_tasks > 0 && (
            <button
              onClick={onPublish}
              className="text-sm bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 rounded-lg flex items-center gap-1.5"
            >
              <Send className="w-3.5 h-3.5" />
              Опубликовать
            </button>
          )}
          <button
            onClick={onView}
            className="text-sm border border-gray-300 hover:border-gray-400 text-gray-700 px-3 py-1.5 rounded-lg flex items-center gap-1.5"
          >
            <Eye className="w-3.5 h-3.5" />
            Отчёт
          </button>
        </div>
      </div>
    </div>
  );
}
