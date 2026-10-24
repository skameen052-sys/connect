import React, { useState, useEffect } from 'react';
import { 
  UserMinus, CheckCircle2, Clock, AlertTriangle, Download, 
  Send, RefreshCw, X 
} from 'lucide-react';
import separationService from '../../services/separationService';

export default function EmployeeResignation() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const [formState, setFormState] = useState({
    reason: '',
    intended_last_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    notice_period_days: 30,
  });

  const fetchMyResignation = async () => {
    setLoading(true);
    try {
      const data = await separationService.getRequests();
      setRequests(data);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch separation records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMyResignation();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!window.confirm('Are you sure you want to submit your resignation? This begins the official exit process.')) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await separationService.submitResignation({
        reason: formState.reason,
        intended_last_date: formState.intended_last_date,
        notice_period_days: parseInt(formState.notice_period_days, 10),
      });
      setSuccessMsg('Resignation submitted successfully to HR Administration.');
      fetchMyResignation();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit resignation.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDownloadStatement = async (separationId) => {
    try {
      await separationService.downloadStatementPdf(separationId, 'My_FnF_Statement.pdf');
    } catch (err) {
      alert('Could not download FnF Statement PDF.');
    }
  };

  const activeReq = requests.length > 0 ? requests[0] : null;

  const getStatusBadge = (status) => {
    const s = (status || 'SUBMITTED').toUpperCase();
    if (s === 'SETTLED') return <span className="hrms-badge hrms-badge-success"><CheckCircle2 size={12} /> FULL & FINAL SETTLED</span>;
    if (s === 'APPROVED') return <span className="hrms-badge hrms-badge-info"><CheckCircle2 size={12} /> APPROVED BY HR</span>;
    return <span className="hrms-badge hrms-badge-warning"><Clock size={12} /> AWAITING HR REVIEW</span>;
  };

  return (
    <div className="hrms-page-container">
      {/* Header */}
      <div className="hrms-page-header">
        <div className="hrms-page-title-group">
          <h1><UserMinus size={28} className="text-forest" /> Resignation & Full-and-Final (FnF)</h1>
          <p className="hrms-page-subtitle">
            Submit formal resignation, track handover notice period, and download official Full & Final settlement statements.
          </p>
        </div>

        <div className="hrms-actions-group">
          <button type="button" className="hrms-btn-secondary" onClick={fetchMyResignation} disabled={loading}>
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

      {/* Active Resignation Status View */}
      {activeReq ? (
        <div className="hrms-card">
          <div className="hrms-card-header">
            <h2 className="hrms-card-title"><Clock size={20} /> Exit Process Status</h2>
            {getStatusBadge(activeReq.status)}
          </div>

          <div className="hrms-card-body">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem', marginBottom: '1.5rem' }}>
              <div>
                <div className="hrms-metric-subtext">Resignation Submitted On</div>
                <div style={{ fontSize: '1.1rem', fontWeight: '700', color: '#0f172a' }}>
                  {activeReq.resignation_date || activeReq.created_at?.split('T')[0]}
                </div>
              </div>

              <div>
                <div className="hrms-metric-subtext">Intended / Approved Last Working Day</div>
                <div style={{ fontSize: '1.1rem', fontWeight: '700', color: '#134e4a' }}>
                  {activeReq.last_working_date || activeReq.intended_last_date}
                </div>
              </div>

              <div>
                <div className="hrms-metric-subtext">Notice Period Commitment</div>
                <div style={{ fontSize: '1.1rem', fontWeight: '700', color: '#0f172a' }}>
                  {activeReq.notice_period_days || 30} Days
                </div>
              </div>
            </div>

            <div style={{ backgroundColor: '#f8fafc', padding: '1rem', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '1.5rem' }}>
              <div style={{ fontSize: '0.85rem', fontWeight: '600', color: '#334155', marginBottom: '0.25rem' }}>Reason on Record:</div>
              <div style={{ fontSize: '0.85rem', color: '#64748b' }}>{activeReq.reason}</div>
            </div>

            {/* FnF Settlement Card */}
            {activeReq.status === 'SETTLED' && activeReq.fnf_settlement && (
              <div style={{ backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', padding: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                  <span className="hrms-badge hrms-badge-success" style={{ marginBottom: '0.25rem' }}>
                    Statement Ready
                  </span>
                  <div style={{ fontSize: '1.25rem', fontWeight: '700', color: '#134e4a' }}>
                    Net Settlement Amount: ₹{parseFloat(activeReq.fnf_settlement.net_settlement || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#166534' }}>
                    Includes prorated final month salary, leave encashment, and gratuity.
                  </div>
                </div>

                <button
                  type="button"
                  className="hrms-btn-primary"
                  onClick={() => handleDownloadStatement(activeReq.id || activeReq._firestore_id)}
                >
                  <Download size={15} /> Download FnF Statement PDF
                </button>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Resignation Submission Form */
        <div className="hrms-card" style={{ maxWidth: '700px' }}>
          <div className="hrms-card-header">
            <h2 className="hrms-card-title"><UserMinus size={20} /> Formal Resignation Submission</h2>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="hrms-card-body">
              <p style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '1.25rem' }}>
                Submitting this form initiates your formal handover notice period with Human Resources and triggers the clearance procedure.
              </p>

              <div className="hrms-form-group">
                <label>Intended Last Working Day *</label>
                <input
                  type="date"
                  className="hrms-input"
                  value={formState.intended_last_date}
                  onChange={(e) => setFormState({ ...formState, intended_last_date: e.target.value })}
                  required
                />
              </div>

              <div className="hrms-form-group">
                <label>Notice Period (Days) *</label>
                <input
                  type="number"
                  className="hrms-input"
                  value={formState.notice_period_days}
                  onChange={(e) => setFormState({ ...formState, notice_period_days: e.target.value })}
                  min="0"
                  required
                />
              </div>

              <div className="hrms-form-group">
                <label>Formal Reason for Separation *</label>
                <textarea
                  rows="4"
                  className="hrms-input"
                  placeholder="Provide your official reason for leaving..."
                  value={formState.reason}
                  onChange={(e) => setFormState({ ...formState, reason: e.target.value })}
                  required
                />
              </div>
            </div>

            <div className="hrms-card-header" style={{ justifyContent: 'flex-end', borderTop: '1px solid #f1f5f9', borderBottom: 'none' }}>
              <button type="submit" className="hrms-btn-primary" disabled={submitting}>
                <Send size={15} /> {submitting ? 'Submitting...' : 'Submit Resignation'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
