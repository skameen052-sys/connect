import React, { useState, useEffect } from 'react';
import { 
  CreditCard, Plus, Clock, CheckCircle2, XCircle, 
  RefreshCw, DollarSign, X 
} from 'lucide-react';
import loanService from '../../services/loanService';

export default function EmployeeLoans() {
  const [loans, setLoans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isApplyModalOpen, setIsApplyModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const [formState, setFormState] = useState({
    loan_type: 'Salary Advance',
    principal_amount: 25000,
    term_months: 3,
    reason: 'Emergency medical expenses',
  });

  const fetchMyLoans = async () => {
    setLoading(true);
    try {
      const data = await loanService.getLoans();
      setLoans(data);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch personal loan requests.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMyLoans();
  }, []);

  const handleApplySubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await loanService.applyLoan({
        loan_type: formState.loan_type,
        principal_amount: parseFloat(formState.principal_amount),
        term_months: parseInt(formState.term_months, 10),
        reason: formState.reason,
      });
      setSuccessMsg('Loan application submitted for administrator review.');
      setIsApplyModalOpen(false);
      fetchMyLoans();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit loan application.');
    } finally {
      setSubmitting(false);
    }
  };

  const activeLoan = loans.find((l) => ['ACTIVE', 'APPROVED'].includes((l.status || '').toUpperCase()));

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
    return <span className="hrms-badge hrms-badge-warning"><Clock size={12} /> PENDING APPROVAL</span>;
  };

  return (
    <div className="hrms-page-container">
      {/* Header */}
      <div className="hrms-page-header">
        <div className="hrms-page-title-group">
          <h1><CreditCard size={28} className="text-forest" /> Loans & Salary Advances</h1>
          <p className="hrms-page-subtitle">
            Apply for emergency salary advances and personal loans with automated payroll installment deductions.
          </p>
        </div>

        <div className="hrms-actions-group">
          <button type="button" className="hrms-btn-secondary" onClick={fetchMyLoans} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
          <button type="button" className="hrms-btn-primary" onClick={() => setIsApplyModalOpen(true)}>
            <Plus size={16} /> Apply for Loan / Advance
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
            <span className="hrms-metric-label">Active Outstanding Balance</span>
            <div className="hrms-metric-icon-wrap"><DollarSign size={18} /></div>
          </div>
          <div className="hrms-metric-value">
            ₹{parseFloat(activeLoan?.remaining_balance || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <div className="hrms-metric-subtext">Remaining principal to be repaid</div>
        </div>

        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Monthly EMI Deduction</span>
            <div className="hrms-metric-icon-wrap"><CreditCard size={18} /></div>
          </div>
          <div className="hrms-metric-value">
            ₹{parseFloat(activeLoan?.monthly_installment || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <div className="hrms-metric-subtext">Deducted from next payroll</div>
        </div>

        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Applications Count</span>
            <div className="hrms-metric-icon-wrap"><Clock size={18} /></div>
          </div>
          <div className="hrms-metric-value">{loans.length}</div>
          <div className="hrms-metric-subtext">Total loans requested</div>
        </div>
      </div>

      {/* Table */}
      <div className="hrms-card">
        <div className="hrms-card-header">
          <h2 className="hrms-card-title"><CreditCard size={20} /> Loan Application History</h2>
        </div>

        <div className="hrms-table-container">
          <table className="hrms-table">
            <thead>
              <tr>
                <th>Loan Type</th>
                <th>Principal Amount</th>
                <th>Term</th>
                <th>Monthly Installment</th>
                <th>Remaining Balance</th>
                <th>Application Date</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {loans.length === 0 ? (
                <tr>
                  <td colSpan="7">
                    <div className="hrms-empty-state">
                      <CreditCard className="hrms-empty-icon" />
                      <p>You have not applied for any loans or salary advances.</p>
                      <button
                        type="button"
                        className="hrms-btn-primary"
                        style={{ marginTop: '0.75rem' }}
                        onClick={() => setIsApplyModalOpen(true)}
                      >
                        Apply Now
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                loans.map((l) => {
                  const lId = l.id || l._firestore_id;
                  return (
                    <tr key={lId}>
                      <td>
                        <strong>{l.loan_type}</strong>
                        <div className="hrms-metric-subtext">{l.reason}</div>
                      </td>
                      <td>₹{parseFloat(l.principal_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                      <td>{l.term_months} Months</td>
                      <td>₹{parseFloat(l.monthly_installment || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                      <td>
                        <strong style={{ color: parseFloat(l.remaining_balance || 0) > 0 ? '#b45309' : '#16a34a' }}>
                          ₹{parseFloat(l.remaining_balance || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </strong>
                      </td>
                      <td>{l.applied_date || l.created_at?.split('T')[0]}</td>
                      <td>{getStatusBadge(l.status)}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Apply Modal */}
      {isApplyModalOpen && (
        <div className="hrms-modal-overlay" onClick={() => setIsApplyModalOpen(false)}>
          <div className="hrms-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="hrms-modal-header">
              <h3 className="hrms-modal-title">Apply for Loan or Salary Advance</h3>
              <button type="button" className="hrms-modal-close" onClick={() => setIsApplyModalOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleApplySubmit}>
              <div className="hrms-modal-body">
                <div className="hrms-form-group">
                  <label>Loan Type *</label>
                  <select
                    className="hrms-select"
                    style={{ width: '100%' }}
                    value={formState.loan_type}
                    onChange={(e) => setFormState({ ...formState, loan_type: e.target.value })}
                  >
                    <option value="Salary Advance">Salary Advance (Short Term)</option>
                    <option value="Emergency Advance">Emergency Advance</option>
                    <option value="Personal Loan">Personal Loan (Extended Tenure)</option>
                    <option value="Education Loan">Education Loan</option>
                  </select>
                </div>

                <div className="hrms-form-row">
                  <div className="hrms-form-group">
                    <label>Principal Amount (₹) *</label>
                    <input
                      type="number"
                      className="hrms-input"
                      value={formState.principal_amount}
                      onChange={(e) => setFormState({ ...formState, principal_amount: e.target.value })}
                      min="1000"
                      step="500"
                      required
                    />
                  </div>

                  <div className="hrms-form-group">
                    <label>Repayment Tenure (Months) *</label>
                    <input
                      type="number"
                      className="hrms-input"
                      value={formState.term_months}
                      onChange={(e) => setFormState({ ...formState, term_months: e.target.value })}
                      min="1"
                      max="24"
                      required
                    />
                  </div>
                </div>

                {/* Real-time EMI preview */}
                <div style={{ backgroundColor: '#f0fdf4', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid #bbf7d0', marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem' }}>
                  <span>Estimated Monthly EMI Deduction:</span>
                  <strong style={{ color: '#134e4a' }}>
                    ₹{(parseFloat(formState.principal_amount) / (parseInt(formState.term_months, 10) || 1)).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} / mo
                  </strong>
                </div>

                <div className="hrms-form-group">
                  <label>Reason / Purpose *</label>
                  <textarea
                    rows="3"
                    className="hrms-input"
                    placeholder="Brief explanation for administration..."
                    value={formState.reason}
                    onChange={(e) => setFormState({ ...formState, reason: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="hrms-modal-footer">
                <button type="button" className="hrms-btn-secondary" onClick={() => setIsApplyModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="hrms-btn-primary" disabled={submitting}>
                  {submitting ? 'Submitting...' : 'Submit Application'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
