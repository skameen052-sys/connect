import React, { useState, useEffect, useRef } from 'react';
import { Check, AlertCircle, CheckCircle2 } from 'lucide-react';
import Modal from '../common/Modal';
import { leaveService } from '../../services/leaveService';

export const LEAVE_TYPES = [
  { value: 'Casual Leave (CL)', label: 'Casual Leave', code: 'CL' },
  { value: 'Sick Leave (SL)', label: 'Sick Leave', code: 'SL' },
  { value: 'Earned Leave (EL)', label: 'Earned Leave', code: 'EL' },
  { value: 'Emergency Leave', label: 'Emergency Leave', code: 'EML' },
  { value: 'Maternity / Paternity', label: 'Maternity / Paternity', code: 'MPL' },
  { value: 'Compensatory Off', label: 'Compensatory Off', code: 'COMP' },
];

export const LEAVE_DURATIONS = [
  { value: 'Full-Day Leave', label: 'Full-Day Leave' },
  { value: 'Hourly Leave', label: 'Hourly Leave' },
];

// Helper to compute day count between two ISO date strings (inclusive)
export const calculateDaysDifference = (fromStr, toStr) => {
  if (!fromStr || !toStr) return null;
  const d1 = new Date(fromStr);
  const d2 = new Date(toStr);
  if (isNaN(d1.getTime()) || isNaN(d2.getTime())) return null;
  const diffTime = d2.getTime() - d1.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
  return diffDays;
};

// Helper to compute hour count between two HH:MM strings
export const calculateHoursDifference = (startStr, endStr) => {
  if (!startStr || !endStr) return null;
  const [sH, sM] = startStr.split(':').map(Number);
  const [eH, eM] = endStr.split(':').map(Number);
  if (isNaN(sH) || isNaN(sM) || isNaN(eH) || isNaN(eM)) return null;
  const diffMinutes = (eH * 60 + eM) - (sH * 60 + sM);
  if (diffMinutes <= 0) return 0;
  return Math.round((diffMinutes / 60) * 10) / 10;
};

/**
 * ApplyLeaveModal - Authoritative Employee Apply for Leave Form
 *
 * Matches the canonical UI design from screenshot 1:
 * - Header: Apply for Leave
 * - Subtitle: Fill in the details for your leave request.
 * - Section Heading: New Leave Request
 * - Custom styled dropdowns for Leave Type and Leave Duration
 * - From Date & To Date (Full-Day) or Leave Date, Start Time & End Time (Hourly)
 * - Reason for Leave textarea
 * - Real-time validations, duration counter, balance checks, and backend submission
 */
export default function ApplyLeaveModal({
  isOpen,
  onClose,
  onSuccess,
  balances: initialBalances,
  recentDecisions = [],
}) {
  // Form Fields
  const [leaveType, setLeaveType] = useState('Casual Leave (CL)');
  const [durationType, setDurationType] = useState('Full-Day Leave');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [leaveDate, setLeaveDate] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [reason, setReason] = useState('');

  // Dropdown UI States
  const [isLeaveTypeOpen, setIsLeaveTypeOpen] = useState(false);
  const [isDurationTypeOpen, setIsDurationTypeOpen] = useState(false);
  const leaveTypeRef = useRef(null);
  const durationTypeRef = useRef(null);

  // Status & Validation
  const [fieldErrors, setFieldErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [balances, setBalances] = useState(
    initialBalances || {
      casualLeave: { available: 8, total: 12 },
      sickLeave: { available: 6, total: 8 },
      earnedLeave: { available: 10, total: 15 },
    }
  );

  // Sync balances if prop changes or fetch dynamically if not provided
  useEffect(() => {
    if (initialBalances) {
      setBalances(initialBalances);
    } else if (isOpen) {
      leaveService.getLeaveBalances().then((res) => {
        if (res) setBalances(res);
      }).catch(() => {});
    }
  }, [initialBalances, isOpen]);

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      resetForm();
    }
  }, [isOpen]);

  // Close dropdowns on outside click
  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (leaveTypeRef.current && !leaveTypeRef.current.contains(e.target)) {
        setIsLeaveTypeOpen(false);
      }
      if (durationTypeRef.current && !durationTypeRef.current.contains(e.target)) {
        setIsDurationTypeOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
    }
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, [isOpen]);

  const resetForm = () => {
    setLeaveType('Casual Leave (CL)');
    setDurationType('Full-Day Leave');
    setStartDate('');
    setEndDate('');
    setLeaveDate('');
    setStartTime('');
    setEndTime('');
    setReason('');
    setFieldErrors({});
    setIsLeaveTypeOpen(false);
    setIsDurationTypeOpen(false);
    setIsSuccess(false);
    setErrorMessage('');
  };

  // Real-time calculated values
  const calculatedDays = durationType === 'Full-Day Leave' ? calculateDaysDifference(startDate, endDate) : null;
  const calculatedHours = durationType === 'Hourly Leave' ? calculateHoursDifference(startTime, endTime) : null;

  // Real-time balance check helper
  const getAvailableBalance = (type) => {
    const norm = (type || '').toLowerCase();
    if (norm.includes('casual') || norm.includes('cl')) {
      return balances?.casualLeave?.available ?? 0;
    }
    if (norm.includes('sick') || norm.includes('sl')) {
      return balances?.sickLeave?.available ?? 0;
    }
    if (norm.includes('earned') || norm.includes('el')) {
      return balances?.earnedLeave?.available ?? 0;
    }
    return null;
  };

  const validateForm = () => {
    const errors = {};

    if (!leaveType) {
      errors.leaveType = 'Please select a leave type.';
    }

    if (!durationType) {
      errors.durationType = 'Please select a leave duration.';
    }

    if (durationType === 'Full-Day Leave') {
      if (!startDate) {
        errors.startDate = 'Please select a start date.';
      }
      if (!endDate) {
        errors.endDate = 'Please select an end date.';
      }
      if (startDate && endDate) {
        if (new Date(endDate) < new Date(startDate)) {
          errors.dateRange = 'To Date must be on or after From Date.';
        } else {
          const available = getAvailableBalance(leaveType);
          const diff = calculateDaysDifference(startDate, endDate);
          if (available !== null && diff !== null && diff > available) {
            errors.balance = 'Insufficient leave balance.';
          }
        }
      }
    } else if (durationType === 'Hourly Leave') {
      if (!leaveDate) {
        errors.leaveDate = 'Please select a leave date.';
      }
      if (!startTime) {
        errors.startTime = 'Please select a start time.';
      }
      if (!endTime) {
        errors.endTime = 'Please select an end time.';
      }
      if (startTime && endTime) {
        const [sH, sM] = startTime.split(':').map(Number);
        const [eH, eM] = endTime.split(':').map(Number);
        if (eH * 60 + eM <= sH * 60 + sM) {
          errors.timeRange = 'End Time must be later than Start Time.';
        } else {
          const available = getAvailableBalance(leaveType);
          if (available !== null && available <= 0) {
            errors.balance = 'Insufficient leave balance.';
          }
        }
      }
    }

    if (!reason.trim()) {
      errors.reason = 'Please enter a reason for your leave.';
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleApplyLeave = async (e) => {
    e.preventDefault();
    if (isSubmitting) return;

    if (!validateForm()) return;

    try {
      setIsSubmitting(true);
      setErrorMessage('');

      const payload = {
        leaveType,
        durationType,
        reason: reason.trim(),
      };

      if (durationType === 'Hourly Leave') {
        payload.leaveDate = leaveDate;
        payload.startDate = leaveDate;
        payload.endDate = leaveDate;
        payload.startTime = startTime;
        payload.endTime = endTime;
        payload.hoursCount = calculatedHours || 0;
        payload.daysCount = 0;
      } else {
        payload.startDate = startDate;
        payload.endDate = endDate;
        payload.daysCount = calculatedDays && calculatedDays > 0 ? calculatedDays : 1;
      }

      const res = await leaveService.applyLeave(payload);
      setIsSuccess(true);
      setTimeout(() => {
        setIsSuccess(false);
        resetForm();
        if (onSuccess) {
          onSuccess(res);
        }
        onClose();
      }, 1200);
    } catch (err) {
      setErrorMessage(err.message || 'Failed to submit leave request. Please retry.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={isSubmitting ? () => {} : onClose}
      title="Apply for Leave"
      subtitle="Fill in the details for your leave request."
      maxWidth="560px"
    >
      {isSuccess ? (
        <div style={{ textAlign: 'center', padding: '28px 16px' }}>
          <CheckCircle2 size={46} color="#10b981" style={{ margin: '0 auto 12px auto' }} />
          <h3 style={{ fontSize: '1.2rem', fontWeight: '700', color: '#0b3d2b', marginBottom: '6px' }}>
            Leave Application Submitted!
          </h3>
          <p style={{ fontSize: '0.875rem', color: '#64748b', margin: 0 }}>
            Your request has been officially recorded in the database for administrator review.
          </p>
        </div>
      ) : (
        <form onSubmit={handleApplyLeave} style={{ position: 'relative' }}>
          {errorMessage && (
            <div
              style={{
                backgroundColor: '#fef2f2',
                border: '1px solid #fecaca',
                color: '#b91c1c',
                padding: '10px 14px',
                borderRadius: '10px',
                marginBottom: '16px',
                fontSize: '0.825rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <AlertCircle size={16} style={{ flexShrink: 0 }} />
              <span>{errorMessage}</span>
            </div>
          )}
          {recentDecisions && recentDecisions.length > 0 && (
            <div style={{ marginBottom: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: '700', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Recent Decision Updates
              </div>
              {recentDecisions.map((dec) => (
                <div
                  key={dec.id}
                  style={{
                    backgroundColor: dec.status === 'Approved' ? '#ecfdf5' : '#fef2f2',
                    border: `1.5px solid ${dec.status === 'Approved' ? '#a7f3d0' : '#fca5a5'}`,
                    borderRadius: '12px',
                    padding: '12px 14px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    {dec.status === 'Approved' ? (
                      <CheckCircle2 size={20} color="#059669" style={{ flexShrink: 0 }} />
                    ) : (
                      <AlertCircle size={20} color="#dc2626" style={{ flexShrink: 0 }} />
                    )}
                    <div>
                      <div style={{ fontSize: '0.88rem', fontWeight: 700, color: dec.status === 'Approved' ? '#065f46' : '#991b1b' }}>
                        Leave Request {dec.id} &bull; {dec.status.toUpperCase()}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '2px' }}>
                        {dec.leave_type || 'Leave'} {dec.rejection_remarks ? `• Reason: ${dec.rejection_remarks}` : '• Reviewed by Administrator'}
                      </div>
                    </div>
                  </div>
                  <span
                    style={{
                      fontSize: '0.72rem',
                      fontWeight: 800,
                      backgroundColor: dec.status === 'Approved' ? '#d1fae5' : '#fee2e2',
                      color: dec.status === 'Approved' ? '#047857' : '#b91c1c',
                      padding: '3px 10px',
                      borderRadius: '999px',
                      flexShrink: 0,
                    }}
                  >
                    {dec.status}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Section Heading matching reference screenshot 1 */}
          <h3
            style={{
              fontSize: '1.25rem',
              fontWeight: '800',
              color: '#1e1b4b',
              margin: '0 0 18px 0',
              letterSpacing: '-0.02em',
            }}
          >
            New Leave Request
          </h3>

          {/* 1. Leave Type Dropdown */}
          <div className="form-group" ref={leaveTypeRef} style={{ position: 'relative', marginBottom: '16px' }}>
            <label className="form-label" style={{ fontWeight: '600', color: '#1e293b', marginBottom: '6px', display: 'block' }}>
              Leave Type <span style={{ color: '#ef4444' }}>*</span>
            </label>

            <div
              id="leave-type-dropdown"
              tabIndex={0}
              role="button"
              aria-haspopup="listbox"
              aria-expanded={isLeaveTypeOpen}
              onClick={() => {
                setIsLeaveTypeOpen(!isLeaveTypeOpen);
                setIsDurationTypeOpen(false);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  setIsLeaveTypeOpen(!isLeaveTypeOpen);
                  setIsDurationTypeOpen(false);
                } else if (e.key === 'Escape') {
                  setIsLeaveTypeOpen(false);
                }
              }}
              style={{
                width: '100%',
                minHeight: '42px',
                padding: '0 14px',
                backgroundColor: '#ffffff',
                border: fieldErrors.leaveType ? '1.5px solid #ef4444' : isLeaveTypeOpen ? '1.5px solid #7047eb' : '1.5px solid #cbd5e1',
                borderRadius: '10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer',
                outline: 'none',
                boxShadow: isLeaveTypeOpen ? '0 0 0 3px rgba(112, 71, 235, 0.12)' : '0 1px 2px rgba(0,0,0,0.04)',
                transition: 'border-color 0.15s, box-shadow 0.15s',
                userSelect: 'none',
              }}
            >
              <span style={{ fontSize: '0.925rem', color: '#1e293b', fontWeight: '500' }}>
                {LEAVE_TYPES.find((opt) => opt.value === leaveType)?.label || leaveType || 'Casual Leave'}
              </span>
              <svg
                width="11"
                height="11"
                viewBox="0 0 24 24"
                fill="#7047eb"
                style={{
                  transform: isLeaveTypeOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                  flexShrink: 0,
                }}
              >
                <path d="M7 10l5 5 5-5z" />
              </svg>
            </div>

            {/* Dropdown Options */}
            {isLeaveTypeOpen && (
              <div
                role="listbox"
                style={{
                  position: 'absolute',
                  top: 'calc(100% + 4px)',
                  left: 0,
                  right: 0,
                  backgroundColor: '#ffffff',
                  borderRadius: '10px',
                  border: '1px solid #e2e8f0',
                  boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.12), 0 8px 10px -6px rgba(0, 0, 0, 0.08)',
                  zIndex: 90,
                  maxHeight: '230px',
                  overflowY: 'auto',
                  padding: '4px 0',
                }}
              >
                {LEAVE_TYPES.map((opt) => {
                  const isSelected = opt.value === leaveType;
                  return (
                    <div
                      key={opt.value}
                      role="option"
                      aria-selected={isSelected}
                      tabIndex={0}
                      onClick={() => {
                        setLeaveType(opt.value);
                        setIsLeaveTypeOpen(false);
                        if (fieldErrors.leaveType || fieldErrors.balance) {
                          setFieldErrors((prev) => ({ ...prev, leaveType: '', balance: '' }));
                        }
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          setLeaveType(opt.value);
                          setIsLeaveTypeOpen(false);
                        }
                      }}
                      onMouseEnter={(e) => {
                        if (!isSelected) e.currentTarget.style.backgroundColor = '#f5f3ff';
                      }}
                      onMouseLeave={(e) => {
                        if (!isSelected) e.currentTarget.style.backgroundColor = 'transparent';
                      }}
                      style={{
                        padding: '10px 16px',
                        fontSize: '0.9rem',
                        fontWeight: isSelected ? '600' : '500',
                        color: isSelected ? '#5b21b6' : '#1e293b',
                        backgroundColor: isSelected ? '#ede9fe' : 'transparent',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        cursor: 'pointer',
                        outline: 'none',
                        transition: 'background-color 0.1s',
                      }}
                    >
                      <span>{opt.label}</span>
                      {isSelected && <Check size={16} color="#7047eb" />}
                    </div>
                  );
                })}
              </div>
            )}

            {fieldErrors.leaveType && (
              <span style={{ fontSize: '0.75rem', color: '#ef4444', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <AlertCircle size={12} />
                {fieldErrors.leaveType}
              </span>
            )}
          </div>

          {/* 2. Leave Duration Dropdown */}
          <div className="form-group" ref={durationTypeRef} style={{ position: 'relative', marginBottom: '16px' }}>
            <label className="form-label" style={{ fontWeight: '600', color: '#1e293b', marginBottom: '6px', display: 'block' }}>
              Leave Duration <span style={{ color: '#ef4444' }}>*</span>
            </label>

            <div
              id="leave-duration-dropdown"
              tabIndex={0}
              role="button"
              aria-haspopup="listbox"
              aria-expanded={isDurationTypeOpen}
              onClick={() => {
                setIsDurationTypeOpen(!isDurationTypeOpen);
                setIsLeaveTypeOpen(false);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  setIsDurationTypeOpen(!isDurationTypeOpen);
                  setIsLeaveTypeOpen(false);
                } else if (e.key === 'Escape') {
                  setIsDurationTypeOpen(false);
                }
              }}
              style={{
                width: '100%',
                minHeight: '42px',
                padding: '0 14px',
                backgroundColor: '#ffffff',
                border: fieldErrors.durationType ? '1.5px solid #ef4444' : isDurationTypeOpen ? '1.5px solid #7047eb' : '1.5px solid #cbd5e1',
                borderRadius: '10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer',
                outline: 'none',
                boxShadow: isDurationTypeOpen ? '0 0 0 3px rgba(112, 71, 235, 0.12)' : '0 1px 2px rgba(0,0,0,0.04)',
                transition: 'border-color 0.15s, box-shadow 0.15s',
                userSelect: 'none',
              }}
            >
              <span style={{ fontSize: '0.925rem', color: '#1e293b', fontWeight: '500' }}>
                {LEAVE_DURATIONS.find((opt) => opt.value === durationType)?.label || durationType || 'Full-Day Leave'}
              </span>
              <svg
                width="11"
                height="11"
                viewBox="0 0 24 24"
                fill="#7047eb"
                style={{
                  transform: isDurationTypeOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                  flexShrink: 0,
                }}
              >
                <path d="M7 10l5 5 5-5z" />
              </svg>
            </div>

            {/* Dropdown Options */}
            {isDurationTypeOpen && (
              <div
                role="listbox"
                style={{
                  position: 'absolute',
                  top: 'calc(100% + 4px)',
                  left: 0,
                  right: 0,
                  backgroundColor: '#ffffff',
                  borderRadius: '10px',
                  border: '1px solid #e2e8f0',
                  boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.12), 0 8px 10px -6px rgba(0, 0, 0, 0.08)',
                  zIndex: 90,
                  overflowY: 'auto',
                  padding: '4px 0',
                }}
              >
                {LEAVE_DURATIONS.map((opt) => {
                  const isSelected = opt.value === durationType;
                  return (
                    <div
                      key={opt.value}
                      role="option"
                      aria-selected={isSelected}
                      tabIndex={0}
                      onClick={() => {
                        setDurationType(opt.value);
                        setIsDurationTypeOpen(false);
                        if (fieldErrors.durationType || fieldErrors.balance) {
                          setFieldErrors((prev) => ({ ...prev, durationType: '', balance: '' }));
                        }
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          setDurationType(opt.value);
                          setIsDurationTypeOpen(false);
                        }
                      }}
                      onMouseEnter={(e) => {
                        if (!isSelected) e.currentTarget.style.backgroundColor = '#f5f3ff';
                      }}
                      onMouseLeave={(e) => {
                        if (!isSelected) e.currentTarget.style.backgroundColor = 'transparent';
                      }}
                      style={{
                        padding: '10px 16px',
                        fontSize: '0.9rem',
                        fontWeight: isSelected ? '600' : '500',
                        color: isSelected ? '#5b21b6' : '#1e293b',
                        backgroundColor: isSelected ? '#ede9fe' : 'transparent',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        cursor: 'pointer',
                        outline: 'none',
                        transition: 'background-color 0.1s',
                      }}
                    >
                      <span>{opt.label}</span>
                      {isSelected && <Check size={16} color="#7047eb" />}
                    </div>
                  );
                })}
              </div>
            )}

            {fieldErrors.durationType && (
              <span style={{ fontSize: '0.75rem', color: '#ef4444', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <AlertCircle size={12} />
                {fieldErrors.durationType}
              </span>
            )}
          </div>

          {/* 3. Conditional Fields Based on Leave Duration */}
          {durationType === 'Full-Day Leave' ? (
            <div style={{ marginBottom: '16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
                <div className="form-group" style={{ marginBottom: '6px' }}>
                  <label className="form-label" style={{ fontWeight: '600', color: '#1e293b', marginBottom: '6px' }}>
                    From Date <span style={{ color: '#ef4444' }}>*</span>
                  </label>
                  <input
                    type="date"
                    required
                    className="form-input-auth"
                    value={startDate}
                    onChange={(e) => {
                      setStartDate(e.target.value);
                      if (fieldErrors.startDate || fieldErrors.dateRange || fieldErrors.balance) {
                        setFieldErrors((prev) => ({ ...prev, startDate: '', dateRange: '', balance: '' }));
                      }
                    }}
                    style={{
                      border: (fieldErrors.startDate || fieldErrors.dateRange) ? '1.5px solid #ef4444' : undefined,
                    }}
                  />
                  {fieldErrors.startDate && (
                    <span style={{ fontSize: '0.75rem', color: '#ef4444', marginTop: '4px', display: 'block' }}>
                      {fieldErrors.startDate}
                    </span>
                  )}
                </div>

                <div className="form-group" style={{ marginBottom: '6px' }}>
                  <label className="form-label" style={{ fontWeight: '600', color: '#1e293b', marginBottom: '6px' }}>
                    To Date <span style={{ color: '#ef4444' }}>*</span>
                  </label>
                  <input
                    type="date"
                    required
                    className="form-input-auth"
                    value={endDate}
                    onChange={(e) => {
                      setEndDate(e.target.value);
                      if (fieldErrors.endDate || fieldErrors.dateRange || fieldErrors.balance) {
                        setFieldErrors((prev) => ({ ...prev, endDate: '', dateRange: '', balance: '' }));
                      }
                    }}
                    style={{
                      border: (fieldErrors.endDate || fieldErrors.dateRange) ? '1.5px solid #ef4444' : undefined,
                    }}
                  />
                  {fieldErrors.endDate && (
                    <span style={{ fontSize: '0.75rem', color: '#ef4444', marginTop: '4px', display: 'block' }}>
                      {fieldErrors.endDate}
                    </span>
                  )}
                </div>
              </div>

              {/* Date Range Error */}
              {fieldErrors.dateRange && (
                <span style={{ fontSize: '0.75rem', color: '#ef4444', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <AlertCircle size={12} />
                  {fieldErrors.dateRange}
                </span>
              )}

              {/* Calculated Full-Day Duration Info Badge */}
              {startDate && endDate && calculatedDays !== null && calculatedDays > 0 && !fieldErrors.dateRange && (
                <div style={{ marginTop: '8px', padding: '6px 12px', backgroundColor: '#f0fdf4', borderRadius: '8px', border: '1px solid #bbf7d0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8rem', color: '#166534' }}>
                  <span>Calculated Duration:</span>
                  <span style={{ fontWeight: '700' }}>{calculatedDays} {calculatedDays === 1 ? 'day' : 'days'}</span>
                </div>
              )}
            </div>
          ) : (
            /* Hourly Leave Fields */
            <div style={{ marginBottom: '16px' }}>
              <div className="form-group" style={{ marginBottom: '12px' }}>
                <label className="form-label" style={{ fontWeight: '600', color: '#1e293b', marginBottom: '6px' }}>
                  Leave Date <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <input
                  type="date"
                  required
                  className="form-input-auth"
                  value={leaveDate}
                  onChange={(e) => {
                    setLeaveDate(e.target.value);
                    if (fieldErrors.leaveDate) {
                      setFieldErrors((prev) => ({ ...prev, leaveDate: '' }));
                    }
                  }}
                  style={{
                    border: fieldErrors.leaveDate ? '1.5px solid #ef4444' : undefined,
                  }}
                />
                {fieldErrors.leaveDate && (
                  <span style={{ fontSize: '0.75rem', color: '#ef4444', marginTop: '4px', display: 'block' }}>
                    {fieldErrors.leaveDate}
                  </span>
                )}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
                <div className="form-group" style={{ marginBottom: '6px' }}>
                  <label className="form-label" style={{ fontWeight: '600', color: '#1e293b', marginBottom: '6px' }}>
                    Start Time <span style={{ color: '#ef4444' }}>*</span>
                  </label>
                  <input
                    type="time"
                    required
                    className="form-input-auth"
                    value={startTime}
                    onChange={(e) => {
                      setStartTime(e.target.value);
                      if (fieldErrors.startTime || fieldErrors.timeRange) {
                        setFieldErrors((prev) => ({ ...prev, startTime: '', timeRange: '' }));
                      }
                    }}
                    style={{
                      border: (fieldErrors.startTime || fieldErrors.timeRange) ? '1.5px solid #ef4444' : undefined,
                    }}
                  />
                  {fieldErrors.startTime && (
                    <span style={{ fontSize: '0.75rem', color: '#ef4444', marginTop: '4px', display: 'block' }}>
                      {fieldErrors.startTime}
                    </span>
                  )}
                </div>

                <div className="form-group" style={{ marginBottom: '6px' }}>
                  <label className="form-label" style={{ fontWeight: '600', color: '#1e293b', marginBottom: '6px' }}>
                    End Time <span style={{ color: '#ef4444' }}>*</span>
                  </label>
                  <input
                    type="time"
                    required
                    className="form-input-auth"
                    value={endTime}
                    onChange={(e) => {
                      setEndTime(e.target.value);
                      if (fieldErrors.endTime || fieldErrors.timeRange) {
                        setFieldErrors((prev) => ({ ...prev, endTime: '', timeRange: '' }));
                      }
                    }}
                    style={{
                      border: (fieldErrors.endTime || fieldErrors.timeRange) ? '1.5px solid #ef4444' : undefined,
                    }}
                  />
                  {fieldErrors.endTime && (
                    <span style={{ fontSize: '0.75rem', color: '#ef4444', marginTop: '4px', display: 'block' }}>
                      {fieldErrors.endTime}
                    </span>
                  )}
                </div>
              </div>

              {/* Time Range Error */}
              {fieldErrors.timeRange && (
                <span style={{ fontSize: '0.75rem', color: '#ef4444', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <AlertCircle size={12} />
                  {fieldErrors.timeRange}
                </span>
              )}

              {/* Calculated Hourly Duration Info Badge */}
              {startTime && endTime && calculatedHours !== null && calculatedHours > 0 && !fieldErrors.timeRange && (
                <div style={{ marginTop: '8px', padding: '6px 12px', backgroundColor: '#eff6ff', borderRadius: '8px', border: '1px solid #bfdbfe', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8rem', color: '#1e40af' }}>
                  <span>Calculated Duration:</span>
                  <span style={{ fontWeight: '700' }}>{calculatedHours} {calculatedHours === 1 ? 'hour' : 'hours'}</span>
                </div>
              )}
            </div>
          )}

          {/* Insufficient Balance Error */}
          {fieldErrors.balance && (
            <div style={{ marginBottom: '14px', padding: '8px 12px', backgroundColor: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', color: '#b91c1c', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <AlertCircle size={14} />
              <span>{fieldErrors.balance}</span>
            </div>
          )}

          {/* 4. Reason for Leave */}
          <div className="form-group" style={{ marginBottom: '16px' }}>
            <label className="form-label" style={{ fontWeight: '600', color: '#1e293b', marginBottom: '6px', display: 'block' }}>
              Reason for Leave <span style={{ color: '#ef4444' }}>*</span>
            </label>
            <textarea
              rows={3}
              required
              className="form-input-auth"
              style={{
                height: '80px',
                padding: '10px 14px',
                resize: 'vertical',
                border: fieldErrors.reason ? '1.5px solid #ef4444' : undefined,
              }}
              placeholder="State the reason clearly..."
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
                if (fieldErrors.reason) {
                  setFieldErrors((prev) => ({ ...prev, reason: '' }));
                }
              }}
            />
            {fieldErrors.reason && (
              <span style={{ fontSize: '0.75rem', color: '#ef4444', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <AlertCircle size={12} />
                {fieldErrors.reason}
              </span>
            )}
          </div>

          {/* 5. Submit and Cancel Actions */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '18px' }}>
            <button
              type="button"
              className="btn-secondary-gray"
              style={{ width: 'auto', padding: '0 16px', height: '38px' }}
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary-purple"
              style={{ width: 'auto', padding: '0 20px', height: '38px', opacity: isSubmitting ? 0.7 : 1 }}
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Submitting...' : 'Submit Application'}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}
