const BASE = process.env.REACT_APP_API_URL || 'http://localhost:5000';

function getToken() {
  return localStorage.getItem('fintrack_token');
}

async function req(method, path, body, isForm = false) {
  const headers = {};
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (!isForm) headers['Content-Type'] = 'application/json';

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: isForm ? body : body ? JSON.stringify(body) : undefined,
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.msg || 'Request failed');
  return data;
}

// Auth
export const signup = (email, password) => req('POST', '/auth/signup', { email, password });
export const login  = (email, password) => req('POST', '/auth/login',  { email, password });

// Transactions
export const getTransactions = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return req('GET', `/transactions${qs ? '?' + qs : ''}`);
};
export const addTransaction    = (data)    => req('POST',   '/transactions',     data);
export const updateTransaction = (id, data) => req('PUT',   `/transactions/${id}`, data);
export const deleteTransaction = (id)      => req('DELETE', `/transactions/${id}`);

// Budget
export const getBudget = (month, year) => req('GET', `/budget?month=${month}&year=${year}`);
export const setBudget = (data)        => req('POST', '/budget', data);

// Analytics
export const getSummary = (month, year) => req('GET', `/analytics/summary?month=${month}&year=${year}`);

// Upload
export const uploadPDF  = (file, bank) => {
  const fd = new FormData();
  fd.append('file', file);
  fd.append('bank', bank);
  return req('POST', '/upload/pdf', fd, true);
};
export const trainModel   = () => req('POST', '/upload/train');
export const getMLMetrics = () => req('GET',  '/upload/metrics');

// Export
export const exportPDF = (month, year) => {
  const token = getToken();
  window.open(`${BASE}/export/pdf?month=${month}&year=${year}&token=${token}`, '_blank');
};
