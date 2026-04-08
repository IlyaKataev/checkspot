import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft, Download, RefreshCw, CheckCircle, XCircle, Clock, Eye, Send
} from 'lucide-react';
import { campaignsApi, TaskReport } from '../api/campaigns';

const API_BASE = import.meta.env.VITE_API_URL?.replace('/api', '') || 'http://localhost:8000';

const STATUS_LABEL: Record<string, string> = {
  available: 'Ожидает',
  in_progress: 'В работе',
  pending_review: 'На проверке',
  completed: 'Принято',
  rejected: 'Отклонено',
};

const STATUS_COLOR: Record<string, string> = {
  available: 'bg-gray-100 text-gray-600',
  in_progress: 'bg-blue-100 text-blue-700',
  pending_review: 'bg-yellow-100 text-yellow-700',
  completed: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
};

export function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const campaignId = Number(id);
  const queryClient = useQueryClient();

  const [photoModal, setPhotoModal] = useState<string | null>(null);
  const [rejectModal, setRejectModal] = useState<{ taskId: number } | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  const { data: campaign } = useQuery({
    queryKey: ['campaign', campaignId],
    queryFn: () => campaignsApi.get(campaignId),
  });

  const { data: reports = [], isLoading, refetch } = useQuery({
    queryKey: ['reports', campaignId],
    queryFn: () => campaignsApi.reports(campaignId),
    refetchInterval: 30_000, // обновляем каждые 30 сек
  });

  const publishMutation = useMutation({
    mutationFn: () => campaignsApi.publish(campaignId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign', campaignId] });
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });

  const moderateMutation = useMutation({
    mutationFn: ({ taskId, approved, reason }: { taskId: number; approved: boolean; reason?: string }) =>
      campaignsApi.moderate(taskId, approved, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports', campaignId] });
      queryClient.invalidateQueries({ queryKey: ['campaign', campaignId] });
      setRejectModal(null);
      setRejectReason('');
    },
  });

  const pendingReview = reports.filter((r) => r.status === 'pending_review');

  const exportCSV = () => {
    const rows = [
      ['Адрес', 'Статус', 'Исполнитель', 'Время фото', 'Ссылка на фото'],
      ...reports.map((r) => [
        r.address,
        STATUS_LABEL[r.status] || r.status,
        r.executor_phone || '',
        r.photo_taken_at ? new Date(r.photo_taken_at).toLocaleString('ru-RU') : '',
        r.photo_url ? API_BASE + r.photo_url : '',
      ]),
    ];
    const csv = rows.map((r) => r.map((c) => `"${c}"`).join(',')).join('\n');
    const a = document.createElement('a');
    a.href = 'data:text/csv;charset=utf-8,\uFEFF' + encodeURIComponent(csv);
    a.download = `checkspot_${campaign?.name || 'report'}.csv`;
    a.click();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <button onClick={() => navigate('/')} className="text-gray-400 hover:text-gray-700 mb-2 flex items-center gap-1 text-sm">
            <ArrowLeft className="w-4 h-4" /> Назад
          </button>
          <h2 className="text-xl font-bold text-gray-900">{campaign?.name || '...'}</h2>
          {campaign && (
            <p className="text-sm text-gray-500 mt-0.5">
              Категория: {campaign.category} · {campaign.price_per_task} ₽/точка
            </p>
          )}
        </div>
        <div className="flex gap-2">
          {campaign?.status === 'draft' && campaign.total_tasks > 0 && (
            <button
              onClick={() => publishMutation.mutate()}
              disabled={publishMutation.isPending}
              className="bg-green-600 hover:bg-green-700 text-white text-sm px-3 py-2 rounded-lg flex items-center gap-1.5"
            >
              <Send className="w-4 h-4" />
              Опубликовать
            </button>
          )}
          <button
            onClick={() => refetch()}
            className="border border-gray-300 hover:border-gray-400 text-gray-700 text-sm px-3 py-2 rounded-lg flex items-center gap-1.5"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={exportCSV}
            className="border border-gray-300 hover:border-gray-400 text-gray-700 text-sm px-3 py-2 rounded-lg flex items-center gap-1.5"
          >
            <Download className="w-4 h-4" />
            CSV
          </button>
        </div>
      </div>

      {/* Pending review banner */}
      {pendingReview.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-yellow-800">
            <Clock className="w-5 h-5" />
            <span className="font-medium">
              {pendingReview.length} фото ожидают проверки
            </span>
          </div>
          <span className="text-sm text-yellow-600">Прокрутите таблицу ниже</span>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="text-center py-12 text-gray-400">Загрузка...</div>
        ) : reports.length === 0 ? (
          <div className="text-center py-12 text-gray-400">Нет данных по этой кампании</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['Адрес', 'Статус', 'Фото', 'Исполнитель', 'Время', 'Действия'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {reports.map((report) => (
                  <ReportRow
                    key={report.id}
                    report={report}
                    onViewPhoto={() => setPhotoModal(API_BASE + report.photo_url!)}
                    onApprove={() => moderateMutation.mutate({ taskId: report.task_id, approved: true })}
                    onReject={() => setRejectModal({ taskId: report.task_id })}
                    moderating={moderateMutation.isPending}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Photo modal */}
      {photoModal && (
        <div
          className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
          onClick={() => setPhotoModal(null)}
        >
          <img
            src={photoModal}
            alt="Фото полки"
            className="max-w-2xl max-h-[90vh] rounded-xl object-contain"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}

      {/* Reject modal */}
      {rejectModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-2xl">
            <h3 className="font-semibold text-gray-900 mb-3">Отклонить фото</h3>
            <textarea
              rows={3}
              placeholder="Причина отклонения (необязательно)"
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
                  moderateMutation.mutate({
                    taskId: rejectModal.taskId,
                    approved: false,
                    reason: rejectReason || undefined,
                  })
                }
                disabled={moderateMutation.isPending}
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

function ReportRow({
  report,
  onViewPhoto,
  onApprove,
  onReject,
  moderating,
}: {
  report: TaskReport;
  onViewPhoto: () => void;
  onApprove: () => void;
  onReject: () => void;
  moderating: boolean;
}) {
  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-3 text-gray-900 max-w-48">{report.address}</td>
      <td className="px-4 py-3">
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOR[report.status] || 'bg-gray-100'}`}>
          {STATUS_LABEL[report.status] || report.status}
        </span>
      </td>
      <td className="px-4 py-3">
        {report.photo_url ? (
          <button
            onClick={onViewPhoto}
            className="text-[#0088cc] hover:underline flex items-center gap-1"
          >
            <Eye className="w-3.5 h-3.5" />
            Смотреть
          </button>
        ) : (
          <span className="text-gray-300">—</span>
        )}
      </td>
      <td className="px-4 py-3 text-gray-500">{report.executor_phone || '—'}</td>
      <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
        {report.photo_taken_at
          ? new Date(report.photo_taken_at).toLocaleString('ru-RU', {
              day: 'numeric',
              month: 'short',
              hour: '2-digit',
              minute: '2-digit',
            })
          : '—'}
      </td>
      <td className="px-4 py-3">
        {report.status === 'pending_review' && (
          <div className="flex gap-1.5">
            <button
              onClick={onApprove}
              disabled={moderating}
              className="bg-green-100 hover:bg-green-200 text-green-700 px-2.5 py-1 rounded-lg text-xs font-medium flex items-center gap-1 disabled:opacity-60"
            >
              <CheckCircle className="w-3.5 h-3.5" />
              Принять
            </button>
            <button
              onClick={onReject}
              disabled={moderating}
              className="bg-red-100 hover:bg-red-200 text-red-700 px-2.5 py-1 rounded-lg text-xs font-medium flex items-center gap-1 disabled:opacity-60"
            >
              <XCircle className="w-3.5 h-3.5" />
              Отклонить
            </button>
          </div>
        )}
        {report.status === 'rejected' && report.rejection_reason && (
          <span className="text-xs text-gray-400">{report.rejection_reason}</span>
        )}
      </td>
    </tr>
  );
}
