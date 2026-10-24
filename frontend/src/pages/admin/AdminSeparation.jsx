import React, { useState, useEffect } from 'react';
import { 
  UserMinus, CheckCircle2, Clock, Calculator, Download, 
  Search, RefreshCw, X, ShieldAlert, FileText 
} from 'lucide-react';
import separationService from '../../services/separationService';

export default function AdminSeparation() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  // Modals state
  const [approveModalOpen, setApproveModalOpen] = useState(false);
  const [selectedReq, setSelectedReq] = useState(null);
  const [approveForm, setApproveForm] = useState({
    approved_last_working_date: '',
    notice_shortfall_days: 0,
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
      setRequests(data);
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
      notes: 'Approved standard resignation with notice period',
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
      setSuccessMsg('Resignation approved. You can now calculate Full & Final Settlement.');
      setApproveModalOpen(false);
      fetchRequests();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to approve resignation.');
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
      setSuccessMsg(`FnF calculated. Net Settlement: ₹${parseFloat(res.calculation.net_settlement || 0).toLocaleString('en-IN')}`);
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
    return <span className="hrms-badge hrms-badge-warning"><Clock size={12} /> PENDING NOTICE</span>;
  };

  return (
    <div className="hrms-page-container">
      {/* Header */}
      <div className="hrms-page-header">
        <div className="hrms-page-title-group">
          <h1><UserMinus size={28} className="text-forest" /> Resignation & FnF Settlement</h1>
          <p className="hrms-page-subtitle">
            Manage employee separations, track notice periods, and compute automated Full & Final (FnF) settlements with statement generation.
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
            <span className="hrms-metric-label">Separation Requests</span>
            <div className="hrms-metric-icon-wrap"><UserMinus size={18} /></div>
          </div>
          <div className="hrms-metric-value">{requests.length}</div>
          <div className="hrms-metric-subtext">Total recorded separations</div>
        </div>

        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Settled & Closed</span>
            <div className="hrms-metric-icon-wrap"><CheckCircle2 size={18} /></div>
          </div>
          <div className="hrms-metric-value">
            {requests.filter((r) => (r.status || '').toUpperCase() === 'SETTLED').length}
          </div>
          <div className="hrms-metric-subtext">Full & Final completed</div>
        </div>

        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">In Notice Period</span>
            <div className="hrms-metric-icon-wrap" style={{ color: '#d97706', backgroundColor: '#fef3c7' }}><Clock size={18} /></div>
          </div>
          <div className="hrms-metric-value" style={{ color: '#d97706' }}>
            {requests.filter((r) => ['SUBMITTED', 'APPROVED'].includes((r.status || '').toUpperCase())).length}
          </div>
          <div className="hrms-metric-subtext">Active handovers in progress</div>
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
                placeholder="Search by employee name or reason..."
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
              <option value="SUBMITTED">Pending Notice</option>
              <option value="APPROVED">Approved (Awaiting FnF)</option>
              <option value="SETTLED">Settled & Statement Issued</option>
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
                        <span style={{ fontSize: '0.8rem', color: '#64748b' }}>{r.reason}</span>
                      </td>
                      <td>{getStatusBadge(r.status)}</td>
                      <td>
                        {r.fnf_settlement ? (
                          <strong style={{ color: '#134e4a' }}>
                            ₹{parseFloat(r.fnf_settlement.net_settlement || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                          </strong>
                        ) : (
                          <span style={{ color: '#94a3b8' }}>Pending Calculation</span>
                        )}
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          {status === 'SUBMITTED' && (
                            <button
                              type="button"
                              className="hrms-btn-primary"
                              style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
                              onClick={() => handleOpenApprove(r)}
                            >
                              Approve
                            </button>
                          )}

                          {status === 'APPROVED' && (
                            <button
                              type="button"
                              className="hrms-btn-primary"
                              style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem', backgroundColor: '#0f766e' }}
                              onClick={() => handleOpenFnF(r)}
                            >
                              <Calculator size={13} /> Run FnF
                            </button>
                          )}

                          {status === 'SETTLED' && (
                            <button
                              type="button"
                              className="hrms-btn-outline-green"
                              style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
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

      {/* Approve Modal */}
      {approveModalOpen && selectedReq && (
        <div className="hrms-modal-overlay" onClick={() => setApproveModalOpen(false)}>
          <div className="hrms-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="hrms-modal-header">
              <h3 className="hrms-modal-title">Approve Resignation ({selectedReq.employee_name})</h3>
              <button type="button" className="hrms-modal-close" onClick={() => setApproveModalOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleApproveSubmit}>
              <div className="hrms-modal-body">
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
                    className="hrms-input"
                    value={approveForm.notice_shortfall_days}
                    onChange={(e) => setApproveForm({ ...approveForm, notice_shortfall_days: e.target.value })}
                    min="0"
                    placeholder="0"
                  />
                  <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                    Days of shortfall will be deducted during final settlement based on daily gross salary.
                  </span>
                </div>

                <div className="hrms-form-group">
                  <label>HR Approval Notes</label>
                  <textarea
                    rows="2"
                    className="hrms-input"
                    value={approveForm.notes}
                    onChange={(e) => setApproveForm({ ...approveForm, notes: e.target.value })}
                  />
                </div>
              </div>

              <div className="hrms-modal-footer">
                <button type="button" className="hrms-btn-secondary" onClick={() => setApproveModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="hrms-btn-primary" disabled={actionLoading}>
                  {actionLoading ? 'Approving...' : 'Confirm Approval'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* FnF Calculator Modal */}
      {fnfModalOpen && selectedReq && (
        <div className="hrms-modal-overlay" onClick={() => setFnfModalOpen(false)}>
          <div className="hrms-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="hrms-modal-header">
              <h3 className="hrms-modal-title">Compute Full & Final Settlement</h3>
              <button type="button" className="hrms-modal-close" onClick={() => setFnfModalOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleFnFSubmit}>
              <div className="hrms-modal-body">
                <p style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '1.25rem' }}>
                  Calculates prorated final month earnings, leave encashment, statutory gratuity, notice period recoveries, and nets any outstanding loan balances.
                </p>

                <div className="hrms-form-row">
                  <div className="hrms-form-group">
                    <label>Days Worked in Final Month</label>
                    <input
                      type="number"
                      className="hrms-input"
                      value={fnfForm.days_worked_in_final_month}
                      onChange={(e) => setFnfForm({ ...fnfForm, days_worked_in_final_month: e.target.value })}
                      min="0"
                      max="31"
                      required
                    />
                  </div>

                  <div className="hrms-form-group">
                    <label>Accrued Leave Encashment Days</label>
                    <input
                      type="number"
                      className="hrms-input"
                      value={fnfForm.accrued_unused_leaves}
                      onChange={(e) => setFnfForm({ ...fnfForm, accrued_unused_leaves: e.target.value })}
                      min="0"
                    />
                  </div>
                </div>

                <div className="hrms-form-row">
                  <div className="hrms-form-group">
                    <label>Other Additions / Bonus (₹)</label>
                    <input
                      type="number"
                      className="hrms-input"
                      value={fnfForm.other_additions}
                      onChange={(e) => setFnfForm({ ...fnfForm, other_additions: e.target.value })}
                    />
                  </div>

                  <div className="hrms-form-group">
                    <label>Other Deductions / Recoveries (₹)</label>
                    <input
                      type="number"
                      className="hrms-input"
                      value={fnfForm.other_deductions}
                      onChange={(e) => setFnfForm({ ...fnfForm, other_deductions: e.target.value })}
                    />
                  </div>
                </div>
              </div>

              <div className="hrms-modal-footer">
                <button type="button" className="hrms-btn-secondary" onClick={() => setFnfModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="hrms-btn-primary" disabled={actionLoading}>
                  {actionLoading ? 'Calculating...' : 'Settle & Issue Statement'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
