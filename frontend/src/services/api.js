import axios from 'axios';

/**
 * Arshith Connect - API Service
 * Configured Axios instance ready for future FastAPI backend integration.
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Request Interceptor: Attach Auth Token if present and handle FormData boundary
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('arshith_auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // When sending FormData, delete Content-Type so browser/Axios generates multipart/form-data with exact boundary
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type'];
      delete config.headers['content-type'];
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Uniform error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Optional: Redirect to login or dispatch session timeout
      console.warn('API returned 401 Unauthorized.');
    }
    return Promise.reject(error);
  }
);

export { authService } from './authService';
export { attendanceService } from './attendanceService';
export { leaveService } from './leaveService';
export { holidayService } from './holidayService';
export { meetingService } from './meetingService';
export { announcementService } from './announcementService';
export { employeeService } from './employeeService';
export { reportService } from './reportService';
export { teamService } from './teamService';
export { assignmentService } from './assignmentService';
export { workUpdateService } from './workUpdateService';
export { registrationRequestService } from './registrationRequestService';
export { officeTimingService } from './officeTimingService';
export { dashboardService } from './dashboardService';
export { payrollService } from './payrollService';
export { payslipService } from './payslipService';
export { paymentService } from './paymentService';
export { loanService } from './loanService';
export { separationService } from './separationService';
export { recruitmentService } from './recruitmentService';
export { performanceService } from './performanceService';
export { departmentService } from './departmentService';
export { auditService } from './auditService';
export { settingsService } from './settingsService';

export default api;

