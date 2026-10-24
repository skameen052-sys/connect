import api from './api';

export const settingsService = {
  getSettings: async () => {
    const response = await api.get('/api/settings');
    return response.data;
  },

  updateSettings: async (payload) => {
    const response = await api.put('/api/settings', payload);
    return response.data;
  },
};

export default settingsService;
