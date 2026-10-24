import api from './api';

export const payrollService = {
  getRuns: async () => {
    const response = await api.get('/api/payroll/runs');
    return response.data;
  },

  getRunDetails: async (runId) => {
    const response = await api.get(`/api/payroll/runs/${runId}`);
    return response.data;
  },

  calculate: async (payload) => {
    const response = await api.post('/api/payroll/calculate', payload);
    return response.data;
  },

  reviewRun: async (runId, notes = '') => {
    const response = await api.post(`/api/payroll/runs/${runId}/review`, { notes });
    return response.data;
  },

  approveRun: async (runId, notes = '') => {
    const response = await api.post(`/api/payroll/runs/${runId}/approve`, { notes });
    return response.data;
  },

  finalizeRun: async (runId, notes = '') => {
    const response = await api.post(`/api/payroll/runs/${runId}/finalize`, { notes });
    return response.data;
  },

  getExceptions: async (runId) => {
    const response = await api.get(`/api/payroll/runs/${runId}/exceptions`);
    return response.data;
  },

  deleteRun: async (runId) => {
    const response = await api.delete(`/api/payroll/runs/${runId}`);
    return response.data;
  },

  // Salary Structures
  getSalaryStructures: async () => {
    const response = await api.get('/api/salary-structures');
    return response.data;
  },

  getEmployeeSalaryStructure: async (employeeId) => {
    const response = await api.get(`/api/salary-structures/${employeeId}`);
    return response.data;
  },

  saveSalaryStructure: async (payload) => {
    const response = await api.post('/api/salary-structures', payload);
    return response.data;
  },

  getSalaryHistory: async (employeeId) => {
    const response = await api.get(`/api/salary-structures/${employeeId}/history`);
    return response.data;
  },
};

export default payrollService;
