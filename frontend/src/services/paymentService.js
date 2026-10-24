import api from './api';

export const paymentService = {
  getAllPayments: async () => {
    const response = await api.get('/api/payments/all');
    return response.data;
  },

  getPaymentsForRun: async (runId) => {
    const response = await api.get(`/api/payments/runs/${runId}`);
    return response.data;
  },

  exportBankFile: async (runId, fallbackName = 'Bank_Batch_Export.csv') => {
    const response = await api.post(
      '/api/payments/export-bank-file',
      { payroll_run_id: runId },
      { responseType: 'blob' }
    );

    const blob = new Blob([response.data], { type: 'text/csv' });
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

  confirmPayments: async (payload) => {
    const response = await api.post('/api/payments/record-confirmation', payload);
    return response.data;
  },
};

export default paymentService;
