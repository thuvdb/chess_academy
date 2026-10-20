import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const isProduction = import.meta.env.PROD;
const defaultBaseURL = isProduction ? '/api' : 'http://localhost:8000/api';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || defaultBaseURL,
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
});

// Attach Bearer token on every request
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

// Auto-logout on 401 & handle network timeouts gracefully
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = '/login';
      return Promise.reject(err);
    }

    if (err.code === 'ECONNABORTED' || !err.response) {
      const customMessage = 'Kết nối máy chủ bị gián đoạn hoặc phản hồi quá chậm (timeout). Vui lòng thử lại.';
      if (err.response) {
        err.response.data = { detail: customMessage, ...err.response.data };
      } else {
        err.response = {
          data: { detail: customMessage },
          status: 504,
          statusText: 'Gateway Timeout',
          headers: {},
          config: err.config,
        };
      }
    }

    return Promise.reject(err);
  }
);

export default api;
