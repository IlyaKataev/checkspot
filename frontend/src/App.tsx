import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuthStore } from './store/auth';
import { Layout } from './components/Layout';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { CampaignsPage } from './pages/CampaignsPage';
import { NewCampaignPage } from './pages/NewCampaignPage';
import { CampaignDetailPage } from './pages/CampaignDetailPage';
import { PayoutsPage } from './pages/PayoutsPage';

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 10_000 } },
});

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/"
            element={
              <RequireAuth>
                <Layout />
              </RequireAuth>
            }
          >
            <Route index element={<CampaignsPage />} />
            <Route path="campaigns/new" element={<NewCampaignPage />} />
            <Route path="campaigns/:id" element={<CampaignDetailPage />} />
            <Route path="payouts" element={<PayoutsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
