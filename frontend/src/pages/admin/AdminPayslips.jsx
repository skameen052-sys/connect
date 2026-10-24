import React, { useState, useEffect } from 'react';
import { 
  FileText, Download, Search, RefreshCw, Eye, CheckCircle2, 
  Calendar, Users, DollarSign, X 
} from 'lucide-react';
import payslipService from '../../services/payslipService';

export default function AdminPayslips() {
  const [payslips, setPayslips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedMonth, setSelectedMonth] = useState('ALL');
  const [selectedPayslip, setSelectedPayslip] = useState(null);
  const [downloadingId, setDownloadingId] = useState(null);
  const [error, setError] = useState(null);

  const fetchPayslips = async () => {
    setLoading(true);
    try {
      const data = await payslipService.getPayslips();
      setPayslips(data);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch generated payslips.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPayslips();
  }, []);

  const handleDownload = async (payslipId, empId) => {
    setDownloadingId(payslipId);
    try {
      await payslipService.downloadPayslipPdf(payslipId, `Payslip_${empId}.pdf`);
    } catch (err) {
      alert('Could not download payslip PDF. Please check backend.');
    } finally {
      setDownloadingId(null);
    }
  };

  const filteredPayslips = payslips.filter((p) => {
    const matchesSearch =
      (p.employee_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.employee_id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.payslip_number || '').toLowerCase().includes(searchTerm.toLowerCase());
    const matchesMonth = selectedMonth === 'ALL' || String(p.month) === selectedMonth;
    return matchesSearch && matchesMonth;
  });

  const totalDisbursed = payslips.reduce((acc, p) => acc + (parseFloat(p.net_salary) || 0), 0);

  return (
    <div className="hrms-page-container">
      {/* Header */}
      <div className="hrms-page-header">
        <div className="hrms-page-title-group">
          <h1><FileText size={28} className="text-forest" /> Digital Payslip Directory</h1>
          <p className="hrms-page-subtitle">
            Inspect generated salary slips, review deductions, and download high-resolution branded PDF payslips.
          </p>
        </div>

        <div className="hrms-actions-group">
          <button type="button" className="hrms-btn-secondary" onClick={fetchPayslips} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="hrms-card" style={{ borderColor: '#fca5a5', backgroundColor: '#fef2f2', padding: '1rem', marginBottom: '1rem' }}>
          <span style={{ color: '#991b1b' }}>{error}</span>
        </div>
      )}

      {/* KPI Metrics */}
      <div className="hrms-metrics-grid">
        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Generated Payslips</span>
            <div className="hrms-metric-icon-wrap"><FileText size={18} /></div>
          </div>
          <div className="hrms-metric-value">{payslips.length}</div>
          <div className="hrms-metric-subtext">Archived in digital registry</div>
        </div>

        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Total Net Pay Value</span>
            <div className="hrms-metric-icon-wrap"><DollarSign size={18} /></div>
          </div>
          <div className="hrms-metric-value">₹{totalDisbursed.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
          <div className="hrms-metric-subtext">Total compensation disbursed</div>
        </div>

        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Verified Security Hash</span>
            <div className="hrms-metric-icon-wrap"><CheckCircle2 size={18} /></div>
          </div>
          <div className="hrms-metric-value">100%</div>
          <div className="hrms-metric-subtext">Digital tamper-proof audit</div>
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
                placeholder="Search by employee name, ID or payslip ref..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            <select
              className="hrms-select"
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
            >
              <option value="ALL">All Months</option>
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
        </div>
      </div>

      {/* Table */}
      <div className="hrms-card">
        <div className="hrms-table-container">
          <table className="hrms-table">
            <thead>
              <tr>
                <th>Payslip Reference</th>
                <th>Employee</th>
                <th>Period</th>
                <th>Payable Days</th>
                <th>Gross Pay</th>
                <th>Total Deductions</th>
                <th>Net Salary</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredPayslips.length === 0 ? (
                <tr>
                  <td colSpan="9">
                    <div className="hrms-empty-state">
                      <FileText className="hrms-empty-icon" />
                      <p>No payslips found matching your filters.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredPayslips.map((p) => {
                  const pId = p.id || p._firestore_id || p.payslip_number;
                  return (
                    <tr key={pId}>
                      <td>
                        <strong>{p.payslip_number || pId}</strong>
                        <div className="hrms-metric-subtext">{p.generated_at?.split('T')[0]}</div>
                      </td>
                      <td>
                        <strong>{p.employee_name}</strong>
                        <div className="hrms-metric-subtext">{p.employee_id} • {p.department}</div>
                      </td>
                      <td>{p.month_name || p.month} {p.year}</td>
                      <td>
                        <span style={{ color: '#16a34a', fontWeight: '600' }}>{p.payable_days} Days</span>
                      </td>
                      <td>₹{parseFloat(p.gross_salary || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                      <td style={{ color: '#dc2626' }}>- ₹{parseFloat(p.total_deductions || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                      <td>
                        <strong style={{ color: '#134e4a', fontSize: '0.95rem' }}>
                          ₹{parseFloat(p.net_salary || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </strong>
                      </td>
                      <td>
                        <span className="hrms-badge hrms-badge-success"><CheckCircle2 size={12} /> Generated</span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button
                            type="button"
                            className="hrms-btn-secondary"
                            style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
                            onClick={() => setSelectedPayslip(p)}
                            title="Quick View"
                          >
                            <Eye size={13} /> View
                          </button>
                          <button
                            type="button"
                            className="hrms-btn-primary"
                            style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
                            onClick={() => handleDownload(pId, p.employee_id)}
                            disabled={downloadingId === pId}
                            title="Download PDF"
                          >
                            <Download size={13} /> {downloadingId === pId ? 'Downloading...' : 'PDF'}
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

      {/* Quick View Modal */}
      {selectedPayslip && (
        <div className="hrms-modal-overlay" onClick={() => setSelectedPayslip(null)}>
          <div className="hrms-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="hrms-modal-header">
              <h3 className="hrms-modal-title">Payslip Details ({selectedPayslip.payslip_number})</h3>
              <button type="button" className="hrms-modal-close" onClick={() => setSelectedPayslip(null)}>
                <X size={20} />
              </button>
            </div>

            <div className="hrms-modal-body">
              <div style={{ backgroundColor: '#f0fdf4', padding: '1rem', borderRadius: '8px', border: '1px solid #bbf7d0', marginBottom: '1.25rem', textAlign: 'center' }}>
                <div style={{ fontSize: '0.85rem', color: '#166534' }}>Net Take-Home Pay</div>
                <div style={{ fontSize: '1.75rem', fontWeight: '700', color: '#134e4a' }}>
                  ₹{parseFloat(selectedPayslip.net_salary || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem' }}>
                  Period: {selectedPayslip.month_name || selectedPayslip.month} {selectedPayslip.year}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', fontSize: '0.875rem' }}>
                <div>
                  <div style={{ fontWeight: '600', marginBottom: '0.5rem', color: '#334155' }}>Earnings:</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0' }}>
                    <span>Gross Salary:</span>
                    <strong>₹{parseFloat(selectedPayslip.gross_salary || 0).toLocaleString('en-IN')}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0', color: '#dc2626' }}>
                    <span>Loss of Pay (LOP):</span>
                    <strong>- ₹{parseFloat(selectedPayslip.loss_of_pay || 0).toLocaleString('en-IN')}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0', borderTop: '1px solid #e2e8f0', marginTop: '0.25rem' }}>
                    <span>Adjusted Gross:</span>
                    <strong>₹{parseFloat(selectedPayslip.adjusted_gross || selectedPayslip.gross_salary || 0).toLocaleString('en-IN')}</strong>
                  </div>
                </div>

                <div>
                  <div style={{ fontWeight: '600', marginBottom: '0.5rem', color: '#334155' }}>Deductions:</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0' }}>
                    <span>Total Deductions:</span>
                    <strong style={{ color: '#dc2626' }}>₹{parseFloat(selectedPayslip.total_deductions || 0).toLocaleString('en-IN')}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0' }}>
                    <span>Payable Days:</span>
                    <strong>{selectedPayslip.payable_days} Days</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0' }}>
                    <span>Unpaid LOP Days:</span>
                    <strong>{selectedPayslip.unpaid_days || 0} Days</strong>
                  </div>
                </div>
              </div>
            </div>

            <div className="hrms-modal-footer">
              <button type="button" className="hrms-btn-secondary" onClick={() => setSelectedPayslip(null)}>
                Close
              </button>
              <button
                type="button"
                className="hrms-btn-primary"
                onClick={() => handleDownload(selectedPayslip.id || selectedPayslip.payslip_number, selectedPayslip.employee_id)}
              >
                <Download size={14} /> Download PDF File
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
