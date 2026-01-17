import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_BASE = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth APIs
export const authAPI = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  register: (data) => api.post('/auth/register', data),
  getMe: () => api.get('/auth/me'),
};

// Parts APIs
export const partsAPI = {
  list: () => api.get('/parts'),
  getStats: () => api.get('/parts/stats'),
  get: (id) => api.get(`/parts/${id}`),
  create: (data) => api.post('/parts', data),
  update: (id, data) => api.put(`/parts/${id}`, data),
  delete: (id) => api.delete(`/parts/${id}`),
  search: (q) => api.get(`/search?q=${encodeURIComponent(q)}`),
  // Child parts
  addChild: (partId, data) => api.post(`/parts/${partId}/children`, data),
  updateChild: (partId, childId, data) => api.put(`/parts/${partId}/children/${childId}`, data),
  deleteChild: (partId, childId) => api.delete(`/parts/${partId}/children/${childId}`),
  duplicateChild: (partId, childId) => api.post(`/parts/${partId}/children/${childId}/duplicate`),
};

// Documents APIs
export const documentsAPI = {
  list: () => api.get('/documents'),
  get: (id) => api.get(`/documents/${id}`),
  upload: (file, parentPartIds = [], childPartIds = []) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('parent_part_ids', JSON.stringify(parentPartIds));
    formData.append('child_part_ids', JSON.stringify(childPartIds));
    return api.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  update: (id, data) => api.put(`/documents/${id}`, data),
  delete: (id) => api.delete(`/documents/${id}`),
  downloadUrl: (id) => `${API_BASE}/documents/${id}/download`,
};

// Import/Export APIs
export const importExportAPI = {
  downloadTemplate: () => `${API_BASE}/export/template`,
  importExcel: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/import/excel', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  exportParts: () => `${API_BASE}/export/parts`,
};

// Suppliers APIs (Admin only)
export const suppliersAPI = {
  list: () => api.get('/suppliers'),
  create: (data) => api.post('/suppliers', data),
  update: (id, data) => api.put(`/suppliers/${id}`, data),
  delete: (id) => api.delete(`/suppliers/${id}`),
};

// Audit Logs APIs (Admin only)
export const auditAPI = {
  list: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.supplier_id) queryParams.append('supplier_id', params.supplier_id);
    if (params.entity_type) queryParams.append('entity_type', params.entity_type);
    if (params.start_date) queryParams.append('start_date', params.start_date);
    if (params.end_date) queryParams.append('end_date', params.end_date);
    if (params.limit) queryParams.append('limit', params.limit);
    return api.get(`/audit-logs?${queryParams.toString()}`);
  },
  exportUrl: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.supplier_id) queryParams.append('supplier_id', params.supplier_id);
    if (params.entity_type) queryParams.append('entity_type', params.entity_type);
    return `${API_BASE}/audit-logs/export?${queryParams.toString()}`;
  },
};

export default api;
