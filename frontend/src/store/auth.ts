import { create } from 'zustand';

interface AuthState {
  token: string | null;
  userId: number | null;
  name: string | null;
  login: (token: string, userId: number, name: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('token'),
  userId: null,
  name: localStorage.getItem('user_name'),
  login: (token, userId, name) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user_name', name);
    set({ token, userId, name });
  },
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user_name');
    set({ token: null, userId: null, name: null });
  },
}));
