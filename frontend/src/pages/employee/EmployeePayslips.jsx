import React, { useState, useEffect } from 'react';
import { 
  FileText, Download, Eye, DollarSign, Calendar, CheckCircle2, 
  RefreshCw, X 
} from 'lucide-react';
import payslipService from '../../services/payslipService';

export default function EmployeePayslips() {
  const [payslips, setPayslips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedPayslip, setSelectedPayslip] = useState(null);
  const [downloadingId, setDownloadingId] = useState(null);
  const [error, setError] = useState(null);

  const fetchMyPayslips = async () => {
    setLoading(true);
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
    try {
      await payslipService.downloadPayslipPdf(payslipId, `My_Payslip_${month}_${year}.pdf`);
    } catch (err) {
      alert('Could not download payslip.');
    } finally {
      setDownloadingId(null);
    }
  };

  const latest = payslips.length > 0 ? payslips[0] : null;

  return (
    <div className="hrms-page-container">
      {/* Header */}
      <div className="hrms-page-header">
        <div className="hrms-page-title-group">
          <h1><FileText size={28} className="text-forest" /> My Monthly Payslips</h1>
          <p className="hrms-page-subtitle">
            View detailed compensation records, itemized statutory deductions, and download official PDF payslips.
          </p>
        </div>

        <div className="hrms-actions-group">
          <button type="button" className="hrms-btn-secondary" onClick={fetchMyPayslips} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="hrms-card" style={{ borderColor: '#fca5a5', backgroundColor: '#fef2f2', padding: '1rem', marginBottom: '1rem' }}>
          <span style={{ color: '#991b1b' }}>{error}</span>
        </div>
      )}

      {/* Latest Payslip Highlight Card */}
      {latest && (
        <div className="hrms-card" style={{ background: 'linear-gradient(135deg, #134e4a 0%, #064e3b 100%)', color: '#ffffff', border: 'none', marginBottom: '1.5rem' }}>
          <div className="hrms-card-body" style={{ padding: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
              <div>
                <span className="hrms-badge" style={{ backgroundColor: 'rgba(255, 255, 255, 0.2)', color: '#ffffff', border: 'none', marginBottom: '0.5rem' }}>
                  Latest Disbursed Payslip
                </span>
                <h2 style={{ fontSize: '1.5rem', fontWeight: '700', margin: '0.25rem 0' }}>
                  {latest.month_name || latest.month} {latest.year}
                </h2>
                <div style={{ opacity: 0.85, fontSize: '0.85rem' }}>
                  Payable Days: {latest.payable_days} Days • Ref: {latest.payslip_number}
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <div style={{ opacity: 0.8, fontSize: '0.8rem', textTransform: 'uppercase' }}>Net Take-Home Pay</div>
                <div style={{ fontSize: '2rem', fontWeight: '800' }}>
                  ₹{parseFloat(latest.net_salary || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </div>
                <button
                  type="button"
                  className="hrms-btn-secondary"
                  style={{ marginTop: '0.5rem', backgroundColor: '#ffffff', color: '#134e4a', fontWeight: '700' }}
                  onClick={() => handleDownload(latest.id || latest._firestore_id || latest.payslip_number, latest.month, latest.year)}
                  disabled={downloadingId === (latest.id || latest.payslip_number)}
                >
                  <Download size={15} /> Download PDF Payslip
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Payslips Table */}
      <div className="hrms-card">
        <div className="hrms-card-header">
          <h2 className="hrms-card-title"><Calendar size={20} /> Payslip History</h2>
          <span className="hrms-metric-subtext">{payslips.length} Statements Available</span>
        </div>

        <div className="hrms-table-container">
          <table className="hrms-table">
            <thead>
              <tr>
                <th>Period</th>
                <th>Reference #</th>
                <th>Payable Days</th>
                <th>Gross Salary</th>
                <th>Total Deductions</th>
                <th>Net Salary</th>
                <th>Status</th>
                <th>Download</th>
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
                  return (
                    <tr key={pId}>
                      <td>
                        <strong>{p.month_name || p.month} {p.year}</strong>
                      </td>
                      <td>{p.payslip_number || pId}</td>
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
                        <span className="hrms-badge hrms-badge-success"><CheckCircle2 size={12} /> Disbursed</span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button
                            type="button"
                            className="hrms-btn-secondary"
                            style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
                            onClick={() => setSelectedPayslip(p)}
                          >
                            <Eye size={13} /> View
                          </button>
                          <button
                            type="button"
                            className="hrms-btn-primary"
                            style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
                            onClick={() => handleDownload(pId, p.month, p.year)}
                            disabled={downloadingId === pId}
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
              <h3 className="hrms-modal-title">Payslip Breakdown ({selectedPayslip.month_name || selectedPayslip.month} {selectedPayslip.year})</h3>
              <button type="button" className="hrms-modal-close" onClick={() => setSelectedPayslip(null)}>
                <X size={20} />
              </button>
            </div>

            <div className="hrms-modal-body">
              <div style={{ backgroundColor: '#f0fdf4', padding: '1rem', borderRadius: '8px', border: '1px solid #bbf7d0', marginBottom: '1.25rem', textAlign: 'center' }}>
                <div style={{ fontSize: '0.85rem', color: '#166534' }}>Net Take-Home Salary</div>
                <div style={{ fontSize: '1.75rem', fontWeight: '700', color: '#134e4a' }}>
                  ₹{parseFloat(selectedPayslip.net_salary || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
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
                onClick={() => handleDownload(selectedPayslip.id || selectedPayslip.payslip_number, selectedPayslip.month, selectedPayslip.year)}
              >
                <Download size={14} /> Download PDF
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
