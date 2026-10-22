import React, { useState, useEffect } from 'react';
import { Calendar, Plus, Clock, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import PageHeader from '../../components/common/PageHeader';
import ApplyLeaveModal from '../../components/employee/ApplyLeaveModal';
import { leaveService } from '../../services/leaveService';

const formatDateSafe = (dateVal) => {
  if (!dateVal) return '-';
  if (typeof dateVal === 'string') {
    if (/^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}$/.test(dateVal.trim())) {
      return dateVal.trim();
    }
    const datePart = dateVal.split('T')[0].split(' ')[0];
    const parts = datePart.split('-');
    if (parts.length === 3) {
      const year = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      if (!isNaN(year) && !isNaN(month) && !isNaN(day) && month >= 0 && month <= 11) {
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        return `${day < 10 ? '0' + day : day} ${months[month]} ${year}`;
      }
    }
  }
  try {
    const d = new Date(dateVal);
    if (!isNaN(d.getTime())) {
      const day = d.getDate();
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      return `${day < 10 ? '0' + day : day} ${months[d.getMonth()]} ${d.getFullYear()}`;
    }
  } catch (e) {
    // fallback
  }
  return String(dateVal);
};

export default function EmployeeLeave() {
  const [isApplyModalOpen, setIsApplyModalOpen] = useState(false);
  const [successBanner, setSuccessBanner] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [leaveHistory, setLeaveHistory] = useState([]);
  const [balances, setBalances] = useState({
    casualLeave: { available: 8, total: 12 },
    sickLeave: { available: 6, total: 8 },
    earnedLeave: { available: 10, total: 15 },
  });
  const [isLoading, setIsLoading] = useState(true);

  const fetchMyLeaves = async () => {
    try {
      setIsLoading(true);
      setErrorMessage('');
      const [leavesRes, balancesRes] = await Promise.allSettled([
        leaveService.getMyLeaves(),
        leaveService.getLeaveBalances(),
      ]);

      if (leavesRes.status === 'fulfilled' && Array.isArray(leavesRes.value)) {
        setLeaveHistory(leavesRes.value);
      } else if (leavesRes.status === 'rejected') {
        setErrorMessage(leavesRes.reason?.message || 'Failed to fetch personal leave requests');
      }

      if (balancesRes.status === 'fulfilled' && balancesRes.value) {
        setBalances(balancesRes.value);
      }
    } catch (err) {
      setErrorMessage(err.message || 'Failed to fetch personal leave requests');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMyLeaves();
  }, []);

  const handleOpenModal = () => {
    setIsApplyModalOpen(true);
  };

  return (
    <div className="employee-leave-view animate-fade-in">
      <PageHeader
        title="Leave Management"
        subtitle="Submit leave applications and track approval status"
        breadcrumb={[{ label: 'Employee', path: '/employee/dashboard' }, { label: 'Leave' }]}
        actionButton={
          <button
            type="button"
            className="btn-primary-action"
            onClick={handleOpenModal}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Plus size={16} />
            <span>Apply For Leave</span>
          </button>
        }
      />

      {successBanner && (
        <div style={{ backgroundColor: '#ecfdf5', color: '#047857', padding: '12px 18px', borderRadius: '12px', border: '1px solid #a7f3d0', marginBottom: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <CheckCircle2 size={18} />
          <span style={{ fontWeight: '500' }}>{successBanner}</span>
        </div>
      )}

      {errorMessage && (
        <div style={{ backgroundColor: '#fef2f2', color: '#b91c1c', padding: '12px 18px', borderRadius: '12px', border: '1px solid #fecaca', marginBottom: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertCircle size={18} />
          <span style={{ fontWeight: '500' }}>{errorMessage}</span>
        </div>
      )}

      {/* Leave History Table */}
      <div className="management-page-card">
        <h2 style={{ fontSize: '1.05rem', fontWeight: '800', color: '#0b3d2b', marginBottom: '14px' }}>
          Leave Request History
        </h2>

        <div className="table-responsive-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Request ID</th>
                <th>Leave Type</th>
                <th>From Date</th>
                <th>To Date</th>
                <th>Duration</th>
                <th>Reason</th>
                <th>Applied On</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '28px', color: '#64748b' }}>
                    Loading leave requests...
                  </td>
                </tr>
              ) : leaveHistory.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '28px', color: '#64748b' }}>
                    No leave requests found.
                  </td>
                </tr>
              ) : (
                leaveHistory.map((item, idx) => {
                  const requestId = item.request_id || item.requestId || item.id || `REQ-${idx + 1}`;
                  const leaveTypeDisplay = item.leave_type || item.leaveType || item.type || '-';
                  const isHourly = (item.duration_type || item.durationType) === 'Hourly Leave' || item.hours != null || item.hours_count != null;
                  const fromDate = formatDateSafe(item.from_date || item.fromDate || item.startDate || item.start_date || item.leave_date || item.leaveDate || item.from);
                  const toDate = isHourly && (item.start_time || item.startTime)
                    ? `${item.start_time || item.startTime} - ${item.end_time || item.endTime}`
                    : formatDateSafe(item.to_date || item.toDate || item.endDate || item.end_date || item.to);

                  const hours = item.hours ?? item.hours_count ?? item.hoursCount;
                  const days = item.days ?? item.days_count ?? item.daysCount ?? 1;
                  const durationDisplay = isHourly
                    ? `${hours} hr${hours === 1 ? '' : 's'}`
                    : `${days} ${days === 1 ? 'day' : 'days'}`;

                  const itemReason = item.reason || '-';
                  const appliedOn = formatDateSafe(
                    item.applied_on || item.appliedOn || item.applied_date || item.appliedDate || item.requestDate
                  );
                  const itemStatus = item.status || 'Pending';

                  return (
                    <tr key={item.id || item.request_id || idx}>
                      <td style={{ fontWeight: '700', color: '#0b3d2b' }}>{requestId}</td>
                      <td style={{ fontWeight: '600' }}>{leaveTypeDisplay}</td>
                      <td>{fromDate}</td>
                      <td>{toDate}</td>
                      <td style={{ fontWeight: '600', color: isHourly ? '#6d28d9' : '#1e293b' }}>
                        {durationDisplay}
                      </td>
                      <td style={{ color: '#475569', maxWidth: '240px' }}>{itemReason}</td>
                      <td style={{ color: '#64748b' }}>{appliedOn}</td>
                      <td>
                        <span
                          className={`badge-status ${itemStatus === 'Approved'
                              ? 'badge-present'
                              : itemStatus === 'Rejected'
                                ? 'badge-absent'
                                : 'badge-late'
                            }`}
                        >
                          {itemStatus}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Apply Leave Modal */}
      <ApplyLeaveModal
        isOpen={isApplyModalOpen}
        onClose={() => setIsApplyModalOpen(false)}
        onSuccess={() => {
          setSuccessBanner('Leave request submitted successfully for administrator approval.');
          setTimeout(() => setSuccessBanner(''), 4500);
          fetchMyLeaves();
        }}
        balances={balances}
      />
    </div>
  );
}
