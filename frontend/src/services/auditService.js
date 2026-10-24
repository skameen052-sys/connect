import api from './api';

export const auditService = {
  getLogs: async (params = {}) => {
    const query = new URLSearchParams(params).toString();
    const url = query ? `/api/audit/logs?${query}` : '/api/audit/logs';
    const response = await api.get(url);
    return response.data;
  },
};

export default auditService;
