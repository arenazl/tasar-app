import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8600/api';

export const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('tasar_token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && !window.location.pathname.includes('/login')) {
      localStorage.removeItem('tasar_token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export const API_BASE = API_URL;
