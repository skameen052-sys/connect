import api from './api';

export const loanService = {
  getLoans: async () => {
    const response = await api.get('/api/loans');
    return response.data;
  },

  applyLoan: async (payload) => {
    const response = await api.post('/api/loans/apply', payload);
    return response.data;
  },

  updateStatus: async (loanId, payload) => {
    const response = await api.patch(`/api/loans/${loanId}/status`, payload);
    return response.data;
  },

  getSchedule: async (loanId) => {
    const response = await api.get(`/api/loans/${loanId}/schedule`);
    return response.data;
  },
};

export default loanService;
