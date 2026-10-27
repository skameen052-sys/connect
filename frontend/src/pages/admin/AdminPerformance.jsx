import React, { useState, useEffect } from 'react';
import { 
  Award, Star, TrendingUp, Search, RefreshCw, X 
} from 'lucide-react';
import performanceService from '../../services/performanceService';
import employeeService from '../../services/employeeService';

export default function AdminPerformance() {
  const [reviews, setReviews] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  // Modals state
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);

  const [reviewForm, setReviewForm] = useState({
    employee_id: '',
    review_period: 'Annual 2026',
    rating: 4.5,
    strengths: 'Outstanding system delivery and cross-team collaboration.',
    areas_for_improvement: 'Continue mentoring junior engineers.',
    manager_feedback: 'Consistently exceeded sprint goals and maintained 99.9% uptime.',
    recommended_increment_pct: 12.0,
  });

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [revs, emps] = await Promise.all([
        performanceService.getReviews(),
        employeeService.getEmployees(),
      ]);
      setReviews(revs);
      setEmployees(emps);
      if (emps.length > 0) {
        const firstId = emps[0].employeeId || emps[0].employee_id || emps[0].id;
        if (!reviewForm.employee_id) setReviewForm((p) => ({ ...p, employee_id: firstId }));
      }
    } catch (err) {
      console.error(err);
      setError('Failed to fetch performance records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateReview = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const selectedEmp = employees.find((emp) => 
        (emp.employeeId || emp.employee_id || emp.id) === reviewForm.employee_id ||
        emp.id === reviewForm.employee_id ||
        emp.email === reviewForm.employee_id
      );

      await performanceService.submitReview({
        ...reviewForm,
        employee_id: reviewForm.employee_id,
        employee_name: selectedEmp ? (selectedEmp.name || selectedEmp.full_name || selectedEmp.fullName) : '',
        employee_email: selectedEmp?.email || '',
        department: selectedEmp ? (selectedEmp.department || selectedEmp.dept) : '',
        rating: parseFloat(reviewForm.rating),
        recommended_increment_pct: parseFloat(reviewForm.recommended_increment_pct) || 0,
      });
      const targetName = selectedEmp ? (selectedEmp.name || selectedEmp.full_name || selectedEmp.fullName) : reviewForm.employee_id;
      setSuccessMsg(`Performance appraisal for ${targetName} submitted and reflected on employee portal.`);
      setIsReviewModalOpen(false);
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit appraisal.');
    } finally {
      setSubmitting(false);
    }
  };

  const filteredReviews = reviews.filter((r) =>
    (r.employee_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (r.employee_id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (r.employeeId || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (r.department || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const avgRating = reviews.length
    ? (reviews.reduce((acc, r) => acc + (parseFloat(r.rating) || 0), 0) / reviews.length).toFixed(1)
    : '4.5';

  return (
    <div className="hrms-page-container">
      {/* Header */}
      <div className="hrms-page-header">
        <div className="hrms-page-title-group">
          <h1><Award size={28} className="text-forest" /> Performance Management & Appraisals</h1>
          <p className="hrms-page-subtitle">
            Record 1–5 performance evaluations and direct salary increment recommendations.
          </p>
        </div>

        <div className="hrms-actions-group">
          <button type="button" className="hrms-btn-secondary" onClick={fetchData} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
          <button type="button" className="hrms-btn-primary" onClick={() => setIsReviewModalOpen(true)}>
            <Star size={16} /> Submit Appraisal
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
            <span className="hrms-metric-label">Average Performance Rating</span>
            <div className="hrms-metric-icon-wrap"><Star size={18} /></div>
          </div>
          <div className="hrms-metric-value">{avgRating} / 5.0</div>
          <div className="hrms-metric-subtext">Across completed review cycles</div>
        </div>

        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Appraisals Recorded</span>
            <div className="hrms-metric-icon-wrap"><TrendingUp size={18} /></div>
          </div>
          <div className="hrms-metric-value">{reviews.length}</div>
          <div className="hrms-metric-subtext">Completed evaluations</div>
        </div>
      </div>

      {/* Appraisal Reviews Header & Search */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e2e8f0', marginBottom: '1.25rem', paddingBottom: '0.5rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div style={{ borderBottom: '2px solid #134e4a', paddingBottom: '0.5rem', marginBottom: '-0.5rem', color: '#134e4a', fontWeight: '700', fontSize: '1rem' }}>
          Appraisal Reviews ({reviews.length})
        </div>
        <div className="hrms-search-input-wrap" style={{ minWidth: '260px' }}>
          <Search size={16} />
          <input
            type="text"
            className="hrms-input"
            placeholder="Search employee name or ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {/* Reviews Table */}
      <div className="hrms-card">
        <div className="hrms-table-container">
          <table className="hrms-table">
            <thead>
              <tr>
                <th>Employee</th>
                <th>Review Cycle</th>
                <th>Appraisal Rating</th>
                <th>Manager Feedback & Strengths</th>
                <th>Increment %</th>
                <th>Evaluated By</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {filteredReviews.length === 0 ? (
                <tr>
                  <td colSpan="7">
                    <div className="hrms-empty-state">
                      <Award className="hrms-empty-icon" />
                      <p>No appraisal review records found.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredReviews.map((r, idx) => (
                  <tr key={idx}>
                    <td>
                      <strong>{r.employee_name || r.employee_id}</strong>
                      <div className="hrms-metric-subtext">{r.employee_id} • {r.department}</div>
                    </td>
                    <td>{r.review_period}</td>
                    <td>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', backgroundColor: '#fef3c7', color: '#b45309', padding: '0.25rem 0.5rem', borderRadius: '6px', fontWeight: '700', fontSize: '0.85rem' }}>
                        <Star size={13} fill="#b45309" /> {parseFloat(r.rating).toFixed(1)} / 5.0
                      </span>
                    </td>
                    <td style={{ maxWidth: '300px' }}>
                      <div style={{ fontSize: '0.85rem', fontWeight: '500', color: '#1e293b' }}>{r.strengths}</div>
                      <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{r.manager_feedback}</div>
                    </td>
                    <td>
                      <strong style={{ color: '#16a34a' }}>+{r.recommended_increment_pct || 0}%</strong>
                    </td>
                    <td>{r.evaluated_by}</td>
                    <td>{r.created_at?.split('T')[0]}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Submit Review Modal */}
      {isReviewModalOpen && (
        <div className="hrms-modal-overlay" onClick={() => setIsReviewModalOpen(false)}>
          <div className="hrms-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="hrms-modal-header">
              <h3 className="hrms-modal-title">Record Performance Appraisal</h3>
              <button type="button" className="hrms-modal-close" onClick={() => setIsReviewModalOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleCreateReview}>
              <div className="hrms-modal-body">
                <div className="hrms-form-row">
                  <div className="hrms-form-group">
                    <label>Employee *</label>
                    <select
                      className="hrms-select"
                      style={{ width: '100%' }}
                      value={reviewForm.employee_id}
                      onChange={(e) => setReviewForm({ ...reviewForm, employee_id: e.target.value })}
                      required
                    >
                      {employees.map((emp) => {
                        const empEid = emp.employeeId || emp.employee_id || emp.id;
                        const empName = emp.name || emp.full_name || emp.fullName || 'Employee';
                        const empDept = emp.department || emp.dept || '';
                        return (
                          <option key={emp.id || empEid} value={empEid}>
                            {empName} ({empEid}){empDept ? ` • ${empDept}` : ''}
                          </option>
                        );
                      })}
                    </select>
                  </div>

                  <div className="hrms-form-group">
                    <label>Rating (1.0 - 5.0) *</label>
                    <input
                      type="number"
                      step="0.1"
                      min="1.0"
                      max="5.0"
                      className="hrms-input"
                      value={reviewForm.rating}
                      onChange={(e) => setReviewForm({ ...reviewForm, rating: e.target.value })}
                      required
                    />
                  </div>
                </div>

                <div className="hrms-form-group">
                  <label>Strengths & Major Accomplishments</label>
                  <textarea
                    rows="2"
                    className="hrms-input"
                    value={reviewForm.strengths}
                    onChange={(e) => setReviewForm({ ...reviewForm, strengths: e.target.value })}
                  />
                </div>

                <div className="hrms-form-group">
                  <label>Areas for Development</label>
                  <textarea
                    rows="2"
                    className="hrms-input"
                    value={reviewForm.areas_for_improvement}
                    onChange={(e) => setReviewForm({ ...reviewForm, areas_for_improvement: e.target.value })}
                  />
                </div>

                <div className="hrms-form-row">
                  <div className="hrms-form-group">
                    <label>Recommended Salary Increment %</label>
                    <input
                      type="number"
                      step="0.5"
                      className="hrms-input"
                      value={reviewForm.recommended_increment_pct}
                      onChange={(e) => setReviewForm({ ...reviewForm, recommended_increment_pct: e.target.value })}
                    />
                  </div>

                  <div className="hrms-form-group">
                    <label>Review Period</label>
                    <input
                      type="text"
                      className="hrms-input"
                      value={reviewForm.review_period}
                      onChange={(e) => setReviewForm({ ...reviewForm, review_period: e.target.value })}
                    />
                  </div>
                </div>
              </div>

              <div className="hrms-modal-footer">
                <button type="button" className="hrms-btn-secondary" onClick={() => setIsReviewModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="hrms-btn-primary" disabled={submitting}>
                  {submitting ? 'Submitting...' : 'Save Appraisal'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
