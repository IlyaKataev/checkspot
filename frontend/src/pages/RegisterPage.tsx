import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { UserPlus } from 'lucide-react';
import { authApi } from '../api/campaigns';
import { useAuthStore } from '../store/auth';

export function RegisterPage() {
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const [form, setForm] = useState({
    email: '',
    password: '',
    name: '',
    company_name: '',
    phone: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await authApi.register(form);
      login(data.access_token, data.user_id, data.name);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка регистрации');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0088cc] to-[#006699] flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-8">
        <div className="text-center mb-6">
          <div className="text-4xl mb-3">📍</div>
          <h1 className="text-2xl font-bold text-gray-900">Регистрация</h1>
          <p className="text-gray-500 text-sm mt-1">CheckSpot для бизнеса</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {[
            { key: 'name', label: 'Ваше имя', placeholder: 'Иван Иванов', type: 'text' },
            { key: 'company_name', label: 'Компания', placeholder: 'ООО Ромашка', type: 'text' },
            { key: 'phone', label: 'Телефон', placeholder: '+79991234567', type: 'tel' },
            { key: 'email', label: 'Email', placeholder: 'ivan@company.com', type: 'email' },
            { key: 'password', label: 'Пароль', placeholder: '••••••••', type: 'password' },
          ].map(({ key, label, placeholder, type }) => (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
              <input
                type={type}
                placeholder={placeholder}
                value={form[key as keyof typeof form]}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                required={key !== 'company_name' && key !== 'phone'}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0088cc]"
              />
            </div>
          ))}

          {error && <p className="text-red-500 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#0088cc] hover:bg-[#0077b3] text-white font-medium py-2.5 rounded-lg flex items-center justify-center gap-2 disabled:opacity-60"
          >
            <UserPlus className="w-4 h-4" />
            {loading ? 'Регистрируем...' : 'Зарегистрироваться'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-6">
          Уже есть аккаунт?{' '}
          <Link to="/login" className="text-[#0088cc] hover:underline">
            Войти
          </Link>
        </p>
      </div>
    </div>
  );
}
