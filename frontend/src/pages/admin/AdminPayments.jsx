import React, { useState, useEffect } from 'react';
import { 
  DollarSign, Download, CheckCircle2, Clock, AlertTriangle, 
  Search, RefreshCw, X, ShieldCheck, CreditCard 
} from 'lucide-react';
import paymentService from '../../services/paymentService';

export default function AdminPayments() {
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [selectedPaymentIds, setSelectedPaymentIds] = useState([]);
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);
  const [confirmForm, setConfirmForm] = useState({
    transaction_reference: '',
    payment_date: new Date().toISOString().split('T')[0],
    notes: 'Direct Bank NEFT Corporate Bulk Disbursement',
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const fetchPayments = async () => {
    setLoading(true);
    try {
      const data = await paymentService.getAllPayments();
      setPayments(data);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch payment disbursement records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPayments();
  }, []);

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedPaymentIds(filteredPayments.map((p) => p.id || p._firestore_id));
    } else {
      setSelectedPaymentIds([]);
    }
  };

  const handleSelectOne = (id) => {
    setSelectedPaymentIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handleConfirmSubmit = async (e) => {
    e.preventDefault();
    if (!selectedPaymentIds.length) {
      alert('Please select at least one employee payment record.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await paymentService.confirmPayments({
        payment_ids: selectedPaymentIds,
        transaction_reference: confirmForm.transaction_reference,
        payment_date: confirmForm.payment_date,
        status: 'Paid',
        notes: confirmForm.notes,
      });
      setSuccessMsg(`Recorded payment confirmation for ${selectedPaymentIds.length} records.`);
      setIsConfirmModalOpen(false);
      setSelectedPaymentIds([]);
      fetchPayments();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to record payment confirmations.');
    } finally {
      setSubmitting(false);
    }
  };

  const filteredPayments = payments.filter((p) => {
    const matchesSearch =
      (p.employee_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.employee_id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.payment_reference || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.transaction_reference || '').toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || (p.status || '').toUpperCase() === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const totalPaid = payments
    .filter((p) => (p.status || '').toLowerCase() === 'paid')
    .reduce((acc, p) => acc + (parseFloat(p.amount) || 0), 0);

  const totalPending = payments
    .filter((p) => (p.status || '').toLowerCase() !== 'paid')
    .reduce((acc, p) => acc + (parseFloat(p.amount) || 0), 0);

  const getStatusBadge = (status) => {
    const s = (status || 'Approved').toUpperCase();
    if (s === 'PAID') {
      return <span className="hrms-badge hrms-badge-success"><CheckCircle2 size={12} /> PAID</span>;
    }
    if (s === 'PROCESSING') {
      return <span className="hrms-badge hrms-badge-warning"><Clock size={12} /> PROCESSING</span>;
    }
    if (s === 'FAILED') {
      return <span className="hrms-badge hrms-badge-danger"><AlertTriangle size={12} /> FAILED</span>;
    }
    return <span className="hrms-badge hrms-badge-info"><Clock size={12} /> APPROVED</span>;
  };

  return (
    <div className="hrms-page-container">
      {/* Header */}
      <div className="hrms-page-header">
        <div className="hrms-page-title-group">
          <h1><CreditCard size={28} className="text-forest" /> Salary Payment Disbursements</h1>
          <p className="hrms-page-subtitle">
            Track bank disbursements, export corporate batch files, and record bank transaction reference numbers (UTR).
          </p>
        </div>

        <div className="hrms-actions-group">
          <button type="button" className="hrms-btn-secondary" onClick={fetchPayments} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>

          {selectedPaymentIds.length > 0 && (
            <button
              type="button"
              className="hrms-btn-primary"
              onClick={() => setIsConfirmModalOpen(true)}
            >
              <ShieldCheck size={16} /> Confirm Selected ({selectedPaymentIds.length})
            </button>
          )}
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
            <span className="hrms-metric-label">Confirmed Disbursed</span>
            <div className="hrms-metric-icon-wrap"><CheckCircle2 size={18} /></div>
          </div>
          <div className="hrms-metric-value">₹{totalPaid.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
          <div className="hrms-metric-subtext">UTR verified salary transfers</div>
        </div>

        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Pending / Processing</span>
            <div className="hrms-metric-icon-wrap" style={{ color: '#d97706', backgroundColor: '#fef3c7' }}><Clock size={18} /></div>
          </div>
          <div className="hrms-metric-value" style={{ color: '#d97706' }}>₹{totalPending.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
          <div className="hrms-metric-subtext">Awaiting bank reconciliation</div>
        </div>

        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Total Transactions</span>
            <div className="hrms-metric-icon-wrap"><DollarSign size={18} /></div>
          </div>
          <div className="hrms-metric-value">{payments.length}</div>
          <div className="hrms-metric-subtext">Disbursement queue records</div>
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
                placeholder="Search by employee, reference or UTR..."
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
              <option value="PAID">Paid</option>
              <option value="APPROVED">Approved (Pending)</option>
              <option value="PROCESSING">Processing</option>
              <option value="FAILED">Failed</option>
            </select>
          </div>
        </div>
      </div>

      {/* Payments Table */}
      <div className="hrms-card">
        <div className="hrms-table-container">
          <table className="hrms-table">
            <thead>
              <tr>
                <th style={{ width: '40px' }}>
                  <input
                    type="checkbox"
                    onChange={handleSelectAll}
                    checked={filteredPayments.length > 0 && selectedPaymentIds.length === filteredPayments.length}
                  />
                </th>
                <th>Employee</th>
                <th>Bank & Account</th>
                <th>Amount Payable</th>
                <th>Disbursement Mode</th>
                <th>Status</th>
                <th>UTR Reference</th>
                <th>Payment Date</th>
              </tr>
            </thead>
            <tbody>
              {filteredPayments.length === 0 ? (
                <tr>
                  <td colSpan="8">
                    <div className="hrms-empty-state">
                      <CreditCard className="hrms-empty-icon" />
                      <p>No payment disbursement records found.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredPayments.map((p) => {
                  const pId = p.id || p._firestore_id;
                  const isChecked = selectedPaymentIds.includes(pId);
                  return (
                    <tr key={pId}>
                      <td>
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => handleSelectOne(pId)}
                        />
                      </td>
                      <td>
                        <strong>{p.employee_name}</strong>
                        <div className="hrms-metric-subtext">{p.employee_id} • Ref: {p.payment_reference}</div>
                      </td>
                      <td>
                        <strong>{p.bank_name || 'HDFC Bank'}</strong>
                        <div className="hrms-metric-subtext">{p.account_number || 'XXXX-XXXX-XXXX'}</div>
                      </td>
                      <td>
                        <strong style={{ color: '#134e4a', fontSize: '0.95rem' }}>
                          ₹{parseFloat(p.amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </strong>
                      </td>
                      <td>{p.payment_method || 'Bank Transfer (NEFT)'}</td>
                      <td>{getStatusBadge(p.status)}</td>
                      <td>
                        {p.transaction_reference ? (
                          <span style={{ fontFamily: 'monospace', fontWeight: '600', color: '#166534' }}>
                            {p.transaction_reference}
                          </span>
                        ) : (
                          <span style={{ color: '#94a3b8' }}>Pending UTR</span>
                        )}
                      </td>
                      <td>{p.payment_date || p.created_at?.split('T')[0]}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Confirm Modal */}
      {isConfirmModalOpen && (
        <div className="hrms-modal-overlay" onClick={() => setIsConfirmModalOpen(false)}>
          <div className="hrms-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="hrms-modal-header">
              <h3 className="hrms-modal-title">Record Bank Payment Confirmation</h3>
              <button type="button" className="hrms-modal-close" onClick={() => setIsConfirmModalOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleConfirmSubmit}>
              <div className="hrms-modal-body">
                <p style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '1.25rem' }}>
                  Entering the bank UTR confirmation reference marks {selectedPaymentIds.length} salary payment records as officially disbursed and reconciles the payroll run.
                </p>

                <div className="hrms-form-group">
                  <label>Bank Transaction Reference (UTR Number) *</label>
                  <input
                    type="text"
                    className="hrms-input"
                    placeholder="e.g. HDFCN26102398471"
                    value={confirmForm.transaction_reference}
                    onChange={(e) => setConfirmForm({ ...confirmForm, transaction_reference: e.target.value })}
                    required
                  />
                </div>

                <div className="hrms-form-group">
                  <label>Payment Settlement Date</label>
                  <input
                    type="date"
                    className="hrms-input"
                    value={confirmForm.payment_date}
                    onChange={(e) => setConfirmForm({ ...confirmForm, payment_date: e.target.value })}
                    required
                  />
                </div>

                <div className="hrms-form-group">
                  <label>Confirmation Narration</label>
                  <textarea
                    rows="2"
                    className="hrms-input"
                    value={confirmForm.notes}
                    onChange={(e) => setConfirmForm({ ...confirmForm, notes: e.target.value })}
                  />
                </div>
              </div>

              <div className="hrms-modal-footer">
                <button type="button" className="hrms-btn-secondary" onClick={() => setIsConfirmModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="hrms-btn-primary" disabled={submitting}>
                  {submitting ? 'Confirming...' : 'Confirm Disbursement'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
