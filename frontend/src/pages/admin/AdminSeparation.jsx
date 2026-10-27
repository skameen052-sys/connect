import React, { useState, useEffect } from 'react';
import { 
  UserMinus, CheckCircle2, Clock, Calculator, Download, 
  Search, RefreshCw, X, ShieldAlert, FileText, XCircle, AlertCircle 
} from 'lucide-react';
import separationService from '../../services/separationService';

export default function AdminSeparation() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  // Modals state
  const [approveModalOpen, setApproveModalOpen] = useState(false);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [selectedReq, setSelectedReq] = useState(null);

  const [approveForm, setApproveForm] = useState({
    approved_last_working_date: '',
    notice_shortfall_days: 0,
    notes: '',
  });

  const [rejectForm, setRejectForm] = useState({
    rejection_reason: '',
    notes: '',
  });

  const [fnfModalOpen, setFnfModalOpen] = useState(false);
  const [fnfForm, setFnfForm] = useState({
    days_worked_in_final_month: 20,
    accrued_unused_leaves: 8,
    other_additions: 0,
    other_deductions: 0,
  });

  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const fetchRequests = async () => {
    setLoading(true);
    try {
      const data = await separationService.getRequests();
      setRequests(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch separation requests.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const handleOpenApprove = (req) => {
    setSelectedReq(req);
    setApproveForm({
      approved_last_working_date: req.intended_last_date || new Date().toISOString().split('T')[0],
      notice_shortfall_days: 0,
      notes: 'Approved standard resignation with notice period handover.',
    });
    setApproveModalOpen(true);
  };

  const handleApproveSubmit = async (e) => {
    e.preventDefault();
    setActionLoading(true);
    setError(null);
    try {
      await separationService.approveResignation(selectedReq.id || selectedReq._firestore_id, {
        approved_last_working_date: approveForm.approved_last_working_date,
        notice_shortfall_days: parseFloat(approveForm.notice_shortfall_days) || 0,
        notes: approveForm.notes,
      });
      setSuccessMsg(`Resignation for ${selectedReq.employee_name || selectedReq.employee_id} approved successfully.`);
      setApproveModalOpen(false);
      fetchRequests();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to approve resignation.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleOpenReject = (req) => {
    setSelectedReq(req);
    setRejectForm({
      rejection_reason: '',
      notes: '',
    });
    setRejectModalOpen(true);
  };

  const handleRejectSubmit = async (e) => {
    e.preventDefault();
    if (!rejectForm.rejection_reason.trim()) {
      setError('Please provide a formal rejection reason.');
      return;
    }
    setActionLoading(true);
    setError(null);
    try {
      await separationService.rejectResignation(selectedReq.id || selectedReq._firestore_id, {
        rejection_reason: rejectForm.rejection_reason.trim(),
        notes: rejectForm.notes.trim() || rejectForm.rejection_reason.trim(),
      });
      setSuccessMsg(`Resignation for ${selectedReq.employee_name || selectedReq.employee_id} has been rejected.`);
      setRejectModalOpen(false);
      fetchRequests();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to reject resignation.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleOpenFnF = (req) => {
    setSelectedReq(req);
    setFnfForm({
      days_worked_in_final_month: 22,
      accrued_unused_leaves: 5,
      other_additions: 0,
      other_deductions: 0,
    });
    setFnfModalOpen(true);
  };

  const handleFnFSubmit = async (e) => {
    e.preventDefault();
    setActionLoading(true);
    setError(null);
    try {
      const res = await separationService.calculateFnF(selectedReq.id || selectedReq._firestore_id, {
        days_worked_in_final_month: parseFloat(fnfForm.days_worked_in_final_month) || 0,
        accrued_unused_leaves: parseFloat(fnfForm.accrued_unused_leaves) || 0,
        other_additions: parseFloat(fnfForm.other_additions) || 0,
        other_deductions: parseFloat(fnfForm.other_deductions) || 0,
      });
      setSuccessMsg(`FnF calculated. Net Settlement: ₹${parseFloat(res.calculation?.net_settlement || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`);
      setFnfModalOpen(false);
      fetchRequests();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to calculate FnF settlement.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDownloadStatement = async (separationId, empId) => {
    try {
      await separationService.downloadStatementPdf(separationId, `FnF_Statement_${empId}.pdf`);
    } catch (err) {
      alert('Could not download FnF Statement PDF.');
    }
  };

  const filteredRequests = requests.filter((r) => {
    const matchesSearch =
      (r.employee_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (r.employee_id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (r.reason || '').toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || (r.status || '').toUpperCase() === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getStatusBadge = (status) => {
    const s = (status || 'SUBMITTED').toUpperCase();
    if (s === 'SETTLED') {
      return <span className="hrms-badge hrms-badge-success"><CheckCircle2 size={12} /> SETTLED</span>;
    }
    if (s === 'APPROVED') {
      return <span className="hrms-badge hrms-badge-info"><CheckCircle2 size={12} /> APPROVED</span>;
    }
    if (s === 'REJECTED') {
      return <span className="hrms-badge" style={{ backgroundColor: '#fee2e2', color: '#b91c1c', border: '1px solid #fca5a5' }}><XCircle size={12} /> REJECTED</span>;
    }
    return <span className="hrms-badge hrms-badge-warning"><Clock size={12} /> PENDING NOTICE</span>;
  };

  const pendingCount = requests.filter((r) => (r.status || '').toUpperCase() === 'SUBMITTED').length;
  const approvedCount = requests.filter((r) => (r.status || '').toUpperCase() === 'APPROVED').length;
  const settledCount = requests.filter((r) => (r.status || '').toUpperCase() === 'SETTLED').length;
  const rejectedCount = requests.filter((r) => (r.status || '').toUpperCase() === 'REJECTED').length;

  return (
    <div className="hrms-page-container">
      {/* Header */}
      <div className="hrms-page-header">
        <div className="hrms-page-title-group">
          <h1><UserMinus size={28} className="text-forest" /> Resignation & FnF Settlement</h1>
          <p className="hrms-page-subtitle">
            Manage employee separations, track notice periods, accept or reject resignations, and compute automated Full & Final (FnF) settlements.
          </p>
        </div>

        <div className="hrms-actions-group">
          <button type="button" className="hrms-btn-secondary" onClick={fetchRequests} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="hrms-card" style={{ borderColor: '#fca5a5', backgroundColor: '#fef2f2', padding: '1rem', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#991b1b' }}>
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        </div>
      )}

      {successMsg && (
        <div className="hrms-card" style={{ borderColor: '#86efac', backgroundColor: '#f0fdf4', padding: '1rem', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#166534' }}>
            <CheckCircle2 size={18} />
            <span>{successMsg}</span>
          </div>
        </div>
      )}

      {/* Metrics */}
      <div className="hrms-metrics-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Separation Requests</span>
            <div className="hrms-metric-icon-wrap"><UserMinus size={18} /></div>
          </div>
          <div className="hrms-metric-value">{requests.length}</div>
          <div className="hrms-metric-subtext">Total recorded separations</div>
        </div>

        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Pending Review</span>
            <div className="hrms-metric-icon-wrap" style={{ color: '#d97706', backgroundColor: '#fef3c7' }}><Clock size={18} /></div>
          </div>
          <div className="hrms-metric-value" style={{ color: '#d97706' }}>{pendingCount}</div>
          <div className="hrms-metric-subtext">Awaiting admin accept/reject</div>
        </div>

        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">In Notice Period</span>
            <div className="hrms-metric-icon-wrap" style={{ color: '#0284c7', backgroundColor: '#e0f2fe' }}><CheckCircle2 size={18} /></div>
          </div>
          <div className="hrms-metric-value" style={{ color: '#0284c7' }}>{approvedCount}</div>
          <div className="hrms-metric-subtext">Approved handovers active</div>
        </div>

        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Settled & Closed</span>
            <div className="hrms-metric-icon-wrap"><CheckCircle2 size={18} /></div>
          </div>
          <div className="hrms-metric-value">{settledCount}</div>
          <div className="hrms-metric-subtext">Full & Final completed</div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="hrms-card">
        <div className="hrms-card-body" style={{ padding: '1rem 1.5rem' }}>
          <div className="hrms-filter-bar" style={{ margin: 0, display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
            <div className="hrms-search-input-wrap" style={{ flex: 1, minWidth: '240px' }}>
              <Search size={16} />
              <input
                type="text"
                className="hrms-input"
                placeholder="Search by employee name, ID or reason..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            <select
              className="hrms-select"
              style={{ minWidth: '200px' }}
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="ALL">All Statuses ({requests.length})</option>
              <option value="SUBMITTED">Pending Notice ({pendingCount})</option>
              <option value="APPROVED">Approved (Awaiting FnF) ({approvedCount})</option>
              <option value="REJECTED">Rejected ({rejectedCount})</option>
              <option value="SETTLED">Settled & Statement Issued ({settledCount})</option>
            </select>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="hrms-card">
        <div className="hrms-table-container">
          <table className="hrms-table">
            <thead>
              <tr>
                <th>Employee</th>
                <th>Resignation Date</th>
                <th>Last Working Date</th>
                <th>Notice Period</th>
                <th>Reason</th>
                <th>Status</th>
                <th>FnF Settlement</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredRequests.length === 0 ? (
                <tr>
                  <td colSpan="8">
                    <div className="hrms-empty-state">
                      <UserMinus className="hrms-empty-icon" />
                      <p>No resignation or separation records found.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredRequests.map((r) => {
                  const rId = r.id || r._firestore_id;
                  const status = (r.status || '').toUpperCase();
                  return (
                    <tr key={rId}>
                      <td>
                        <strong>{r.employee_name || r.employee_id}</strong>
                        <div className="hrms-metric-subtext">{r.employee_id} • {r.department}</div>
                      </td>
                      <td>{r.resignation_date || r.created_at?.split('T')[0]}</td>
                      <td>
                        <strong>{r.last_working_date || r.intended_last_date}</strong>
                      </td>
                      <td>{r.notice_period_days || 30} Days</td>
                      <td>
                        <span style={{ fontSize: '0.8rem', color: '#475569' }}>{r.reason}</span>
                        {status === 'REJECTED' && r.rejection_reason && (
                          <div style={{ fontSize: '0.75rem', color: '#dc2626', marginTop: '2px', fontStyle: 'italic' }}>
                            Declined: {r.rejection_reason}
                          </div>
                        )}
                      </td>
                      <td>{getStatusBadge(r.status)}</td>
                      <td>
                        {r.fnf_settlement ? (
                          <strong style={{ color: '#134e4a' }}>
                            ₹{parseFloat(r.fnf_settlement.net_settlement || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                          </strong>
                        ) : (
                          <span style={{ color: '#94a3b8' }}>
                            {status === 'REJECTED' ? 'N/A' : 'Pending Calculation'}
                          </span>
                        )}
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                          {status === 'SUBMITTED' && (
                            <>
                              <button
                                type="button"
                                className="hrms-btn-primary"
                                style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                                onClick={() => handleOpenApprove(r)}
                                title="Accept & Approve Resignation"
                              >
                                <CheckCircle2 size={13} /> Accept
                              </button>
                              <button
                                type="button"
                                style={{
                                  backgroundColor: '#ef4444',
                                  color: '#ffffff',
                                  border: 'none',
                                  padding: '0.35rem 0.65rem',
                                  borderRadius: '6px',
                                  fontSize: '0.75rem',
                                  fontWeight: 600,
                                  cursor: 'pointer',
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '4px',
                                }}
                                onClick={() => handleOpenReject(r)}
                                title="Reject Resignation Request"
                              >
                                <XCircle size={13} /> Reject
                              </button>
                            </>
                          )}

                          {status === 'APPROVED' && (
                            <>
                              <button
                                type="button"
                                className="hrms-btn-primary"
                                style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem', backgroundColor: '#0f766e', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                                onClick={() => handleOpenFnF(r)}
                              >
                                <Calculator size={13} /> Run FnF
                              </button>
                              <button
                                type="button"
                                style={{
                                  backgroundColor: '#fee2e2',
                                  color: '#b91c1c',
                                  border: '1px solid #fecaca',
                                  padding: '0.35rem 0.65rem',
                                  borderRadius: '6px',
                                  fontSize: '0.75rem',
                                  fontWeight: 600,
                                  cursor: 'pointer',
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '4px',
                                }}
                                onClick={() => handleOpenReject(r)}
                                title="Cancel approval and reject resignation"
                              >
                                <XCircle size={13} /> Reject
                              </button>
                            </>
                          )}

                          {status === 'REJECTED' && (
                            <button
                              type="button"
                              className="hrms-btn-secondary"
                              style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                              onClick={() => handleOpenApprove(r)}
                              title="Reconsider and approve resignation"
                            >
                              <CheckCircle2 size={13} /> Re-evaluate
                            </button>
                          )}

                          {status === 'SETTLED' && (
                            <button
                              type="button"
                              className="hrms-btn-outline-green"
                              style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                              onClick={() => handleDownloadStatement(rId, r.employee_id)}
                              title="Download official statement PDF"
                            >
                              <Download size={13} /> Statement PDF
                            </button>
                          )}
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

      {/* Approve / Accept Modal */}
      {approveModalOpen && selectedReq && (
        <div className="hrms-modal-overlay" onClick={() => setApproveModalOpen(false)}>
          <div 
            className="hrms-modal-content" 
            style={{ maxHeight: '90vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="hrms-modal-header" style={{ flexShrink: 0 }}>
              <h3 className="hrms-modal-title">Approve Resignation ({selectedReq.employee_name})</h3>
              <button type="button" className="hrms-modal-close" onClick={() => setApproveModalOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <form 
              onSubmit={handleApproveSubmit}
              style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, overflow: 'hidden', margin: 0 }}
            >
              <div className="hrms-modal-body" style={{ overflowY: 'auto', flex: 1, padding: '1.25rem 1.5rem' }}>
                <div style={{ backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', padding: '12px', marginBottom: '16px' }}>
                  <div style={{ fontSize: '0.85rem', color: '#166534', fontWeight: 600 }}>
                    Accepting formal resignation for {selectedReq.employee_name} ({selectedReq.employee_id})
                  </div>
                  <div style={{ fontSize: '0.78rem', color: '#4b5563', marginTop: '2px' }}>
                    Reason on record: "{selectedReq.reason}"
                  </div>
                </div>

                <div className="hrms-form-group">
                  <label>Official Last Working Date *</label>
                  <input
                    type="date"
                    className="hrms-input"
                    value={approveForm.approved_last_working_date}
                    onChange={(e) => setApproveForm({ ...approveForm, approved_last_working_date: e.target.value })}
                    required
                  />
                </div>

                <div className="hrms-form-group">
                  <label>Notice Shortfall Days (If Early Release)</label>
                  <input
                    type="number"
                    step="0.5"
                    className="hrms-input"
                    value={approveForm.notice_shortfall_days}
                    onChange={(e) => setApproveForm({ ...approveForm, notice_shortfall_days: e.target.value })}
                    min="0"
                    placeholder="0"
                  />
                  <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                    Shortfall days will be deducted during final settlement based on daily gross salary.
                  </span>
                </div>

                <div className="hrms-form-group" style={{ marginBottom: 0 }}>
                  <label>HR Approval Notes & Handover Instructions</label>
                  <textarea
                    rows="3"
                    className="hrms-input"
                    value={approveForm.notes}
                    onChange={(e) => setApproveForm({ ...approveForm, notes: e.target.value })}
                    placeholder="e.g. Approved standard handover. Hand over laptop & access cards by last date."
                  />
                </div>
              </div>

              <div 
                className="hrms-modal-footer" 
                style={{ flexShrink: 0, padding: '1rem 1.5rem', borderTop: '1px solid #e2e8f0', backgroundColor: '#f8fafc', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}
              >
                <button type="button" className="hrms-btn-secondary" onClick={() => setApproveModalOpen(false)}>
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="hrms-btn-primary" 
                  style={{ minWidth: '160px', fontWeight: 700, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
                  disabled={actionLoading}
                >
                  <CheckCircle2 size={16} />
                  {actionLoading ? 'Submitting...' : 'Submit Approval'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reject Modal */}
      {rejectModalOpen && selectedReq && (
        <div className="hrms-modal-overlay" onClick={() => setRejectModalOpen(false)}>
          <div 
            className="hrms-modal-content" 
            style={{ maxHeight: '90vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="hrms-modal-header" style={{ flexShrink: 0 }}>
              <h3 className="hrms-modal-title" style={{ color: '#b91c1c' }}>
                Reject Resignation ({selectedReq.employee_name})
              </h3>
              <button type="button" className="hrms-modal-close" onClick={() => setRejectModalOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <form 
              onSubmit={handleRejectSubmit}
              style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, overflow: 'hidden', margin: 0 }}
            >
              <div className="hrms-modal-body" style={{ overflowY: 'auto', flex: 1, padding: '1.25rem 1.5rem' }}>
                <div style={{ backgroundColor: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', padding: '12px', marginBottom: '16px' }}>
                  <div style={{ fontSize: '0.85rem', color: '#991b1b', fontWeight: 600 }}>
                    Rejecting formal resignation for {selectedReq.employee_name} ({selectedReq.employee_id})
                  </div>
                  <div style={{ fontSize: '0.78rem', color: '#7f1d1d', marginTop: '2px' }}>
                    This decision will be communicated directly to the employee's dashboard.
                  </div>
                </div>

                <div className="hrms-form-group">
                  <label>Formal Reason for Rejection *</label>
                  <textarea
                    rows="3"
                    className="hrms-input"
                    placeholder="Specify official justification (e.g. Critical project delivery underway; contract minimum service commitment required; discussion requested with department head)..."
                    value={rejectForm.rejection_reason}
                    onChange={(e) => setRejectForm({ ...rejectForm, rejection_reason: e.target.value })}
                    required
                  />
                </div>

                <div className="hrms-form-group" style={{ marginBottom: 0 }}>
                  <label>Internal HR Notes (Optional)</label>
                  <textarea
                    rows="2"
                    className="hrms-input"
                    placeholder="Additional confidential notes for HR records..."
                    value={rejectForm.notes}
                    onChange={(e) => setRejectForm({ ...rejectForm, notes: e.target.value })}
                  />
                </div>
              </div>

              <div 
                className="hrms-modal-footer" 
                style={{ flexShrink: 0, padding: '1rem 1.5rem', borderTop: '1px solid #e2e8f0', backgroundColor: '#f8fafc', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}
              >
                <button type="button" className="hrms-btn-secondary" onClick={() => setRejectModalOpen(false)}>
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{
                    backgroundColor: '#dc2626',
                    color: '#ffffff',
                    border: 'none',
                    padding: '0.625rem 1.25rem',
                    borderRadius: '8px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                  disabled={actionLoading}
                >
                  <XCircle size={16} />
                  {actionLoading ? 'Submitting...' : 'Submit Rejection'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* FnF Calculator Modal */}
      {fnfModalOpen && selectedReq && (
        <div className="hrms-modal-overlay" onClick={() => setFnfModalOpen(false)}>
          <div 
            className="hrms-modal-content" 
            style={{ maxHeight: '90vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="hrms-modal-header" style={{ flexShrink: 0 }}>
              <h3 className="hrms-modal-title">Calculate FnF Settlement ({selectedReq.employee_name})</h3>
              <button type="button" className="hrms-modal-close" onClick={() => setFnfModalOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <form 
              onSubmit={handleFnFSubmit}
              style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, overflow: 'hidden', margin: 0 }}
            >
              <div className="hrms-modal-body" style={{ overflowY: 'auto', flex: 1, padding: '1.25rem 1.5rem' }}>
                <p style={{ fontSize: '0.825rem', color: '#64748b', marginBottom: '1.25rem' }}>
                  The engine will automatically pull active salary structures, prorate the final month pay, encash accrued unused leaves, compute gratuity, recover notice shortfalls, and deduct any active loans.
                </p>

                <div className="hrms-form-row">
                  <div className="hrms-form-group">
                    <label>Days Worked in Final Month *</label>
                    <input
                      type="number"
                      step="0.5"
                      min="0"
                      max="31"
                      className="hrms-input"
                      value={fnfForm.days_worked_in_final_month}
                      onChange={(e) => setFnfForm({ ...fnfForm, days_worked_in_final_month: e.target.value })}
                      required
                    />
                  </div>

                  <div className="hrms-form-group">
                    <label>Accrued Unused Leaves (Days)</label>
                    <input
                      type="number"
                      step="0.5"
                      min="0"
                      className="hrms-input"
                      value={fnfForm.accrued_unused_leaves}
                      onChange={(e) => setFnfForm({ ...fnfForm, accrued_unused_leaves: e.target.value })}
                    />
                  </div>
                </div>

                <div className="hrms-form-row">
                  <div className="hrms-form-group">
                    <label>Other Settlement Additions (₹)</label>
                    <input
                      type="number"
                      step="1"
                      min="0"
                      className="hrms-input"
                      value={fnfForm.other_additions}
                      onChange={(e) => setFnfForm({ ...fnfForm, other_additions: e.target.value })}
                      placeholder="e.g. Expense reimbursements"
                    />
                  </div>

                  <div className="hrms-form-group" style={{ marginBottom: 0 }}>
                    <label>Other Deductions (₹)</label>
                    <input
                      type="number"
                      step="1"
                      min="0"
                      className="hrms-input"
                      value={fnfForm.other_deductions}
                      onChange={(e) => setFnfForm({ ...fnfForm, other_deductions: e.target.value })}
                      placeholder="e.g. Asset damage recovery"
                    />
                  </div>
                </div>
              </div>

              <div 
                className="hrms-modal-footer" 
                style={{ flexShrink: 0, padding: '1rem 1.5rem', borderTop: '1px solid #e2e8f0', backgroundColor: '#f8fafc', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}
              >
                <button type="button" className="hrms-btn-secondary" onClick={() => setFnfModalOpen(false)}>
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="hrms-btn-primary" 
                  style={{ minWidth: '160px', fontWeight: 700, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
                  disabled={actionLoading}
                >
                  <Calculator size={16} />
                  {actionLoading ? 'Calculating...' : 'Submit Settlement'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
