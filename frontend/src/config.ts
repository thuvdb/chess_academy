/**
 * CAMS Frontend Central Configuration.
 * Tách các giá trị môi trường và hằng số UI, cung cấp fallback an toàn theo cùng Origin.
 */

// Lấy thông tin location an toàn (hỗ trợ cả môi trường browser lẫn SSR / testing)
const getSafeLocation = () => {
  if (typeof window !== 'undefined' && window.location) {
    const isHttps = window.location.protocol === 'https:';
    const wsProto = isHttps ? 'wss:' : 'ws:';
    const host = window.location.host;
    return {
      protocol: window.location.protocol,
      host,
      origin: window.location.origin,
      defaultWsUrl: `${wsProto}//${host}/ws`,
    };
  }
  return {
    protocol: 'http:',
    host: 'localhost:3000',
    origin: 'http://localhost:3000',
    defaultWsUrl: 'ws://localhost:3000/ws',
  };
};

const loc = getSafeLocation();

// API Base URL: Đọc từ VITE_API_BASE_URL (hoặc fallback VITE_API_URL cũ), mặc định fallback là '/api'
export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  '/api';

// WebSocket Base URL: Đọc từ VITE_WS_BASE_URL, mặc định fallback là `${protocol}//${host}/ws`
export const WS_BASE_URL: string =
  import.meta.env.VITE_WS_BASE_URL ||
  loc.defaultWsUrl;

// Hằng số UI mặc định
export const DEFAULT_TIMEZONE: string =
  import.meta.env.VITE_DEFAULT_TIMEZONE || 'Asia/Ho_Chi_Minh';

export const DEFAULT_PAGE_SIZE: number = Number(
  import.meta.env.VITE_PAGE_SIZE || 20
);

/**
 * Xây dựng URL WebSocket cho màn hình thi đấu trực tiếp (Live Game).
 * Tự động chuyển đổi giao thức wss/ws theo đúng domain hoặc endpoint đã cấu hình.
 */
export const getGameWebSocketUrl = (gameId: string, token: string): string => {
  let base = WS_BASE_URL;

  // Nếu WS_BASE_URL chưa được khai báo riêng mà API_BASE_URL là URL tuyệt đối (http/https):
  if (!import.meta.env.VITE_WS_BASE_URL && API_BASE_URL.startsWith('http')) {
    const wsProto = API_BASE_URL.startsWith('https') ? 'wss:' : 'ws:';
    const cleanApi = API_BASE_URL.replace(/^https?:\/\//, '').replace(/\/api\/?$/, '');
    base = `${wsProto}//${cleanApi}/ws`;
  }

  const cleanBase = base.replace(/\/+$/, '');
  return `${cleanBase}/game/${gameId}?token=${encodeURIComponent(token)}`;
};

/**
 * Xử lý đường dẫn file / avatar / static media:
 * Nếu là đường dẫn tương đối (ví dụ /static/avatars/...), tự động phân giải hợp lệ theo API_BASE_URL hoặc Origin.
 */
export const resolveMediaUrl = (url: string | null | undefined): string => {
  if (!url) return '';
  if (
    url.startsWith('http://') ||
    url.startsWith('https://') ||
    url.startsWith('blob:') ||
    url.startsWith('data:')
  ) {
    return url;
  }
  if (API_BASE_URL.startsWith('http')) {
    try {
      const parsed = new URL(API_BASE_URL);
      return `${parsed.origin}${url.startsWith('/') ? '' : '/'}${url}`;
    } catch {
      // fallback
    }
  }
  return url;
};
