import api from './api';

/**
 * AttendanceService - Check-in, Check-out, and Attendance Logs
 * Connected to FastAPI backend and PostgreSQL persistence
 */
export const attendanceService = {
  /**
   * Get attendance records with optional filters (Search, workMode, status, date)
   */
  async getRecords(params = {}) {
    try {
      const response = await api.get('/api/attendance/records', { params });
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || error.response?.data?.message || 'Could not fetch attendance records');
    }
  },

  /**
   * Get personal attendance records for the logged-in employee
   */
  async getMyRecords(params = {}) {
    try {
      const response = await api.get('/api/attendance/me', { params });
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || error.response?.data?.message || 'Could not fetch personal attendance records');
    }
  },

  /**
   * Get today's punch-in and clock status for current employee
   */
  async getTodayStatus() {
    try {
      const response = await api.get('/api/attendance/today-status');
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || error.response?.data?.message || 'Could not fetch today attendance status');
    }
  },

  /**
   * Calculate distance between two coordinates in meters using Haversine formula (frontend mirror)
   */
  calculateHaversineDistance(lat1, lon1, lat2, lon2) {
    const R = 6371000; // meters
    const toRad = (deg) => (deg * Math.PI) / 180;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  },

  /**
   * Get authoritative office coordinates and geofence parameters from backend
   */
  async getOfficeLocation() {
    try {
      const response = await api.get('/api/attendance/office-location');
      return response.data;
    } catch (error) {
      console.warn('Could not fetch office location configuration from backend', error);
      // Fallback matching default configuration
      return {
        latitude: 12.9104417,
        longitude: 77.6442435,
        radiusMeters: 250,
        maxAccuracyMeters: 100,
        timezone: 'Asia/Kolkata',
      };
    }
  },

  /**
   * Pre-validate GPS coordinates and work mode on backend
   */
  async validateLocation({ latitude, longitude, accuracy, workMode }) {
    try {
      const response = await api.post('/api/attendance/validate-location', {
        latitude,
        longitude,
        accuracy,
        workMode,
      });
      return response.data;
    } catch (error) {
      const errData = error.response?.data;
      const code = errData?.code || (errData?.detail && typeof errData.detail === 'object' ? errData.detail.code : null);
      const message =
        (errData?.detail && typeof errData.detail === 'object' ? errData.detail.message : null) ||
        errData?.message ||
        errData?.detail ||
        error.message ||
        'Location verification failed';
      const customErr = new Error(message);
      customErr.code = code;
      customErr.status = error.response?.status;
      customErr.data = errData;
      throw customErr;
    }
  },

  /**
   * Check in employee with photo and GPS location coordinates
   */
  async checkIn(payload = {}) {
    try {
      let data;
      if (payload instanceof FormData) {
        data = payload;
      } else {
        const formData = new FormData();
        const photo = payload.photo || payload.file || payload.photoBlob || payload.capturedBlob;
        if (photo) {
          if (photo instanceof Blob || photo instanceof File) {
            formData.append('photo', photo, 'check_in_selfie.jpg');
          } else {
            formData.append('photo', photo);
          }
        }
        if (payload.latitude !== undefined && payload.latitude !== null) {
          formData.append('latitude', payload.latitude);
        }
        if (payload.longitude !== undefined && payload.longitude !== null) {
          formData.append('longitude', payload.longitude);
        }
        if (payload.accuracy !== undefined && payload.accuracy !== null) {
          formData.append('accuracy', payload.accuracy);
        }
        if (payload.workMode) formData.append('workMode', payload.workMode);
        if (payload.timestamp) formData.append('timestamp', payload.timestamp);
        if (payload.employeeId) formData.append('employeeId', payload.employeeId);
        data = formData;
      }
      const response = await api.post('/api/attendance/check-in', data);
      return response.data;
    } catch (error) {
      const errData = error.response?.data;
      const code = errData?.code || (errData?.detail && typeof errData.detail === 'object' ? errData.detail.code : null);
      const message =
        (errData?.detail && typeof errData.detail === 'object' ? errData.detail.message : null) ||
        errData?.message ||
        errData?.detail ||
        error.message ||
        'Check-in failed';
      const customErr = new Error(message);
      customErr.code = code;
      customErr.data = errData;
      throw customErr;
    }
  },

  /**
   * Submit mandatory late check-in reason
   */
  async submitLateReason({ attendanceId, reason, date } = {}) {
    try {
      const response = await api.post('/api/attendance/late-reason', {
        attendanceId,
        reason: (reason || '').trim(),
        date,
      });
      return response.data;
    } catch (error) {
      const msg = error.response?.data?.detail || error.response?.data?.message || error.message || 'Failed to submit late check-in reason.';
      throw new Error(msg);
    }
  },

  /**
   * Check out employee and lock daily attendance
   */
  async checkOut({ employeeId } = {}) {
    try {
      const payload = {};
      if (employeeId) {
        payload.employeeId = employeeId;
      }
      const response = await api.post('/api/attendance/check-out', payload);
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || error.response?.data?.message || 'Check-out failed');
    }
  },

  /**
   * Get attendance photo binary blob securely using authenticated API client
   */
  async getPhotoBlob(attendanceId, photoType = 'check-in') {
    try {
      const response = await api.get(`/api/attendance/${attendanceId}/photo/${photoType}`, {
        responseType: 'blob',
      });
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Could not load attendance photo');
    }
  },

  /**
   * Edit attendance record (Admin only)
   */
  async updateRecord(recordId, data) {
    try {
      const response = await api.patch(`/api/attendance/${recordId}`, data);
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || error.response?.data?.message || 'Failed to update attendance record');
    }
  },

  /**
   * Get attendance summary counts
   */
  async getSummary() {
    try {
      const response = await api.get('/api/attendance/summary');
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || error.response?.data?.message || 'Could not fetch attendance summary');
    }
  },
};

export default attendanceService;
