import axios from 'axios';

const api = axios.create({
  // Use a relative base URL so the Vite dev-server proxy (/api → localhost:8000/api)
  // forwards requests. This keeps all calls same-origin from the browser's perspective,
  // which completely sidesteps CORS pre-flight and cross-origin cookie restrictions.
  baseURL: '/api',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor — attach CSRF token when available.
// With CsrfExemptSessionAuthentication on the backend this header is not
// strictly required, but we send it anyway to stay compatible if the backend
// is ever switched back to standard SessionAuthentication.
api.interceptors.request.use((config) => {
  const csrfToken = document.cookie
    .split('; ')
    .find((r) => r.startsWith('csrftoken='))
    ?.split('=')[1];
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken;
  }
  return config;
});

// Response interceptor
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status;
    // Redirect to login on 401 (not authenticated) but NOT on 403 (forbidden)
    // to avoid infinite redirect loops when backend returns 403 for bad credentials.
    if (status === 401 && window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default api;
