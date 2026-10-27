import React, { useState, useEffect } from 'react';
import { 
  FileText, Download, Eye, DollarSign, Calendar, CheckCircle2, 
  RefreshCw, X, Lock, Clock, AlertTriangle, Send, ShieldCheck, Building2
} from 'lucide-react';
import payslipService from '../../services/payslipService';

export default function EmployeePayslips() {
  const [payslips, setPayslips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedPayslip, setSelectedPayslip] = useState(null);
  const [requestModalPayslip, setRequestModalPayslip] = useState(null);
  const [requestReason, setRequestReason] = useState('');
  const [requestSubmitting, setRequestSubmitting] = useState(false);
  const [downloadingId, setDownloadingId] = useState(null);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const fetchMyPayslips = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await payslipService.getPayslips();
      setPayslips(data);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch personal payslips.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMyPayslips();
  }, []);

  const handleDownload = async (payslipId, month, year) => {
    setDownloadingId(payslipId);
    setError(null);
    try {
      await payslipService.downloadPayslipPdf(payslipId, `Payslip_${month}_${year}.pdf`);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Could not download payslip. Please verify unlock approval status.';
      setError(msg);
    } finally {
      setDownloadingId(null);
    }
  };

  const handleOpenRequestModal = (payslip) => {
    setRequestModalPayslip(payslip);
    setRequestReason('Official copy requested for personal records / banking verification.');
  };

  const handleSubmitDownloadRequest = async (e) => {
    e.preventDefault();
    if (!requestModalPayslip) return;

    setRequestSubmitting(true);
    setError(null);
    const pId = requestModalPayslip.id || requestModalPayslip._firestore_id || requestModalPayslip.payslip_number;

    try {
      const res = await payslipService.requestDownload(pId, requestReason);
      setSuccessMsg(res.message || 'Request submitted to administrator for download approval.');
      setRequestModalPayslip(null);
      setRequestReason('');
      fetchMyPayslips();
      if (selectedPayslip && (selectedPayslip.id === pId || selectedPayslip.payslip_number === pId)) {
        setSelectedPayslip(res.payslip);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit download unlock request.');
    } finally {
      setRequestSubmitting(false);
    }
  };

  const getStatusBadge = (p) => {
    const status = (p.download_approval_status || 'LOCKED').toUpperCase();
    if (status === 'APPROVED') {
      return (
        <span className="hrms-badge hrms-badge-success" title="Admin authorized PDF download">
          <CheckCircle2 size={12} /> Unlocked
        </span>
      );
    }
    if (status === 'PENDING_APPROVAL') {
      return (
        <span className="hrms-badge" style={{ backgroundColor: '#fef3c7', color: '#92400e', borderColor: '#fde68a' }} title="Awaiting Admin authorization">
          <Clock size={12} /> Request Pending
        </span>
      );
    }
    if (status === 'REJECTED') {
      return (
        <span className="hrms-badge" style={{ backgroundColor: '#fee2e2', color: '#991b1b', borderColor: '#fca5a5' }} title="Admin declined request">
          <AlertTriangle size={12} /> Declined
        </span>
      );
    }
    return (
      <span className="hrms-badge" style={{ backgroundColor: '#f1f5f9', color: '#475569', borderColor: '#cbd5e1' }} title="Download requires Admin authorization">
        <Lock size={12} /> Locked
      </span>
    );
  };

  const latest = payslips.length > 0 ? payslips[0] : null;

  return (
    <div className="hrms-page-container">
      {/* Header */}
      <div className="hrms-page-header">
        <div className="hrms-page-title-group">
          <h1><FileText size={28} className="text-forest" /> My Monthly Payslips</h1>
          <p className="hrms-page-subtitle">
            Official monthly compensation statements from Arshith Fresh India Pvt Ltd. Download requires administrative authorization.
          </p>
        </div>

        <div className="hrms-actions-group">
          <button type="button" className="hrms-btn-secondary" onClick={fetchMyPayslips} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="hrms-card" style={{ borderColor: '#fca5a5', backgroundColor: '#fef2f2', padding: '1rem', marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ color: '#991b1b' }}>{error}</span>
          <button type="button" onClick={() => setError(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#991b1b' }}><X size={16} /></button>
        </div>
      )}

      {successMsg && (
        <div className="hrms-card" style={{ borderColor: '#86efac', backgroundColor: '#f0fdf4', padding: '1rem', marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ color: '#166534', fontWeight: '500' }}>{successMsg}</span>
          <button type="button" onClick={() => setSuccessMsg(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#166534' }}><X size={16} /></button>
        </div>
      )}

      {/* Latest Payslip Highlight Card */}
      {latest && (
        <div className="hrms-card" style={{ background: 'linear-gradient(135deg, #064e3b 0%, #022c22 100%)', color: '#ffffff', border: 'none', marginBottom: '1.5rem', boxShadow: '0 10px 25px -5px rgba(6, 78, 59, 0.4)' }}>
          <div className="hrms-card-body" style={{ padding: '1.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1.25rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.4rem' }}>
                  <span className="hrms-badge" style={{ backgroundColor: 'rgba(255, 255, 255, 0.18)', color: '#ffffff', border: 'none' }}>
                    Latest Statement
                  </span>
                  {getStatusBadge(latest)}
                </div>
                <h2 style={{ fontSize: '1.65rem', fontWeight: '800', margin: '0.25rem 0', letterSpacing: '-0.02em' }}>
                  {latest.month_name || latest.month} {latest.year}
                </h2>
                <div style={{ opacity: 0.85, fontSize: '0.85rem' }}>
                  Arshith Fresh India Pvt Ltd • Code: {latest.employee_code || latest.employeeId || 'AFI-XXXX'} • Ref: {latest.payslip_number}
                </div>
                <div style={{ opacity: 0.75, fontSize: '0.8rem', marginTop: '0.25rem' }}>
                  Paid Days: {latest.payable_days || latest.total_days || 31} / {latest.total_days || 31} • LOP Days: {latest.unpaid_days || 0} • PF (12%): ₹{parseFloat(latest.employee_pf || 4246).toLocaleString('en-IN')}
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <div style={{ opacity: 0.8, fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Net Take-Home Pay</div>
                <div style={{ fontSize: '2.25rem', fontWeight: '900', color: '#6ee7b7' }}>
                  ₹{parseFloat(latest.net_salary || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </div>
                
                <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                  <button
                    type="button"
                    className="hrms-btn-secondary"
                    style={{ backgroundColor: 'rgba(255,255,255,0.15)', color: '#ffffff', border: '1px solid rgba(255,255,255,0.3)' }}
                    onClick={() => setSelectedPayslip(latest)}
                  >
                    <Eye size={15} /> View Statement
                  </button>

                  {latest.download_approval_status === 'APPROVED' ? (
                    <button
                      type="button"
                      className="hrms-btn-primary"
                      style={{ backgroundColor: '#10b981', color: '#ffffff', fontWeight: '700' }}
                      onClick={() => handleDownload(latest.id || latest._firestore_id || latest.payslip_number, latest.month, latest.year)}
                      disabled={downloadingId === (latest.id || latest.payslip_number)}
                    >
                      <Download size={15} /> {downloadingId === (latest.id || latest.payslip_number) ? 'Downloading...' : 'Download PDF'}
                    </button>
                  ) : latest.download_approval_status === 'PENDING_APPROVAL' ? (
                    <button
                      type="button"
                      className="hrms-btn-secondary"
                      style={{ backgroundColor: 'rgba(245, 158, 11, 0.25)', color: '#fef08a', borderColor: '#f59e0b', cursor: 'not-allowed' }}
                      disabled
                    >
                      <Clock size={15} /> Approval Pending
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="hrms-btn-secondary"
                      style={{ backgroundColor: '#ffffff', color: '#064e3b', fontWeight: '700' }}
                      onClick={() => handleOpenRequestModal(latest)}
                    >
                      <Lock size={15} /> Request Unlock
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Payslips Table */}
      <div className="hrms-card">
        <div className="hrms-card-header">
          <h2 className="hrms-card-title"><Calendar size={20} /> Payslip History & Download Authorization</h2>
          <span className="hrms-metric-subtext">{payslips.length} Statements Available</span>
        </div>

        <div className="hrms-table-container">
          <table className="hrms-table">
            <thead>
              <tr>
                <th>Period</th>
                <th>Employee Code</th>
                <th>Paid / Total Days</th>
                <th>Gross Earnings</th>
                <th>Total Deductions</th>
                <th>Net Pay</th>
                <th>Authorization Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {payslips.length === 0 ? (
                <tr>
                  <td colSpan="8">
                    <div className="hrms-empty-state">
                      <FileText className="hrms-empty-icon" />
                      <p>No payslips generated yet for your account.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                payslips.map((p) => {
                  const pId = p.id || p._firestore_id || p.payslip_number;
                  const isApproved = p.download_approval_status === 'APPROVED';
                  const isPending = p.download_approval_status === 'PENDING_APPROVAL';
                  const isRejected = p.download_approval_status === 'REJECTED';

                  return (
                    <tr key={pId}>
                      <td>
                        <strong>{p.month_name || p.month} {p.year}</strong>
                        <div className="hrms-metric-subtext" style={{ fontSize: '0.72rem' }}>
                          Ref: {p.payslip_number || pId}
                        </div>
                      </td>
                      <td>
                        <span style={{ fontWeight: '600', color: '#334155' }}>
                          {p.employee_code || p.employeeId || p.employee_id || 'AFI-XXXX'}
                        </span>
                      </td>
                      <td>
                        <span style={{ color: '#16a34a', fontWeight: '600' }}>
                          {p.payable_days || p.paid_days || p.total_days || 31} Days
                        </span>
                        <div className="hrms-metric-subtext" style={{ fontSize: '0.7rem' }}>
                          LOP: {p.unpaid_days || p.lop_days || 0} Days
                        </div>
                      </td>
                      <td>₹{parseFloat(p.gross_salary || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                      <td style={{ color: '#dc2626' }}>- ₹{parseFloat(p.total_deductions || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                      <td>
                        <strong style={{ color: '#134e4a', fontSize: '0.98rem' }}>
                          ₹{parseFloat(p.net_salary || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </strong>
                      </td>
                      <td>
                        {getStatusBadge(p)}
                        {p.download_approved_at && (
                          <div className="hrms-metric-subtext" style={{ fontSize: '0.68rem', marginTop: '0.2rem' }}>
                            Unlocked on {new Date(p.download_approved_at).toLocaleDateString()}
                          </div>
                        )}
                        {p.download_rejection_reason && isRejected && (
                          <div className="hrms-metric-subtext" style={{ fontSize: '0.68rem', color: '#b91c1c', marginTop: '0.2rem' }}>
                            Note: {p.download_rejection_reason}
                          </div>
                        )}
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                          <button
                            type="button"
                            className="hrms-btn-secondary"
                            style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
                            title="View statement preview"
                            onClick={() => setSelectedPayslip(p)}
                          >
                            <Eye size={13} /> View
                          </button>

                          {isApproved ? (
                            <button
                              type="button"
                              className="hrms-btn-primary"
                              style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem', backgroundColor: '#059669' }}
                              onClick={() => handleDownload(pId, p.month, p.year)}
                              disabled={downloadingId === pId}
                              title="Download official PDF payslip"
                            >
                              <Download size={13} /> {downloadingId === pId ? 'Downloading...' : 'PDF'}
                            </button>
                          ) : isPending ? (
                            <button
                              type="button"
                              className="hrms-btn-secondary"
                              style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem', opacity: 0.75, cursor: 'not-allowed', color: '#92400e', backgroundColor: '#fef3c7' }}
                              disabled
                              title="Request pending Admin approval"
                            >
                              <Clock size={13} /> Pending
                            </button>
                          ) : (
                            <button
                              type="button"
                              className="hrms-btn-secondary"
                              style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem', borderColor: '#0f766e', color: '#0f766e' }}
                              onClick={() => handleOpenRequestModal(p)}
                              title="Request Admin to unlock PDF download"
                            >
                              <Lock size={13} /> {isRejected ? 'Re-request' : 'Unlock'}
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

      {/* Request Unlock Modal */}
      {requestModalPayslip && (
        <div className="hrms-modal-overlay" onClick={() => setRequestModalPayslip(null)}>
          <div className="hrms-modal-content" style={{ maxWidth: '480px' }} onClick={(e) => e.stopPropagation()}>
            <div className="hrms-modal-header">
              <h3 className="hrms-modal-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Lock size={20} className="text-forest" /> Request Payslip Download Authorization
              </h3>
              <button type="button" className="hrms-modal-close" onClick={() => setRequestModalPayslip(null)}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSubmitDownloadRequest}>
              <div className="hrms-modal-body">
                <div style={{ backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '6px', padding: '0.85rem', marginBottom: '1rem', fontSize: '0.85rem' }}>
                  <div style={{ fontWeight: '700', color: '#166534', marginBottom: '0.25rem' }}>
                    Statement: {requestModalPayslip.month_name || requestModalPayslip.month} {requestModalPayslip.year}
                  </div>
                  <div style={{ color: '#15803d' }}>
                    Net Pay: <strong>₹{parseFloat(requestModalPayslip.net_salary || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</strong> • Ref: {requestModalPayslip.payslip_number}
                  </div>
                </div>

                <div style={{ fontSize: '0.82rem', color: '#64748b', marginBottom: '1rem', lineHeight: '1.4' }}>
                  <ShieldCheck size={16} style={{ display: 'inline', verticalAlign: '-3px', marginRight: '4px', color: '#0f766e' }} />
                  Corporate Policy: Official payslip downloads are locked by default. Once you submit this request, an administrator will review and unlock the high-resolution PDF download for you.
                </div>

                <div className="hrms-form-group">
                  <label className="hrms-label" htmlFor="requestReason">
                    Purpose / Reason for Download Request:
                  </label>
                  <textarea
                    id="requestReason"
                    className="hrms-input"
                    rows="3"
                    required
                    placeholder="e.g., Applying for bank loan / visa verification / personal tax filing"
                    value={requestReason}
                    onChange={(e) => setRequestReason(e.target.value)}
                  />
                </div>
              </div>

              <div className="hrms-modal-footer">
                <button type="button" className="hrms-btn-secondary" onClick={() => setRequestModalPayslip(null)} disabled={requestSubmitting}>
                  Cancel
                </button>
                <button type="submit" className="hrms-btn-primary" disabled={requestSubmitting}>
                  <Send size={15} /> {requestSubmitting ? 'Submitting...' : 'Submit Request to Admin'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Official Company Template Preview Modal */}
      {selectedPayslip && (
        <div className="hrms-modal-overlay" onClick={() => setSelectedPayslip(null)}>
          <div className="hrms-modal-content" style={{ maxWidth: '860px', width: '95%' }} onClick={(e) => e.stopPropagation()}>
            <div className="hrms-modal-header">
              <h3 className="hrms-modal-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Building2 size={20} className="text-forest" />
                Arshith Fresh India Pvt Ltd • Official Payslip Preview
              </h3>
              <button type="button" className="hrms-modal-close" onClick={() => setSelectedPayslip(null)}>
                <X size={20} />
              </button>
            </div>

            <div className="hrms-modal-body" style={{ maxHeight: '78vh', overflowY: 'auto' }}>
              {/* Outer Border Box matching Reference Image */}
              <div style={{ border: '2px solid #000000', padding: '1.25rem', backgroundColor: '#ffffff', color: '#000000', fontFamily: 'Inter, system-ui, sans-serif' }}>
                
                {/* Header: Company Name & Address */}
                <div style={{ textAlign: 'center', marginBottom: '0.75rem', position: 'relative' }}>
                  <div style={{ fontSize: '1.35rem', fontWeight: '800', letterSpacing: '0.02em', textTransform: 'uppercase' }}>
                    ARSHITH FRESH INDIA PVT LTD
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#222222', marginTop: '0.2rem' }}>
                    Bangalore, Karnataka, Pincode: 560102
                  </div>
                </div>

                {/* Shaded Month Banner */}
                <div style={{ backgroundColor: '#d1d5db', border: '1px solid #000000', textAlign: 'center', padding: '0.35rem 0', fontWeight: '700', fontSize: '0.9rem', marginBottom: '0.75rem' }}>
                  Payslip for the Month of : {selectedPayslip.month_name || selectedPayslip.month} {selectedPayslip.year}
                </div>

                {/* 3-Column Metadata Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.2fr 0.9fr', gap: '0.5rem 1.5rem', fontSize: '0.8rem', marginBottom: '0.85rem', lineHeight: '1.45' }}>
                  <div>
                    <div><strong>Employee Code:</strong> {selectedPayslip.employee_code || selectedPayslip.employeeId || selectedPayslip.employee_id || 'AFI-XXXX'}</div>
                    <div><strong>Name:</strong> {selectedPayslip.employee_name || 'Employee name'}</div>
                    <div><strong>Date of Joining:</strong> {selectedPayslip.date_of_joining || '16-Jan-2025'}</div>
                    <div><strong>Location:</strong> {selectedPayslip.location || 'Bangalore'}</div>
                    <div><strong>Department:</strong> {selectedPayslip.department || 'IT'}</div>
                    <div><strong>Designation:</strong> {selectedPayslip.designation || 'Python Developer'}</div>
                    <div><strong>Gender:</strong> {selectedPayslip.gender || 'Male'}</div>
                  </div>

                  <div>
                    <div><strong>Bank Name.:</strong> {selectedPayslip.bank_name || 'IDFC FIRST BANK'}</div>
                    <div><strong>Bank Account No.:</strong> {selectedPayslip.account_number || '87387687323'}</div>
                    <div><strong>PAN.:</strong> {selectedPayslip.pan_number || 'GF837FEYB73'}</div>
                    <div><strong>UAN.:</strong> {selectedPayslip.uan_number || '27368873212'}</div>
                  </div>

                  <div>
                    <div><strong>Paid Days:</strong> {parseFloat(selectedPayslip.payable_days || selectedPayslip.total_days || 31).toFixed(1)}</div>
                    <div><strong>LOP Days:</strong> {selectedPayslip.unpaid_days || selectedPayslip.lop_days || 0}</div>
                    <div><strong>Arrear Days:</strong> 0.0</div>
                    <div><strong>Days in Month:</strong> {parseFloat(selectedPayslip.total_days || 31).toFixed(1)}</div>
                  </div>
                </div>

                {/* Horizontal Divider */}
                <div style={{ borderTop: '1.5px solid #000000', margin: '0.65rem 0' }} />

                {/* Dual Financial Table: Earnings vs Deductions */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0', fontSize: '0.8rem', border: '1px solid #000000' }}>
                  {/* Left Column: Earnings */}
                  <div style={{ borderRight: '1.5px solid #000000', padding: '0.5rem' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1.2fr 0.8fr', fontWeight: '700', borderBottom: '1px solid #000000', paddingBottom: '0.35rem', marginBottom: '0.4rem', textDecoration: 'underline' }}>
                      <span>Earning</span>
                      <span style={{ textAlign: 'right' }}>Master</span>
                      <span style={{ textAlign: 'right' }}>Paid (Excl. Arrear)</span>
                      <span style={{ textAlign: 'right' }}>Arrear</span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1.2fr 0.8fr', padding: '0.2rem 0' }}>
                      <span>Basic</span>
                      <span style={{ textAlign: 'right' }}>{parseFloat(selectedPayslip.basic_salary || 17689).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                      <span style={{ textAlign: 'right' }}>{parseFloat(selectedPayslip.paid_basic || selectedPayslip.basic_salary || 17689).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                      <span style={{ textAlign: 'right' }}>0.00</span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1.2fr 0.8fr', padding: '0.2rem 0' }}>
                      <span>HRA</span>
                      <span style={{ textAlign: 'right' }}>{parseFloat(selectedPayslip.hra || 7076).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                      <span style={{ textAlign: 'right' }}>{parseFloat(selectedPayslip.paid_hra || selectedPayslip.hra || 7076).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                      <span style={{ textAlign: 'right' }}>0.00</span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1.2fr 0.8fr', padding: '0.2rem 0' }}>
                      <span>OTHER ALLOWANCES</span>
                      <span style={{ textAlign: 'right' }}>{parseFloat(selectedPayslip.other_allowances || 10612).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                      <span style={{ textAlign: 'right' }}>{parseFloat(selectedPayslip.paid_other || selectedPayslip.other_allowances || 10612).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                      <span style={{ textAlign: 'right' }}>0.00</span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1.2fr 0.8fr', fontWeight: '700', borderTop: '1px solid #000000', borderBottom: '1px solid #000000', padding: '0.35rem 0', marginTop: '0.5rem' }}>
                      <span>Total Earnings</span>
                      <span style={{ textAlign: 'right' }}>{parseFloat(selectedPayslip.gross_salary || 35377).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                      <span style={{ textAlign: 'right' }}>{parseFloat(selectedPayslip.adjusted_gross || selectedPayslip.gross_salary || 35377).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                      <span style={{ textAlign: 'right' }}>0.00</span>
                    </div>
                  </div>

                  {/* Right Column: Deductions */}
                  <div style={{ padding: '0.5rem' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.2fr 0.8fr', fontWeight: '700', borderBottom: '1px solid #000000', paddingBottom: '0.35rem', marginBottom: '0.4rem', textDecoration: 'underline' }}>
                      <span>Deduction</span>
                      <span style={{ textAlign: 'right' }}>Deduction</span>
                      <span style={{ textAlign: 'right' }}>Arrear</span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.2fr 0.8fr', padding: '0.2rem 0' }}>
                      <span>Income Tax</span>
                      <span style={{ textAlign: 'right' }}>{parseFloat(selectedPayslip.income_tax_tds || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                      <span style={{ textAlign: 'right' }}>0.00</span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.2fr 0.8fr', padding: '0.2rem 0' }}>
                      <span>PF</span>
                      <span style={{ textAlign: 'right' }}>{parseFloat(selectedPayslip.employee_pf || 4246).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                      <span style={{ textAlign: 'right' }}>{parseFloat(selectedPayslip.employee_pf || 4246).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.2fr 0.8fr', padding: '0.2rem 0' }}>
                      <span>PT</span>
                      <span style={{ textAlign: 'right' }}>{parseFloat(selectedPayslip.professional_tax || 200).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                      <span style={{ textAlign: 'right' }}>{parseFloat(selectedPayslip.professional_tax || 200).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.2fr 0.8fr', fontWeight: '700', borderTop: '1px solid #000000', borderBottom: '1px solid #000000', padding: '0.35rem 0', marginTop: '0.5rem' }}>
                      <span>Total Deductions</span>
                      <span style={{ textAlign: 'right' }}>{parseFloat(selectedPayslip.total_deductions || 4446).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                      <span style={{ textAlign: 'right' }}>{parseFloat(selectedPayslip.total_deductions || 4446).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                    </div>
                  </div>
                </div>

                {/* Net Pay & Words */}
                <div style={{ marginTop: '0.85rem', paddingTop: '0.5rem', borderTop: '1.5px solid #000000' }}>
                  <div style={{ fontSize: '1.05rem', fontWeight: '800' }}>
                    Net Pay: {parseFloat(selectedPayslip.net_salary || 30931).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </div>
                  <div style={{ fontStyle: 'italic', fontSize: '0.85rem', marginTop: '0.25rem', color: '#111827' }}>
                    {selectedPayslip.net_salary_words || 'Indianrupees Thirty Thousand Nine Hundred and Thirty One Only'}
                  </div>
                </div>
              </div>
            </div>

            <div className="hrms-modal-footer" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {getStatusBadge(selectedPayslip)}
                {selectedPayslip.download_approval_status !== 'APPROVED' && (
                  <span style={{ fontSize: '0.78rem', color: '#64748b' }}>
                    🔒 Official PDF download is locked.
                  </span>
                )}
              </div>

              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button type="button" className="hrms-btn-secondary" onClick={() => setSelectedPayslip(null)}>
                  Close
                </button>

                {selectedPayslip.download_approval_status === 'APPROVED' ? (
                  <button
                    type="button"
                    className="hrms-btn-primary"
                    style={{ backgroundColor: '#059669' }}
                    onClick={() => handleDownload(selectedPayslip.id || selectedPayslip.payslip_number, selectedPayslip.month, selectedPayslip.year)}
                    disabled={downloadingId === (selectedPayslip.id || selectedPayslip.payslip_number)}
                  >
                    <Download size={14} /> Download PDF (Unlocked)
                  </button>
                ) : selectedPayslip.download_approval_status === 'PENDING_APPROVAL' ? (
                  <button type="button" className="hrms-btn-secondary" disabled style={{ opacity: 0.75, cursor: 'not-allowed', color: '#92400e', backgroundColor: '#fef3c7' }}>
                    <Clock size={14} /> Approval Pending
                  </button>
                ) : (
                  <button
                    type="button"
                    className="hrms-btn-primary"
                    onClick={() => {
                      setSelectedPayslip(null);
                      handleOpenRequestModal(selectedPayslip);
                    }}
                  >
                    <Lock size={14} /> Request Download Approval
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
