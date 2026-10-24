import api from './api';

export const departmentService = {
  getDepartments: async () => {
    const response = await api.get('/api/departments');
    return response.data;
  },

  createDepartment: async (payload) => {
    const response = await api.post('/api/departments', payload);
    return response.data;
  },

  getDesignations: async (department = null) => {
    const url = department ? `/api/designations?department=${encodeURIComponent(department)}` : '/api/designations';
    const response = await api.get(url);
    return response.data;
  },

  createDesignation: async (payload) => {
    const response = await api.post('/api/designations', payload);
    return response.data;
  },
};

export default departmentService;
