import api from './api';

export const performanceService = {
  getGoals: async (employeeId = null) => {
    const url = employeeId ? `/api/performance/goals?employee_id=${employeeId}` : '/api/performance/goals';
    const response = await api.get(url);
    return response.data;
  },

  createGoal: async (payload) => {
    const response = await api.post('/api/performance/goals', payload);
    return response.data;
  },

  updateGoalProgress: async (goalId, payload) => {
    const response = await api.patch(`/api/performance/goals/${goalId}/progress`, payload);
    return response.data;
  },

  getReviews: async (employeeId = null) => {
    const url = employeeId ? `/api/performance/reviews?employee_id=${employeeId}` : '/api/performance/reviews';
    const response = await api.get(url);
    return response.data;
  },

  submitReview: async (payload) => {
    const response = await api.post('/api/performance/reviews', payload);
    return response.data;
  },
};

export default performanceService;
