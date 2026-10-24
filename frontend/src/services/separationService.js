import api from './api';

export const separationService = {
  getRequests: async () => {
    const response = await api.get('/api/separation/requests');
    return response.data;
  },

  submitResignation: async (payload) => {
    const response = await api.post('/api/separation/submit', payload);
    return response.data;
  },

  approveResignation: async (id, payload) => {
    const response = await api.patch(`/api/separation/${id}/approve`, payload);
    return response.data;
  },

  calculateFnF: async (id, payload) => {
    const response = await api.post(`/api/separation/${id}/calculate-fnf`, payload);
    return response.data;
  },

  downloadStatementPdf: async (id, fallbackName = 'FnF_Statement.pdf') => {
    const response = await api.get(`/api/separation/${id}/statement`, {
      responseType: 'blob',
    });

    const blob = new Blob([response.data], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;

    const disposition = response.headers['content-disposition'];
    let filename = fallbackName;
    if (disposition && disposition.indexOf('filename=') !== -1) {
      const match = disposition.match(/filename="?([^"]+)"?/);
      if (match && match[1]) {
        filename = match[1];
      }
    }

    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
};

export default separationService;
