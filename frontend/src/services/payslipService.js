import api from './api';

export const payslipService = {
  getPayslips: async () => {
    const response = await api.get('/api/payslips');
    return response.data;
  },

  getPayslip: async (id) => {
    const response = await api.get(`/api/payslips/${id}`);
    return response.data;
  },

  downloadPayslipPdf: async (id, fallbackName = 'Payslip.pdf') => {
    const response = await api.get(`/api/payslips/${id}/download`, {
      responseType: 'blob',
    });

    // Create a temporary anchor element to trigger download in browser
    const blob = new Blob([response.data], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;

    // Extract filename from header if present
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

export default payslipService;
