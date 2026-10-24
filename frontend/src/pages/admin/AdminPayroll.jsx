import React, { useState, useEffect } from 'react';
import { 
  DollarSign, Calculator, FileText, CheckCircle2, AlertTriangle, 
  Download, Lock, Eye, Trash2, RefreshCw, Calendar, Users, 
  ArrowRight, ShieldCheck, ChevronRight, X
} from 'lucide-react';
import payrollService from '../../services/payrollService';
import paymentService from '../../services/paymentService';
import payslipService from '../../services/payslipService';

export default function AdminPayroll() {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Modals & Drawers state
  const [isCalcModalOpen, setIsCalcModalOpen] = useState(false);
  const [selectedRun, setSelectedRun] = useState(null);
  const [exceptionsData, setExceptionsData] = useState(null);
  const [isExceptionsModalOpen, setIsExceptionsModalOpen] = useState(false);
  const [calculating, setCalculating] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // New calculation form state
  const currentDate = new Date();
  const [calcForm, setCalcForm] = useState({
    month: currentDate.getMonth() + 1,
    year: currentDate.getFullYear(),
    custom_payroll_days: 30,
    notes: 'Monthly attendance-driven payroll run',
  });

  const fetchRuns = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await payrollService.getRuns();
      setRuns(data);
    } catch (err) {
      console.error('Error fetching payroll runs:', err);
      setError('Failed to load payroll batches. Please ensure backend is reachable.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
  }, []);

  const handleCalculateSubmit = async (e) => {
    e.preventDefault();
    setCalculating(true);
    setError(null);
    try {
      const res = await payrollService.calculate({
        month: parseInt(calcForm.month, 10),
        year: parseInt(calcForm.year, 10),
        custom_payroll_days: parseInt(calcForm.custom_payroll_days, 10),
        notes: calcForm.notes,
      });
      setSuccessMsg(res.message || 'Payroll calculated successfully!');
      setIsCalcModalOpen(false);
      fetchRuns();
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Calculation failed.';
      setError(msg);
    } finally {
      setCalculating(false);
    }
  };

  const handleReviewRun = async (runId) => {
    setActionLoading(true);
    try {
      await payrollService.reviewRun(runId, 'Reviewed exceptions and verified hours.');
      setSuccessMsg('Payroll moved to UNDER REVIEW.');
      fetchRuns();
      if (selectedRun) {
        const updated = await payrollService.getRunDetails(runId);
        setSelectedRun(updated);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Review failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleApproveRun = async (runId) => {
    setActionLoading(true);
    try {
      await payrollService.approveRun(runId, 'Authorized HR approval granted.');
      setSuccessMsg('Payroll run APPROVED.');
      fetchRuns();
      if (selectedRun) {
        const updated = await payrollService.getRunDetails(runId);
        setSelectedRun(updated);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Approval failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleFinalizeRun = async (runId) => {
    if (!window.confirm('Finalizing will lock this payroll batch and generate payslips. This action is immutable. Proceed?')) {
      return;
    }
    setActionLoading(true);
    try {
      const res = await payrollService.finalizeRun(runId, 'Finalized and locked batch.');
      setSuccessMsg(res.message || 'Payroll FINALIZED. Digital payslips generated.');
      fetchRuns();
      if (selectedRun) {
        const updated = await payrollService.getRunDetails(runId);
        setSelectedRun(updated);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Finalization failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleInspectExceptions = async (runId) => {
    try {
      const exc = await payrollService.getExceptions(runId);
      setExceptionsData(exc);
      setIsExceptionsModalOpen(true);
    } catch (err) {
      setError('Could not inspect exceptions.');
    }
  };

  const handleExportBankFile = async (runId) => {
    try {
      await paymentService.exportBankFile(runId);
      setSuccessMsg('Bank payment batch CSV downloaded successfully.');
    } catch (err) {
      setError('Failed to export bank file.');
    }
  };

  const handleDeleteRun = async (runId) => {
    if (!window.confirm('Are you sure you want to delete this preliminary payroll calculation?')) {
      return;
    }
    try {
      await payrollService.deleteRun(runId);
      setSuccessMsg('Payroll batch deleted.');
      if (selectedRun?.id === runId) setSelectedRun(null);
      fetchRuns();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete payroll run.');
    }
  };

  // Aggregate metrics
  const totalDisbursed = runs.reduce((acc, r) => acc + (parseFloat(r.total_net_disbursed) || 0), 0);
  const totalGross = runs.reduce((acc, r) => acc + (parseFloat(r.total_gross) || 0), 0);
  const totalLop = runs.reduce((acc, r) => acc + (parseFloat(r.total_loss_of_pay) || 0), 0);
  const totalEmployerCost = runs.reduce((acc, r) => acc + (parseFloat(r.total_employer_cost) || 0), 0);

  const getStatusBadge = (status) => {
    const s = (status || '').toUpperCase();
    if (s === 'FINALIZED' || s === 'PAID') {
      return <span className="hrms-badge hrms-badge-success"><CheckCircle2 size={12} /> {s}</span>;
    }
    if (s === 'APPROVED') {
      return <span className="hrms-badge hrms-badge-info"><ShieldCheck size={12} /> {s}</span>;
    }
    if (s === 'UNDER_REVIEW') {
      return <span className="hrms-badge hrms-badge-warning"><AlertTriangle size={12} /> UNDER REVIEW</span>;
    }
    if (s === 'CALCULATED') {
      return <span className="hrms-badge hrms-badge-info"><Calculator size={12} /> CALCULATED</span>;
    }
    return <span className="hrms-badge hrms-badge-neutral">{s || 'DRAFT'}</span>;
  };

  return (
    <div className="hrms-page-container">
      {/* Page Header */}
      <div className="hrms-page-header">
        <div className="hrms-page-title-group">
          <h1><DollarSign size={28} className="text-forest" /> Automated Attendance-Driven Payroll</h1>
          <p className="hrms-page-subtitle">
            Calculate accurate compensation using employee salary structures, punch records, approved leaves, and statutory deductions.
          </p>
        </div>

        <div className="hrms-actions-group">
          <button 
            type="button" 
            className="hrms-btn-secondary" 
            onClick={fetchRuns}
            disabled={loading}
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
          <button 
            type="button" 
            className="hrms-btn-primary" 
            onClick={() => setIsCalcModalOpen(true)}
          >
            <Calculator size={16} /> Run Monthly Payroll
          </button>
        </div>
      </div>

      {/* Notifications / Alerts */}
      {error && (
        <div className="hrms-card" style={{ borderColor: '#fca5a5', backgroundColor: '#fef2f2', padding: '1rem', marginBottom: '1rem' }}>
          <div style={{ color: '#991b1b', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span><strong>Notice:</strong> {error}</span>
            <button onClick={() => setError(null)} style={{ color: '#991b1b' }}><X size={16} /></button>
          </div>
        </div>
      )}

      {successMsg && (
        <div className="hrms-card" style={{ borderColor: '#86efac', backgroundColor: '#f0fdf4', padding: '1rem', marginBottom: '1rem' }}>
          <div style={{ color: '#166534', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span><strong>Success:</strong> {successMsg}</span>
            <button onClick={() => setSuccessMsg(null)} style={{ color: '#166534' }}><X size={16} /></button>
          </div>
        </div>
      )}

      {/* KPI Metrics */}
      <div className="hrms-metrics-grid">
        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Total Net Disbursed</span>
            <div className="hrms-metric-icon-wrap"><DollarSign size={18} /></div>
          </div>
          <div className="hrms-metric-value">₹{totalDisbursed.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
          <div className="hrms-metric-subtext">Across {runs.length} processed batches</div>
        </div>

        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Gross Salary Base</span>
            <div className="hrms-metric-icon-wrap"><Users size={18} /></div>
          </div>
          <div className="hrms-metric-value">₹{totalGross.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
          <div className="hrms-metric-subtext">Total contract commitment</div>
        </div>

        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Loss of Pay (LOP) Total</span>
            <div className="hrms-metric-icon-wrap" style={{ color: '#dc2626', backgroundColor: '#fee2e2' }}><AlertTriangle size={18} /></div>
          </div>
          <div className="hrms-metric-value" style={{ color: '#dc2626' }}>- ₹{totalLop.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
          <div className="hrms-metric-subtext">Attendance absence adjustments</div>
        </div>

        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Total Employer Cost (CTC)</span>
            <div className="hrms-metric-icon-wrap"><ShieldCheck size={18} /></div>
          </div>
          <div className="hrms-metric-value">₹{totalEmployerCost.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
          <div className="hrms-metric-subtext">Includes Employer PF (12%) & ESI (3.25%)</div>
        </div>
      </div>

      {/* Main Payroll Batches Table */}
      <div className="hrms-card">
        <div className="hrms-card-header">
          <h2 className="hrms-card-title"><Calendar size={20} /> Monthly Payroll Runs</h2>
          <span className="hrms-metric-subtext">{runs.length} Records</span>
        </div>

        <div className="hrms-table-container">
          <table className="hrms-table">
            <thead>
              <tr>
                <th>Batch Title & Period</th>
                <th>Employees</th>
                <th>Gross Earnings</th>
                <th>Loss of Pay (LOP)</th>
                <th>Total Deductions</th>
                <th>Net Disbursed</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {runs.length === 0 ? (
                <tr>
                  <td colSpan="8">
                    <div className="hrms-empty-state">
                      <Calculator className="hrms-empty-icon" />
                      <p>No payroll runs calculated yet.</p>
                      <button 
                        type="button" 
                        className="hrms-btn-primary" 
                        style={{ marginTop: '0.75rem' }}
                        onClick={() => setIsCalcModalOpen(true)}
                      >
                        Calculate First Payroll
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                runs.map((r) => {
                  const runId = r.id || r._firestore_id;
                  const isFinalized = ['FINALIZED', 'PAID', 'PAYMENT_PROCESSING'].includes(r.status);
                  return (
                    <tr key={runId}>
                      <td>
                        <strong>{r.title}</strong>
                        <div className="hrms-metric-subtext">{r.month_name || r.month} {r.year} • {r.payroll_days} Days</div>
                      </td>
                      <td>{r.employee_count || (r.details ? r.details.length : 0)} Active</td>
                      <td>₹{parseFloat(r.total_gross || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                      <td style={{ color: '#dc2626' }}>- ₹{parseFloat(r.total_loss_of_pay || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                      <td>₹{parseFloat(r.total_deductions || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                      <td>
                        <strong style={{ color: '#134e4a', fontSize: '0.95rem' }}>
                          ₹{parseFloat(r.total_net_disbursed || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </strong>
                      </td>
                      <td>{getStatusBadge(r.status)}</td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                          <button
                            type="button"
                            className="hrms-btn-secondary"
                            style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
                            title="Inspect Itemized Breakdown"
                            onClick={() => setSelectedRun(r)}
                          >
                            <Eye size={14} /> View
                          </button>

                          <button
                            type="button"
                            className="hrms-btn-outline-green"
                            style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
                            title="Export Bank Batch CSV"
                            onClick={() => handleExportBankFile(runId)}
                          >
                            <Download size={14} /> Bank CSV
                          </button>

                          {!isFinalized && (
                            <button
                              type="button"
                              className="hrms-btn-secondary"
                              style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem', color: '#dc2626' }}
                              title="Delete preliminary draft"
                              onClick={() => handleDeleteRun(runId)}
                            >
                              <Trash2 size={14} />
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

      {/* Selected Run Details Drawer / Modal */}
      {selectedRun && (
        <div className="hrms-modal-overlay" onClick={() => setSelectedRun(null)}>
          <div className="hrms-modal-content lg" onClick={(e) => e.stopPropagation()}>
            <div className="hrms-modal-header">
              <div>
                <h3 className="hrms-modal-title">{selectedRun.title}</h3>
                <span className="hrms-metric-subtext">
                  Status: {selectedRun.status} • Total Employees: {selectedRun.details?.length || 0}
                </span>
              </div>
              <button type="button" className="hrms-modal-close" onClick={() => setSelectedRun(null)}>
                <X size={20} />
              </button>
            </div>

            <div className="hrms-modal-body">
              {/* Lifecycle Stage Actions Bar */}
              <div style={{ backgroundColor: '#f8fafc', padding: '1rem', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem' }}>
                <div>
                  <div style={{ fontSize: '0.85rem', fontWeight: '600', color: '#1e293b' }}>
                    Workflow Stage: {getStatusBadge(selectedRun.status)}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                    Follow governance: Draft → Calculated → Under Review → Approved → Finalized → Paid
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <button 
                    type="button" 
                    className="hrms-btn-secondary"
                    style={{ fontSize: '0.8rem', padding: '0.4rem 0.75rem' }}
                    onClick={() => handleInspectExceptions(selectedRun.id || selectedRun._firestore_id)}
                  >
                    <AlertTriangle size={14} /> Review Exceptions
                  </button>

                  {selectedRun.status === 'CALCULATED' && (
                    <button
                      type="button"
                      className="hrms-btn-secondary"
                      style={{ fontSize: '0.8rem', padding: '0.4rem 0.75rem' }}
                      onClick={() => handleReviewRun(selectedRun.id || selectedRun._firestore_id)}
                      disabled={actionLoading}
                    >
                      <Eye size={14} /> Move to Review
                    </button>
                  )}

                  {['CALCULATED', 'UNDER_REVIEW'].includes(selectedRun.status) && (
                    <button
                      type="button"
                      className="hrms-btn-primary"
                      style={{ fontSize: '0.8rem', padding: '0.4rem 0.75rem' }}
                      onClick={() => handleApproveRun(selectedRun.id || selectedRun._firestore_id)}
                      disabled={actionLoading}
                    >
                      <ShieldCheck size={14} /> Approve Run
                    </button>
                  )}

                  {selectedRun.status === 'APPROVED' && (
                    <button
                      type="button"
                      className="hrms-btn-primary"
                      style={{ fontSize: '0.8rem', padding: '0.4rem 0.75rem', backgroundColor: '#0f766e' }}
                      onClick={() => handleFinalizeRun(selectedRun.id || selectedRun._firestore_id)}
                      disabled={actionLoading}
                    >
                      <Lock size={14} /> Finalize & Lock Batch
                    </button>
                  )}

                  <button
                    type="button"
                    className="hrms-btn-outline-green"
                    style={{ fontSize: '0.8rem', padding: '0.4rem 0.75rem' }}
                    onClick={() => handleExportBankFile(selectedRun.id || selectedRun._firestore_id)}
                  >
                    <Download size={14} /> Bank Transfer CSV
                  </button>
                </div>
              </div>

              {/* Itemized Table */}
              <div className="hrms-table-container">
                <table className="hrms-table">
                  <thead>
                    <tr>
                      <th>Employee</th>
                      <th>Payable / LOP Days</th>
                      <th>Gross Pay</th>
                      <th>LOP Deduct</th>
                      <th>Adj. Gross</th>
                      <th>Emp. PF (12%)</th>
                      <th>PT / Tax</th>
                      <th>Net Pay</th>
                      <th>Payslip</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(selectedRun.details || []).map((d, idx) => (
                      <tr key={idx}>
                        <td>
                          <strong>{d.employee_name}</strong>
                          <div className="hrms-metric-subtext">{d.employee_id} • {d.department}</div>
                        </td>
                        <td>
                          <span style={{ color: '#16a34a', fontWeight: '600' }}>{d.payable_days} Days</span>
                          {d.unpaid_days > 0 && (
                            <span style={{ color: '#dc2626', marginLeft: '0.35rem' }}>({d.unpaid_days} LOP)</span>
                          )}
                        </td>
                        <td>₹{parseFloat(d.gross_salary || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                        <td style={{ color: '#dc2626' }}>- ₹{parseFloat(d.loss_of_pay || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                        <td>₹{parseFloat(d.adjusted_gross || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                        <td>₹{parseFloat(d.employee_pf || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                        <td>₹{(parseFloat(d.professional_tax || 0) + parseFloat(d.income_tax_tds || 0)).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                        <td>
                          <strong style={{ color: '#134e4a', fontSize: '0.95rem' }}>
                            ₹{parseFloat(d.net_salary || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                          </strong>
                        </td>
                        <td>
                          <button
                            type="button"
                            className="hrms-btn-secondary"
                            style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                            title="Download PDF Payslip"
                            onClick={async () => {
                              try {
                                await payslipService.downloadPayslipPdf(d.employee_id);
                              } catch (e) {
                                alert('Payslip available once batch is finalized.');
                              }
                            }}
                          >
                            <Download size={13} /> PDF
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="hrms-modal-footer">
              <button type="button" className="hrms-btn-secondary" onClick={() => setSelectedRun(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Calculate Payroll Wizard Modal */}
      {isCalcModalOpen && (
        <div className="hrms-modal-overlay" onClick={() => setIsCalcModalOpen(false)}>
          <div className="hrms-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="hrms-modal-header">
              <h3 className="hrms-modal-title">Run Monthly Attendance-Driven Payroll</h3>
              <button type="button" className="hrms-modal-close" onClick={() => setIsCalcModalOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleCalculateSubmit}>
              <div className="hrms-modal-body">
                <p style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '1.25rem' }}>
                  The engine scans all employee check-in timestamps, approved leave applications, and active loans to compute prorated salaries, LOP deductions, and statutory PF/ESI liabilities.
                </p>

                <div className="hrms-form-row">
                  <div className="hrms-form-group">
                    <label>Payroll Month</label>
                    <select
                      className="hrms-select"
                      style={{ width: '100%' }}
                      value={calcForm.month}
                      onChange={(e) => setCalcForm({ ...calcForm, month: e.target.value })}
                    >
                      <option value="1">January</option>
                      <option value="2">February</option>
                      <option value="3">March</option>
                      <option value="4">April</option>
                      <option value="5">May</option>
                      <option value="6">June</option>
                      <option value="7">July</option>
                      <option value="8">August</option>
                      <option value="9">September</option>
                      <option value="10">October</option>
                      <option value="11">November</option>
                      <option value="12">December</option>
                    </select>
                  </div>

                  <div className="hrms-form-group">
                    <label>Payroll Year</label>
                    <input
                      type="number"
                      className="hrms-input"
                      value={calcForm.year}
                      onChange={(e) => setCalcForm({ ...calcForm, year: e.target.value })}
                      min="2020"
                      max="2030"
                      required
                    />
                  </div>
                </div>

                <div className="hrms-form-group">
                  <label>Daily Rate Denominator (Configurable Standard)</label>
                  <select
                    className="hrms-select"
                    style={{ width: '100%' }}
                    value={calcForm.custom_payroll_days}
                    onChange={(e) => setCalcForm({ ...calcForm, custom_payroll_days: e.target.value })}
                  >
                    <option value="30">Standard 30 Days (Indian Standard Policy)</option>
                    <option value="31">Actual Calendar Days (e.g. 31/30/28)</option>
                    <option value="26">Working Days Basis (26 Days)</option>
                  </select>
                </div>

                <div className="hrms-form-group">
                  <label>Batch Audit Notes</label>
                  <textarea
                    rows="3"
                    className="hrms-input"
                    value={calcForm.notes}
                    onChange={(e) => setCalcForm({ ...calcForm, notes: e.target.value })}
                    placeholder="e.g. Regular monthly payroll run for HQ workforce"
                  />
                </div>
              </div>

              <div className="hrms-modal-footer">
                <button type="button" className="hrms-btn-secondary" onClick={() => setIsCalcModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="hrms-btn-primary" disabled={calculating}>
                  {calculating ? (
                    <>
                      <RefreshCw size={16} className="animate-spin" /> Processing Engine...
                    </>
                  ) : (
                    <>
                      <Calculator size={16} /> Compute Payroll Batch
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Exceptions Modal */}
      {isExceptionsModalOpen && exceptionsData && (
        <div className="hrms-modal-overlay" onClick={() => setIsExceptionsModalOpen(false)}>
          <div className="hrms-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="hrms-modal-header">
              <h3 className="hrms-modal-title"><AlertTriangle size={18} color="#d97706" /> Payroll Attendance Exceptions</h3>
              <button type="button" className="hrms-modal-close" onClick={() => setIsExceptionsModalOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <div className="hrms-modal-body">
              {exceptionsData.all_clear ? (
                <div style={{ textAlign: 'center', padding: '1.5rem', color: '#16a34a' }}>
                  <CheckCircle2 size={40} style={{ margin: '0 auto 0.75rem' }} />
                  <h4>No Critical Exceptions Found</h4>
                  <p style={{ fontSize: '0.85rem', color: '#64748b' }}>
                    All employee attendance records are reconciled with no zero-pay or abnormal absence anomalies.
                  </p>
                </div>
              ) : (
                <div>
                  <h4 style={{ fontSize: '0.9rem', color: '#b45309', marginBottom: '0.5rem' }}>
                    High Loss of Pay (LOP ≥ 3 Days) Cases:
                  </h4>
                  {exceptionsData.high_lop_cases?.length === 0 ? (
                    <p style={{ fontSize: '0.8rem', color: '#64748b' }}>None</p>
                  ) : (
                    <ul style={{ fontSize: '0.85rem', paddingLeft: '1.25rem', marginBottom: '1rem' }}>
                      {exceptionsData.high_lop_cases?.map((c, i) => (
                        <li key={i}>
                          <strong>{c.employee_name} ({c.employee_id})</strong>: {c.unpaid_days} Unpaid Days (LOP: ₹{c.loss_of_pay})
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>

            <div className="hrms-modal-footer">
              <button type="button" className="hrms-btn-secondary" onClick={() => setIsExceptionsModalOpen(false)}>
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
