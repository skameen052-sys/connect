import React, { useState, useEffect } from 'react';
import { 
  CreditCard, CheckCircle2, XCircle, Search, RefreshCw, 
  Calendar, DollarSign, Clock, Eye, X, Plus 
} from 'lucide-react';
import loanService from '../../services/loanService';

export default function AdminLoans() {
  const [loans, setLoans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false);
  const [selectedSchedule, setSelectedSchedule] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const fetchLoans = async () => {
    setLoading(true);
    try {
      const data = await loanService.getLoans();
      setLoans(data);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch employee loan applications.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLoans();
  }, []);

  const handleUpdateStatus = async (loanId, newStatus) => {
    setActionLoading(true);
    try {
      await loanService.updateStatus(loanId, { status: newStatus });
      setSuccessMsg(`Loan ${newStatus.toLowerCase()} successfully.`);
      fetchLoans();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update loan status.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleViewSchedule = async (loanId) => {
    try {
      const res = await loanService.getSchedule(loanId);
      setSelectedSchedule(res);
      setScheduleModalOpen(true);
    } catch (err) {
      setError('Could not generate repayment schedule.');
    }
  };

  const filteredLoans = loans.filter((l) => {
    const matchesSearch =
      (l.employee_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (l.employee_id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (l.loan_type || '').toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || (l.status || '').toUpperCase() === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const totalOutstanding = loans
    .filter((l) => ['ACTIVE', 'APPROVED'].includes((l.status || '').toUpperCase()))
    .reduce((acc, l) => acc + (parseFloat(l.remaining_balance) || 0), 0);

  const totalMonthlyEmi = loans
    .filter((l) => ['ACTIVE', 'APPROVED'].includes((l.status || '').toUpperCase()))
    .reduce((acc, l) => acc + (parseFloat(l.monthly_installment) || 0), 0);

  const getStatusBadge = (status) => {
    const s = (status || 'PENDING').toUpperCase();
    if (s === 'ACTIVE' || s === 'APPROVED') {
      return <span className="hrms-badge hrms-badge-success"><CheckCircle2 size={12} /> ACTIVE</span>;
    }
    if (s === 'CLOSED') {
      return <span className="hrms-badge hrms-badge-neutral"><CheckCircle2 size={12} /> CLOSED</span>;
    }
    if (s === 'REJECTED') {
      return <span className="hrms-badge hrms-badge-danger"><XCircle size={12} /> REJECTED</span>;
    }
    return <span className="hrms-badge hrms-badge-warning"><Clock size={12} /> PENDING REVIEW</span>;
  };

  return (
    <div className="hrms-page-container">
      {/* Header */}
      <div className="hrms-page-header">
        <div className="hrms-page-title-group">
          <h1><CreditCard size={28} className="text-forest" /> Employee Loans & Salary Advances</h1>
          <p className="hrms-page-subtitle">
            Manage advance approvals, monthly EMI amortization schedules, and automatic payroll salary deductions.
          </p>
        </div>

        <div className="hrms-actions-group">
          <button type="button" className="hrms-btn-secondary" onClick={fetchLoans} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="hrms-card" style={{ borderColor: '#fca5a5', backgroundColor: '#fef2f2', padding: '1rem', marginBottom: '1rem' }}>
          <span style={{ color: '#991b1b' }}>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="hrms-card" style={{ borderColor: '#86efac', backgroundColor: '#f0fdf4', padding: '1rem', marginBottom: '1rem' }}>
          <span style={{ color: '#166534' }}>{successMsg}</span>
        </div>
      )}

      {/* Metrics */}
      <div className="hrms-metrics-grid">
        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Total Outstanding Balance</span>
            <div className="hrms-metric-icon-wrap"><DollarSign size={18} /></div>
          </div>
          <div className="hrms-metric-value">₹{totalOutstanding.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
          <div className="hrms-metric-subtext">Active loan principal outstanding</div>
        </div>

        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Monthly EMI Inflow</span>
            <div className="hrms-metric-icon-wrap"><CreditCard size={18} /></div>
          </div>
          <div className="hrms-metric-value">₹{totalMonthlyEmi.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
          <div className="hrms-metric-subtext">Auto-deducted in monthly payroll</div>
        </div>

        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Pending Applications</span>
            <div className="hrms-metric-icon-wrap" style={{ color: '#d97706', backgroundColor: '#fef3c7' }}><Clock size={18} /></div>
          </div>
          <div className="hrms-metric-value" style={{ color: '#d97706' }}>
            {loans.filter((l) => (l.status || '').toUpperCase() === 'PENDING').length}
          </div>
          <div className="hrms-metric-subtext">Awaiting administrative approval</div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="hrms-card">
        <div className="hrms-card-body" style={{ padding: '1rem 1.5rem' }}>
          <div className="hrms-filter-bar" style={{ margin: 0 }}>
            <div className="hrms-search-input-wrap">
              <Search size={16} />
              <input
                type="text"
                className="hrms-input"
                placeholder="Search by employee name or loan type..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            <select
              className="hrms-select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="ALL">All Statuses</option>
              <option value="PENDING">Pending Review</option>
              <option value="ACTIVE">Active Loans</option>
              <option value="CLOSED">Closed / Repaid</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>
        </div>
      </div>

      {/* Loans Table */}
      <div className="hrms-card">
        <div className="hrms-table-container">
          <table className="hrms-table">
            <thead>
              <tr>
                <th>Employee</th>
                <th>Loan Type</th>
                <th>Principal Amount</th>
                <th>Tenure</th>
                <th>Monthly EMI</th>
                <th>Remaining Balance</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredLoans.length === 0 ? (
                <tr>
                  <td colSpan="8">
                    <div className="hrms-empty-state">
                      <CreditCard className="hrms-empty-icon" />
                      <p>No loan or advance applications found.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredLoans.map((l) => {
                  const lId = l.id || l._firestore_id;
                  const isPending = (l.status || '').toUpperCase() === 'PENDING';
                  return (
                    <tr key={lId}>
                      <td>
                        <strong>{l.employee_name || l.employee_id}</strong>
                        <div className="hrms-metric-subtext">{l.employee_id} • Applied: {l.applied_date || l.created_at?.split('T')[0]}</div>
                      </td>
                      <td>
                        <strong>{l.loan_type}</strong>
                        <div className="hrms-metric-subtext" style={{ maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {l.reason}
                        </div>
                      </td>
                      <td>₹{parseFloat(l.principal_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                      <td>{l.term_months} Months</td>
                      <td>
                        <strong style={{ color: '#134e4a' }}>
                          ₹{parseFloat(l.monthly_installment || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </strong>
                      </td>
                      <td>
                        <strong style={{ color: parseFloat(l.remaining_balance || 0) > 0 ? '#b45309' : '#16a34a' }}>
                          ₹{parseFloat(l.remaining_balance || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </strong>
                      </td>
                      <td>{getStatusBadge(l.status)}</td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          {isPending && (
                            <>
                              <button
                                type="button"
                                className="hrms-btn-primary"
                                style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
                                onClick={() => handleUpdateStatus(lId, 'APPROVED')}
                                disabled={actionLoading}
                              >
                                Approve
                              </button>
                              <button
                                type="button"
                                className="hrms-btn-secondary"
                                style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem', color: '#dc2626' }}
                                onClick={() => handleUpdateStatus(lId, 'REJECTED')}
                                disabled={actionLoading}
                              >
                                Reject
                              </button>
                            </>
                          )}
                          <button
                            type="button"
                            className="hrms-btn-secondary"
                            style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
                            onClick={() => handleViewSchedule(lId)}
                            title="View repayment schedule"
                          >
                            <Eye size={13} /> Schedule
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Repayment Schedule Modal */}
      {scheduleModalOpen && selectedSchedule && (
        <div className="hrms-modal-overlay" onClick={() => setScheduleModalOpen(false)}>
          <div className="hrms-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="hrms-modal-header">
              <h3 className="hrms-modal-title">Loan Repayment Schedule</h3>
              <button type="button" className="hrms-modal-close" onClick={() => setScheduleModalOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <div className="hrms-modal-body">
              <div style={{ backgroundColor: '#f8fafc', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span><strong>Principal:</strong> ₹{parseFloat(selectedSchedule.principal || 0).toLocaleString('en-IN')}</span>
                <span><strong>Monthly EMI:</strong> ₹{parseFloat(selectedSchedule.monthly_emi || 0).toLocaleString('en-IN')}</span>
                <span><strong>Balance:</strong> ₹{parseFloat(selectedSchedule.remaining_balance || 0).toLocaleString('en-IN')}</span>
              </div>

              <div className="hrms-table-container">
                <table className="hrms-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Installment Period</th>
                      <th>Deduction Amount</th>
                      <th>Remaining Balance</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(selectedSchedule.schedule || []).map((row) => (
                      <tr key={row.installment_no}>
                        <td>{row.installment_no}</td>
                        <td>{row.due_month}</td>
                        <td>₹{parseFloat(row.amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                        <td>₹{parseFloat(row.remaining_balance || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                        <td>
                          {row.status === 'Pending' ? (
                            <span className="hrms-badge hrms-badge-warning">Pending</span>
                          ) : (
                            <span className="hrms-badge hrms-badge-success">{row.status}</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="hrms-modal-footer">
              <button type="button" className="hrms-btn-secondary" onClick={() => setScheduleModalOpen(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
