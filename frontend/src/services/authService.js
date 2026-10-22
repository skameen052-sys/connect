import api from './api';

/**
 * AuthService - Handles Employee & Admin Authentication
 * Connected to FastAPI backend with PostgreSQL persistent authentication.
 */
export const authService = {
  /**
   * Employee Login
   * @param {Object} credentials { email, password }
   */
  async login({ email, password }) {
    try {
      try {
        const { loginWithFirebase } = await import('../firebase/auth');
        await loginWithFirebase(email, password);
      } catch (fbErr) {
        // Firebase client sign-in note (backend is authoritative)
      }

      const response = await api.post('/api/auth/login', {
        email: email.trim(),
        password,
      });

      const { access_token, role, user } = response.data;
      if (role !== 'employee') {
        throw new Error('Admin credentials cannot be used to log in through Employee Login. Please use the Admin Login page.');
      }
      if (access_token) {
        localStorage.setItem('arshith_auth_token', access_token);
        localStorage.setItem('arshith_role', 'employee');
        localStorage.setItem('arshith_user', JSON.stringify(user));
      }
      return { success: true, user };
    } catch (error) {
      localStorage.removeItem('arshith_auth_token');
      localStorage.removeItem('arshith_role');
      localStorage.removeItem('arshith_user');
      let msg = error.response?.data?.detail || error.response?.data?.message;
      if (!error.response) {
        msg = 'Unable to connect to the server. Please try again.';
      } else if (!msg) {
        if (error.response?.status >= 500) {
          msg = 'Unable to connect to the server. Please try again.';
        } else {
          msg = 'Invalid employee email or password.';
        }
      }
      throw new Error(msg);
    }
  },

  /**
   * Admin Login
   * @param {Object} credentials { email, password }
   */
  async adminLogin({ email, password }) {
    try {
      try {
        const { loginWithFirebase } = await import('../firebase/auth');
        await loginWithFirebase(email, password);
      } catch (fbErr) {
        // Firebase client sign-in note (backend is authoritative)
      }

      const response = await api.post('/api/auth/admin-login', {
        email: email.trim(),
        password,
      });

      const { access_token, role, user } = response.data;
      if (role !== 'admin') {
        throw new Error('Employee credentials cannot be used to log in through Admin Login. Please use the Employee Login page.');
      }
      if (access_token) {
        localStorage.setItem('arshith_auth_token', access_token);
        localStorage.setItem('arshith_role', 'admin');
        localStorage.setItem('arshith_user', JSON.stringify(user));
      }
      return { success: true, admin: user };
    } catch (error) {
      localStorage.removeItem('arshith_auth_token');
      localStorage.removeItem('arshith_role');
      localStorage.removeItem('arshith_user');
      const msg = error.response?.data?.detail || error.response?.data?.message || (error.response ? 'Invalid administrator credentials' : 'Unable to connect to the server. Please try again.');
      throw new Error(msg);
    }
  },

  /**
   * Register new employee
   * @param {Object} employeeData
   */
  async register(employeeData) {
    try {
      const response = await api.post('/api/auth/register', {
        fullName: employeeData.fullName || employeeData.name,
        employeeId: employeeData.employeeId || employeeData.id,
        email: employeeData.email,
        phone: employeeData.phone || '--',
        password: employeeData.password,
        confirmPassword: employeeData.confirmPassword,
      });

      return {
        success: true,
        message: response.data?.message || 'Your registration request is awaiting admin approval.',
      };
    } catch (error) {
      const data = error.response?.data;
      let msg = typeof data?.detail === 'string' ? data.detail : data?.message;
      if (!error.response) {
        msg = 'Unable to connect to the server. Please check your connection and try again.';
      } else if (!msg) {
        if (error.response?.status >= 500) {
          msg = "We couldn't complete your registration right now. Please try again later.";
        } else {
          msg = 'Please check the form for errors.';
        }
      }
      const customErr = new Error(msg);
      customErr.status = error.response?.status;
      customErr.errors =
        data?.errors ||
        (typeof data?.detail === 'object' && data.detail?.errors ? data.detail.errors : null) ||
        {};
      customErr.detail = msg;
      throw customErr;
    }
  },

  /**
   * Retrieve current authenticated user from storage
   */
  getCurrentUser() {
    try {
      const data = localStorage.getItem('arshith_user');
      return data ? JSON.parse(data) : null;
    } catch {
      return null;
    }
  },

  /**
   * Fetch live authenticated user details from backend
   */
  async fetchMe() {
    try {
      const response = await api.get('/api/auth/me');
      if (response.data) {
        localStorage.setItem('arshith_user', JSON.stringify(response.data));
        localStorage.setItem('arshith_role', response.data.role);
      }
      return response.data;
    } catch {
      return this.getCurrentUser();
    }
  },

  /**
   * Log out session
   */
  logout() {
    try {
      api.post('/api/auth/logout').catch(() => {});
    } catch {
      // Ignored
    }
    localStorage.removeItem('arshith_role');
    localStorage.removeItem('arshith_user');
    localStorage.removeItem('arshith_auth_token');
  },
};

export default authService;
