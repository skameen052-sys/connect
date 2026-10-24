import api from './api';

export const recruitmentService = {
  getJobs: async () => {
    const response = await api.get('/api/recruitment/jobs');
    return response.data;
  },

  createJob: async (payload) => {
    const response = await api.post('/api/recruitment/jobs', payload);
    return response.data;
  },

  getCandidates: async (jobId = null) => {
    const url = jobId ? `/api/recruitment/candidates?job_id=${jobId}` : '/api/recruitment/candidates';
    const response = await api.get(url);
    return response.data;
  },

  createCandidate: async (payload) => {
    const response = await api.post('/api/recruitment/candidates', payload);
    return response.data;
  },

  updateCandidateStage: async (candidateId, payload) => {
    const response = await api.patch(`/api/recruitment/candidates/${candidateId}/stage`, payload);
    return response.data;
  },

  convertToEmployee: async (candidateId, payload) => {
    const response = await api.post(`/api/recruitment/candidates/${candidateId}/convert-to-employee`, payload);
    return response.data;
  },
};

export default recruitmentService;
