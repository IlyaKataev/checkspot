import { useState } from 'react';
import { Outlet, useNavigate, Link, useLocation } from 'react-router-dom';
import { Bell, LogOut, Wallet, LayoutGrid } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../store/auth';
import { notificationsApi } from '../api/campaigns';

export function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { name, logout } = useAuthStore();
  const [showNotifs, setShowNotifs] = useState(false);

  const queryClient = useQueryClient();

  const { data: notifications = [] } = useQuery({
    queryKey: ['notifications'],
    queryFn: notificationsApi.list,
    refetchInterval: 30_000,
  });

  const readAllMutation = useMutation({
    mutationFn: notificationsApi.readAll,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  });

  const unread = notifications.filter((n) => !n.is_read).length;

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top bar */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex items-center justify-between h-14">
          <div className="flex items-center gap-6">
            <Link to="/" className="flex items-center gap-2 font-bold text-gray-900">
              <span className="text-xl">📍</span>
              <span>CheckSpot</span>
            </Link>
            <nav className="hidden sm:flex items-center gap-1">
              <Link
                to="/"
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  location.pathname === '/' ? 'bg-gray-100 text-gray-900' : 'text-gray-500 hover:text-gray-900'
                }`}
              >
                Кампании
              </Link>
              <Link
                to="/payouts"
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5 ${
                  location.pathname === '/payouts' ? 'bg-gray-100 text-gray-900' : 'text-gray-500 hover:text-gray-900'
                }`}
              >
                <Wallet className="w-3.5 h-3.5" />
                Выплаты
              </Link>
            </nav>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500 hidden sm:block">{name}</span>

            {/* Notifications */}
            <div className="relative">
              <button
                onClick={() => setShowNotifs(!showNotifs)}
                className="relative p-2 text-gray-500 hover:text-gray-900"
              >
                <Bell className="w-5 h-5" />
                {unread > 0 && (
                  <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 text-white text-[10px] rounded-full flex items-center justify-center font-bold">
                    {unread}
                  </span>
                )}
              </button>

              {showNotifs && (
                <div className="absolute right-0 top-10 w-72 sm:w-80 bg-white border border-gray-200 rounded-xl shadow-xl z-50 overflow-hidden">
                  <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
                    <span className="font-medium text-sm text-gray-900">Уведомления</span>
                    <button
                      onClick={() => {
                        readAllMutation.mutate();
                        setShowNotifs(false);
                      }}
                      className="text-xs text-[#0088cc] hover:underline"
                    >
                      Прочитать все
                    </button>
                  </div>
                  {notifications.length === 0 ? (
                    <div className="px-4 py-8 text-center text-gray-400 text-sm">Нет уведомлений</div>
                  ) : (
                    <div className="max-h-72 overflow-y-auto divide-y divide-gray-50">
                      {notifications.map((n) => (
                        <div key={n.id} className={`px-4 py-3 ${!n.is_read ? 'bg-blue-50' : ''}`}>
                          <p className="text-sm font-medium text-gray-900">{n.title}</p>
                          <p className="text-xs text-gray-500 mt-0.5">{n.body}</p>
                          <p className="text-xs text-gray-400 mt-1">
                            {new Date(n.created_at).toLocaleString('ru-RU', {
                              day: 'numeric',
                              month: 'short',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            <button onClick={handleLogout} className="p-2 text-gray-400 hover:text-gray-700">
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-6 pb-20 sm:pb-6">
        <Outlet />
      </main>

      {/* Mobile bottom nav */}
      <nav className="sm:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 flex z-30">
        <Link
          to="/"
          className={`flex-1 flex flex-col items-center gap-0.5 py-2.5 text-[11px] font-medium ${
            location.pathname === '/' ? 'text-[#0088cc]' : 'text-gray-400'
          }`}
        >
          <LayoutGrid className="w-5 h-5" />
          Кампании
        </Link>
        <Link
          to="/payouts"
          className={`flex-1 flex flex-col items-center gap-0.5 py-2.5 text-[11px] font-medium ${
            location.pathname === '/payouts' ? 'text-[#0088cc]' : 'text-gray-400'
          }`}
        >
          <Wallet className="w-5 h-5" />
          Выплаты
        </Link>
      </nav>
    </div>
  );
}
