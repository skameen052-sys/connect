import React, { useState } from 'react';
import { AlertCircle, CheckCircle2, Clock, Calendar, User, BadgeAlert } from 'lucide-react';
import Modal from '../common/Modal';
import { attendanceService } from '../../services/attendanceService';
import { authService } from '../../services/authService';

/**
 * LateCheckInModal - Mandatory Late Check-in Reason Form
 *
 * Enforces server-recorded check-in after 9:30 AM IST.
 * Displays employee & attendance details and records verified reason.
 */
export default function LateCheckInModal({
  isOpen,
  onClose,
  recordId,
  employeeName,
  employeeId,
  attendanceDate = '',
  checkInTime = '--',
  onSuccess,
}) {
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const currentUser = authService.getCurrentUser();
  const effectiveName = employeeName || currentUser?.fullName || currentUser?.name || currentUser?.displayName || 'Employee';
  const effectiveId = employeeId || currentUser?.employeeId || currentUser?.id || '--';

  const handleSubmit = async (e) => {
    e.preventDefault();

    const trimmed = (reason || '').trim();
    if (!trimmed) {
      setError('Please provide a valid reason for your late arrival.');
      return;
    }

    if (isSubmitting) return;

    try {
      setIsSubmitting(true);
      setError('');

      const res = await attendanceService.submitLateReason({
        attendanceId: recordId,
        reason: trimmed,
        date: attendanceDate,
      });

      setIsSuccess(true);
      setTimeout(() => {
        setIsSuccess(false);
        setReason('');
        if (onSuccess) {
          onSuccess(res);
        }
        onClose();
      }, 1200);
    } catch (err) {
      // Preserve reason in state so the employee can retry without retyping
      setError(err.message || 'Failed to submit late check-in reason. Please retry.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={isSubmitting ? () => {} : onClose}
      title="Late Check-in"
      subtitle="Your check-in time is after 9:30 AM. Please provide a reason for your late arrival."
      maxWidth="520px"
    >
      {isSuccess ? (
        <div style={{ textAlign: 'center', padding: '24px 12px' }}>
          <CheckCircle2 size={46} color="#10b981" style={{ margin: '0 auto 12px auto' }} />
          <h3 style={{ fontSize: '1.15rem', fontWeight: '700', color: '#0b3d2b', marginBottom: '6px' }}>
            Reason Recorded Successfully
          </h3>
          <p style={{ fontSize: '0.85rem', color: '#64748b', margin: 0 }}>
            Your late arrival reason has been officially saved to your attendance record.
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {error && (
            <div
              style={{
                backgroundColor: '#fef2f2',
                border: '1px solid #fecaca',
                color: '#b91c1c',
                padding: '10px 14px',
                borderRadius: '10px',
                fontSize: '0.825rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <AlertCircle size={16} style={{ flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}

          {/* Employee & Attendance Context Summary */}
          <div
            style={{
              backgroundColor: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '14px',
              padding: '14px 16px',
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '12px',
            }}
          >
            <div>
              <div style={{ fontSize: '0.72rem', color: '#64748b', fontWeight: '600', textTransform: 'uppercase' }}>
                Employee
              </div>
              <div style={{ fontSize: '0.9rem', fontWeight: '700', color: '#0b3d2b', marginTop: '2px' }}>
                {effectiveName}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>ID: {effectiveId}</div>
            </div>

            <div>
              <div style={{ fontSize: '0.72rem', color: '#64748b', fontWeight: '600', textTransform: 'uppercase' }}>
                Actual Check-In
              </div>
              <div style={{ fontSize: '0.9rem', fontWeight: '700', color: '#b45309', marginTop: '2px' }}>
                {checkInTime}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                {attendanceDate || new Date().toISOString().split('T')[0]}
              </div>
            </div>
          </div>

          {/* Mandatory Reason Input */}
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label
              htmlFor="late-arrival-reason"
              className="form-label"
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
            >
              <span>Late Arrival Reason <span style={{ color: '#dc2626' }}>*</span></span>
              <span style={{ fontSize: '0.72rem', color: '#b45309', fontWeight: '600' }}>Mandatory (Post 9:30 AM)</span>
            </label>
            <textarea
              id="late-arrival-reason"
              rows={4}
              required
              disabled={isSubmitting}
              placeholder="Enter your reason for late check-in..."
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
                if (error) setError('');
              }}
              className="form-input-auth"
              style={{
                width: '100%',
                minHeight: '96px',
                padding: '12px 14px',
                resize: 'none',
                boxSizing: 'border-box',
                borderRadius: '12px',
                fontSize: '0.875rem',
              }}
            />
          </div>

          {/* Action Button */}
          <button
            type="submit"
            disabled={isSubmitting}
            className="btn-primary-purple"
            style={{
              marginTop: '4px',
              height: '46px',
              opacity: isSubmitting ? 0.75 : 1,
              cursor: isSubmitting ? 'not-allowed' : 'pointer',
            }}
          >
            {isSubmitting ? 'Submitting Reason...' : 'Submit Reason'}
          </button>
        </form>
      )}
    </Modal>
  );
}
