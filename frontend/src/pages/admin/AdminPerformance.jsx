import React, { useState, useEffect } from 'react';
import { 
  Award, Target, Star, TrendingUp, Search, RefreshCw, 
  Plus, CheckCircle2, X 
} from 'lucide-react';
import performanceService from '../../services/performanceService';
import employeeService from '../../services/employeeService';

export default function AdminPerformance() {
  const [activeTab, setActiveTab] = useState('REVIEWS'); // 'REVIEWS' | 'GOALS'
  const [reviews, setReviews] = useState([]);
  const [goals, setGoals] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  // Modals state
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);
  const [isGoalModalOpen, setIsGoalModalOpen] = useState(false);

  const [reviewForm, setReviewForm] = useState({
    employee_id: '',
    review_period: 'Annual 2026',
    rating: 4.5,
    strengths: 'Outstanding system delivery and cross-team collaboration.',
    areas_for_improvement: 'Continue mentoring junior engineers.',
    manager_feedback: 'Consistently exceeded sprint goals and maintained 99.9% uptime.',
    recommended_increment_pct: 12.0,
  });

  const [goalForm, setGoalForm] = useState({
    employee_id: '',
    title: '',
    description: '',
    target_date: new Date().toISOString().split('T')[0],
    weightage: 25,
  });

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [revs, gls, emps] = await Promise.all([
        performanceService.getReviews(),
        performanceService.getGoals(),
        employeeService.getEmployees(),
      ]);
      setReviews(revs);
      setGoals(gls);
      setEmployees(emps);
      if (emps.length > 0) {
        const firstId = emps[0].employee_id || emps[0].employeeId || emps[0].id;
        if (!reviewForm.employee_id) setReviewForm((p) => ({ ...p, employee_id: firstId }));
        if (!goalForm.employee_id) setGoalForm((p) => ({ ...p, employee_id: firstId }));
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
      await performanceService.submitReview({
        ...reviewForm,
        rating: parseFloat(reviewForm.rating),
        recommended_increment_pct: parseFloat(reviewForm.recommended_increment_pct) || 0,
      });
      setSuccessMsg('Performance appraisal review recorded successfully.');
      setIsReviewModalOpen(false);
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit appraisal.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateGoal = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await performanceService.createGoal(goalForm);
      setSuccessMsg('Performance goal assigned successfully.');
      setIsGoalModalOpen(false);
      setGoalForm((p) => ({ ...p, title: '', description: '' }));
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to assign goal.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateProgress = async (goalId, newProgress) => {
    try {
      await performanceService.updateGoalProgress(goalId, { progress: newProgress });
      fetchData();
    } catch (err) {
      setError('Could not update goal progress.');
    }
  };

  const filteredReviews = reviews.filter((r) =>
    (r.employee_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (r.employee_id || '').toLowerCase().includes(searchTerm.toLowerCase())
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
            Track workforce OKRs, record 1–5 performance evaluations, and direct salary increment recommendations.
          </p>
        </div>

        <div className="hrms-actions-group">
          <button type="button" className="hrms-btn-secondary" onClick={fetchData} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
          <button type="button" className="hrms-btn-secondary" onClick={() => setIsGoalModalOpen(true)}>
            <Plus size={16} /> Assign Goal
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
            <span className="hrms-metric-label">Active Company OKRs</span>
            <div className="hrms-metric-icon-wrap"><Target size={18} /></div>
          </div>
          <div className="hrms-metric-value">{goals.length}</div>
          <div className="hrms-metric-subtext">Employee goals monitored</div>
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

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '1rem', borderBottom: '1px solid #e2e8f0', marginBottom: '1.25rem' }}>
        <button
          type="button"
          onClick={() => setActiveTab('REVIEWS')}
          style={{
            padding: '0.625rem 1rem',
            borderBottom: activeTab === 'REVIEWS' ? '2px solid #134e4a' : 'none',
            color: activeTab === 'REVIEWS' ? '#134e4a' : '#64748b',
            fontWeight: activeTab === 'REVIEWS' ? '700' : '500',
            cursor: 'pointer',
          }}
        >
          Appraisal Reviews ({reviews.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('GOALS')}
          style={{
            padding: '0.625rem 1rem',
            borderBottom: activeTab === 'GOALS' ? '2px solid #134e4a' : 'none',
            color: activeTab === 'GOALS' ? '#134e4a' : '#64748b',
            fontWeight: activeTab === 'GOALS' ? '700' : '500',
            cursor: 'pointer',
          }}
        >
          Performance Goals ({goals.length})
        </button>
      </div>

      {/* Reviews Tab */}
      {activeTab === 'REVIEWS' && (
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
      )}

      {/* Goals Tab */}
      {activeTab === 'GOALS' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1rem' }}>
          {goals.map((g, idx) => (
            <div key={idx} className="hrms-card" style={{ marginBottom: 0 }}>
              <div className="hrms-card-body">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                  <h3 style={{ fontSize: '1rem', fontWeight: '700', color: '#0f172a', margin: 0 }}>{g.title}</h3>
                  <span className="hrms-badge hrms-badge-info">{g.weightage || 20}% Weight</span>
                </div>
                <div className="hrms-metric-subtext" style={{ marginBottom: '0.75rem' }}>
                  Assigned to: {g.employee_id} • Target: {g.target_date}
                </div>
                <p style={{ fontSize: '0.85rem', color: '#475569', marginBottom: '1rem' }}>{g.description}</p>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.25rem' }}>
                    <span>Completion</span>
                    <strong>{g.progress || 0}%</strong>
                  </div>
                  <div style={{ height: '6px', backgroundColor: '#e2e8f0', borderRadius: '999px', overflow: 'hidden' }}>
                    <div style={{ width: `${g.progress || 0}%`, height: '100%', backgroundColor: '#134e4a' }} />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

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
                      {employees.map((emp) => (
                        <option key={emp.employee_id || emp.id} value={emp.employee_id || emp.id}>
                          {emp.name || emp.full_name} ({emp.employee_id || emp.id})
                        </option>
                      ))}
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

      {/* Assign Goal Modal */}
      {isGoalModalOpen && (
        <div className="hrms-modal-overlay" onClick={() => setIsGoalModalOpen(false)}>
          <div className="hrms-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="hrms-modal-header">
              <h3 className="hrms-modal-title">Assign OKR / Performance Goal</h3>
              <button type="button" className="hrms-modal-close" onClick={() => setIsGoalModalOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleCreateGoal}>
              <div className="hrms-modal-body">
                <div className="hrms-form-group">
                  <label>Employee *</label>
                  <select
                    className="hrms-select"
                    style={{ width: '100%' }}
                    value={goalForm.employee_id}
                    onChange={(e) => setGoalForm({ ...goalForm, employee_id: e.target.value })}
                    required
                  >
                    {employees.map((emp) => (
                      <option key={emp.employee_id || emp.id} value={emp.employee_id || emp.id}>
                        {emp.name || emp.full_name} ({emp.employee_id || emp.id})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="hrms-form-group">
                  <label>Goal Title *</label>
                  <input
                    type="text"
                    className="hrms-input"
                    placeholder="e.g. Complete ISO 27001 Security Audit"
                    value={goalForm.title}
                    onChange={(e) => setGoalForm({ ...goalForm, title: e.target.value })}
                    required
                  />
                </div>

                <div className="hrms-form-group">
                  <label>Description & Success Metrics</label>
                  <textarea
                    rows="2"
                    className="hrms-input"
                    value={goalForm.description}
                    onChange={(e) => setGoalForm({ ...goalForm, description: e.target.value })}
                  />
                </div>

                <div className="hrms-form-row">
                  <div className="hrms-form-group">
                    <label>Target Completion Date</label>
                    <input
                      type="date"
                      className="hrms-input"
                      value={goalForm.target_date}
                      onChange={(e) => setGoalForm({ ...goalForm, target_date: e.target.value })}
                      required
                    />
                  </div>

                  <div className="hrms-form-group">
                    <label>Weightage %</label>
                    <input
                      type="number"
                      className="hrms-input"
                      value={goalForm.weightage}
                      onChange={(e) => setGoalForm({ ...goalForm, weightage: e.target.value })}
                      min="5"
                      max="100"
                    />
                  </div>
                </div>
              </div>

              <div className="hrms-modal-footer">
                <button type="button" className="hrms-btn-secondary" onClick={() => setIsGoalModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="hrms-btn-primary" disabled={submitting}>
                  {submitting ? 'Assigning...' : 'Assign Goal'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
