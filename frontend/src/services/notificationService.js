import { collection, onSnapshot } from 'firebase/firestore';
import { db } from '../firebase/firebaseConfig';
import api from './api';

/**
 * NotificationService - Manages dynamic notification badge counts across Quick Actions.
 * Integrates real-time Firestore listeners, persistent server-side read tracking,
 * and optimistic local storage caching scoped per employee.
 */

// In-memory cache and subscriber management
let activeSubscribers = new Set();
let firestoreUnsubscribers = [];
let pollingInterval = null;
let currentSummary = {
  announcements: 0,
  meetings: 0,
  assignments: 0,
  leaves: 0,
  total: 0,
};
let decidedLeavesList = [];

const getEmployeeKey = () => {
  try {
    const user = JSON.parse(localStorage.getItem('arshith_user')) || {};
    return user.employeeId || user.employee_id || user.id || user.uid || user.email || 'default';
  } catch {
    return 'default';
  }
};

const getCacheKey = () => `arshith_notifications_cache_${getEmployeeKey()}`;

export const notificationService = {
  /**
   * Get cached notification counts synchronously for instant flicker-free rendering.
   */
  getCachedCounts() {
    try {
      const cached = localStorage.getItem(getCacheKey());
      if (cached) {
        return JSON.parse(cached);
      }
    } catch {}
    return { announcements: 0, meetings: 0, assignments: 0, leaves: 0, total: 0 };
  },

  /**
   * Fetch authoritative unread summary from backend.
   */
  async getUnreadSummary() {
    try {
      const response = await api.get('/api/notifications/unread-summary');
      if (response.data && response.data.unread) {
        currentSummary = response.data.unread;
        decidedLeavesList = response.data.decidedLeaves || [];
        try {
          localStorage.setItem(getCacheKey(), JSON.stringify(currentSummary));
        } catch {}
        this._notifyAll(currentSummary);
        return response.data;
      }
    } catch (error) {
      console.warn('Could not fetch unread notifications summary:', error);
    }
    return { unread: currentSummary, decidedLeaves: decidedLeavesList };
  },

  /**
   * Mark a module's notifications as read/seen.
   * Optimistically zeroes the badge count immediately, then syncs with server.
   */
  async markAsRead(module, ids = ['*']) {
    const normModule = (module || '').toLowerCase();
    
    // 1. Optimistic UI update
    if (normModule.includes('announc')) {
      currentSummary = { ...currentSummary, announcements: 0 };
    } else if (normModule.includes('meet')) {
      currentSummary = { ...currentSummary, meetings: 0 };
    } else if (normModule.includes('assign')) {
      currentSummary = { ...currentSummary, assignments: 0 };
    } else if (normModule.includes('leave')) {
      currentSummary = { ...currentSummary, leaves: 0 };
    }
    currentSummary.total =
      (currentSummary.announcements || 0) +
      (currentSummary.meetings || 0) +
      (currentSummary.assignments || 0) +
      (currentSummary.leaves || 0);

    try {
      localStorage.setItem(getCacheKey(), JSON.stringify(currentSummary));
    } catch {}
    this._notifyAll(currentSummary);

    // 2. Persist to backend and Firestore
    try {
      const payload = { module: normModule, ids };
      await api.post('/api/notifications/mark-read', payload);
    } catch (err) {
      console.warn(`Failed to persist mark-read for ${normModule}:`, err);
    }
  },

  /**
   * Get list of recently decided leaves (Approved / Rejected) for employee view.
   */
  getDecidedLeaves() {
    return decidedLeavesList;
  },

  /**
   * Subscribe to real-time notification count changes.
   * Leverages both Firestore onSnapshot listeners and backend polling fallback.
   */
  subscribe(callback) {
    activeSubscribers.add(callback);

    // Provide cached data immediately
    const cached = this.getCachedCounts();
    callback(cached);

    // Initial fetch from backend
    this.getUnreadSummary();

    // Start Firestore real-time listeners if not already active
    if (activeSubscribers.size === 1) {
      this._startRealtimeListeners();
    }

    return () => {
      activeSubscribers.delete(callback);
      if (activeSubscribers.size === 0) {
        this._stopRealtimeListeners();
      }
    };
  },

  _notifyAll(summary) {
    activeSubscribers.forEach((cb) => {
      try {
        cb(summary);
      } catch (err) {
        console.error('Subscriber callback error:', err);
      }
    });
  },

  _startRealtimeListeners() {
    this._stopRealtimeListeners();

    // Debounced fetch helper to prevent stampeding
    let debounceTimer = null;
    const triggerRefresh = () => {
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        this.getUnreadSummary();
      }, 500);
    };

    // Firestore onSnapshot listeners on relevant collections
    if (db) {
      try {
        const collectionsToWatch = [
          'announcements',
          'notifications',
          'meetings',
          'assignments',
          'workAssignments',
          'leaves',
          'employee_notifications',
        ];

        collectionsToWatch.forEach((colName) => {
          try {
            const unsub = onSnapshot(
              collection(db, colName),
              () => triggerRefresh(),
              (err) => {
                // Non-fatal permission / network fallback
                console.debug(`Firestore onSnapshot on ${colName} inactive:`, err.message);
              }
            );
            firestoreUnsubscribers.push(unsub);
          } catch (e) {
            console.debug(`Could not attach onSnapshot to ${colName}:`, e);
          }
        });
      } catch (e) {
        console.debug('Firestore real-time listeners setup skipped:', e);
      }
    }

    // Secondary lightweight polling fallback every 10 seconds
    pollingInterval = setInterval(() => {
      this.getUnreadSummary();
    }, 10000);
  },

  _stopRealtimeListeners() {
    firestoreUnsubscribers.forEach((unsub) => {
      try {
        unsub();
      } catch {}
    });
    firestoreUnsubscribers = [];

    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }
  },
};

export default notificationService;
