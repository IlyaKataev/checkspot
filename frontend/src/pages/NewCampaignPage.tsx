import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Upload, FileSpreadsheet, ArrowLeft } from 'lucide-react';
import { campaignsApi } from '../api/campaigns';

export function NewCampaignPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [form, setForm] = useState({
    name: '',
    city: '',
    category: '',
    description: '',
    price_per_task: 150,
    addressesText: '',
  });
  const [error, setError] = useState('');

  const createMutation = useMutation({
    mutationFn: campaignsApi.create,
    onSuccess: (campaign) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      navigate(`/campaigns/${campaign.id}`);
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Ошибка создания кампании');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const addresses = form.addressesText
      .split('\n')
      .map((a) => a.trim())
      .filter(Boolean);

    if (addresses.length === 0) {
      setError('Добавьте хотя бы один адрес');
      return;
    }

    if (!form.city.trim()) {
      setError('Укажите город');
      return;
    }

    createMutation.mutate({
      name: form.name,
      city: form.city.trim(),
      category: form.category,
      description: form.description || undefined,
      price_per_task: form.price_per_task,
      addresses,
    });
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      // Простой парсинг CSV — первая колонка как адрес
      const lines = text
        .split('\n')
        .slice(1) // пропускаем заголовок
        .map((l) => l.split(',')[0].replace(/"/g, '').trim())
        .filter(Boolean);
      setForm({ ...form, addressesText: lines.join('\n') });
    };
    reader.readAsText(file);
  };

  const downloadTemplate = () => {
    const csv = 'Адрес\n"ул. Ленина, 10"\n"пр. Мира, 45"\n"ул. Пушкина, 23"';
    const a = document.createElement('a');
    a.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv);
    a.download = 'checkspot_template.csv';
    a.click();
  };

  const addresses = form.addressesText
    .split('\n')
    .map((a) => a.trim())
    .filter(Boolean);

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => navigate('/')}
          className="text-gray-400 hover:text-gray-700"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h2 className="text-xl font-bold text-gray-900">Новая кампания</h2>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Название кампании <span className="text-red-500">*</span>
          </label>
          <input
            required
            placeholder="Аудит полок молочных продуктов — Апрель 2026"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0088cc]"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Город <span className="text-red-500">*</span>
          </label>
          <input
            required
            placeholder="Москва"
            value={form.city}
            onChange={(e) => setForm({ ...form, city: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0088cc]"
          />
          <p className="text-xs text-gray-400 mt-1">
            Используется для геокодирования адресов — можно вводить улицу без города
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Категория товаров <span className="text-red-500">*</span>
          </label>
          <input
            required
            placeholder="Молочные продукты"
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0088cc]"
          />
          <p className="text-xs text-gray-400 mt-1">
            Что именно нужно сфотографировать
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Дополнительная инструкция
          </label>
          <textarea
            rows={2}
            placeholder="Сфотографируйте полку с молоком, видно все этикетки..."
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0088cc] resize-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Оплата за точку (₽) <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            min={50}
            max={2000}
            required
            value={form.price_per_task}
            onChange={(e) => setForm({ ...form, price_per_task: Number(e.target.value) })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0088cc]"
          />
          <p className="text-xs text-gray-400 mt-1">Рекомендуем 150–300 ₽</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Адреса магазинов <span className="text-red-500">*</span>
          </label>
          <div className="flex gap-2 mb-2">
            <input type="file" accept=".csv" id="csv-upload" onChange={handleFileUpload} className="hidden" />
            <button
              type="button"
              onClick={() => document.getElementById('csv-upload')?.click()}
              className="text-sm border border-gray-300 hover:border-gray-400 px-3 py-1.5 rounded-lg flex items-center gap-1.5 text-gray-700"
            >
              <Upload className="w-3.5 h-3.5" />
              Загрузить CSV
            </button>
            <button
              type="button"
              onClick={downloadTemplate}
              className="text-sm border border-gray-300 hover:border-gray-400 px-3 py-1.5 rounded-lg flex items-center gap-1.5 text-gray-700"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              Шаблон
            </button>
          </div>
          <textarea
            rows={6}
            placeholder={'ул. Ленина, 10\nпр. Мира, 45\nул. Пушкина, 23'}
            value={form.addressesText}
            onChange={(e) => setForm({ ...form, addressesText: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0088cc] resize-none font-mono"
          />
          {addresses.length > 0 && (
            <p className="text-xs text-gray-400 mt-1">
              {addresses.length} адрес{addresses.length === 1 ? '' : 'ов'} ·{' '}
              {(addresses.length * form.price_per_task).toLocaleString()} ₽ бюджет
            </p>
          )}
        </div>

        <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 text-sm text-blue-800">
          <b>Как это работает:</b>
          <ol className="list-decimal list-inside mt-1 space-y-0.5">
            <li>Кампания создаётся в статусе «Черновик»</li>
            <li>После публикации задания появятся у исполнителей в боте</li>
            <li>Исполнители делают фото и отправляют на проверку</li>
            <li>Вы проверяете фото и одобряете или отклоняете</li>
          </ol>
        </div>

        {error && <p className="text-red-500 text-sm">{error}</p>}

        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="flex-1 border border-gray-300 hover:border-gray-400 text-gray-700 font-medium py-2.5 rounded-lg text-sm"
          >
            Отмена
          </button>
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="flex-1 bg-[#0088cc] hover:bg-[#0077b3] text-white font-medium py-2.5 rounded-lg text-sm disabled:opacity-60"
          >
            {createMutation.isPending ? 'Создаём...' : 'Создать кампанию'}
          </button>
        </div>
      </form>
    </div>
  );
}
