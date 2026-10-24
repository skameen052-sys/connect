import React, { useState, useEffect } from 'react';
import { 
  Briefcase, Users, Plus, CheckCircle2, ChevronRight, 
  Search, RefreshCw, X, UserPlus, ArrowRight, DollarSign 
} from 'lucide-react';
import recruitmentService from '../../services/recruitmentService';

export default function AdminRecruitment() {
  const [activeTab, setActiveTab] = useState('CANDIDATES'); // 'CANDIDATES' | 'JOBS'
  const [jobs, setJobs] = useState([]);
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [stageFilter, setStageFilter] = useState('ALL');

  // Modals state
  const [isJobModalOpen, setIsJobModalOpen] = useState(false);
  const [isCandidateModalOpen, setIsCandidateModalOpen] = useState(false);
  const [isConvertModalOpen, setIsConvertModalOpen] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState(null);

  const [jobForm, setJobForm] = useState({
    title: '',
    department: 'Engineering',
    location: 'HQ Office',
    employment_type: 'Full-time',
    vacancies: 2,
    description: '',
    requirements: '',
  });

  const [candidateForm, setCandidateForm] = useState({
    job_id: '',
    full_name: '',
    email: '',
    phone: '',
    experience_years: 3,
    expected_ctc: 600000,
    notice_period_days: 30,
    notes: 'Candidate applied via career portal',
  });

  const [convertForm, setConvertForm] = useState({
    employee_id: '',
    designation: '',
    department: 'Engineering',
    joining_date: new Date().toISOString().split('T')[0],
    basic_salary: 25000,
    hra: 10000,
    other_allowances: 5000,
  });

  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [jobsData, candidatesData] = await Promise.all([
        recruitmentService.getJobs(),
        recruitmentService.getCandidates(),
      ]);
      setJobs(jobsData);
      setCandidates(candidatesData);
      if (jobsData.length > 0 && !candidateForm.job_id) {
        setCandidateForm((prev) => ({ ...prev, job_id: jobsData[0].id || jobsData[0]._firestore_id }));
      }
    } catch (err) {
      console.error(err);
      setError('Failed to fetch recruitment data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateJob = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await recruitmentService.createJob(jobForm);
      setSuccessMsg('Job requisition created successfully.');
      setIsJobModalOpen(false);
      setJobForm({
        title: '',
        department: 'Engineering',
        location: 'HQ Office',
        employment_type: 'Full-time',
        vacancies: 2,
        description: '',
        requirements: '',
      });
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create job.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateCandidate = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await recruitmentService.createCandidate(candidateForm);
      setSuccessMsg('Candidate added to talent pipeline.');
      setIsCandidateModalOpen(false);
      setCandidateForm({
        job_id: jobs[0]?.id || '',
        full_name: '',
        email: '',
        phone: '',
        experience_years: 3,
        expected_ctc: 600000,
        notice_period_days: 30,
        notes: '',
      });
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add candidate.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleStageChange = async (candidateId, nextStage) => {
    try {
      await recruitmentService.updateCandidateStage(candidateId, { stage: nextStage });
      setSuccessMsg(`Candidate transitioned to ${nextStage}.`);
      fetchData();
    } catch (err) {
      setError('Could not update candidate stage.');
    }
  };

  const handleOpenConvert = (cand) => {
    setSelectedCandidate(cand);
    const generatedEmpId = `EMP-${Math.floor(1000 + Math.random() * 9000)}`;
    const matchingJob = jobs.find((j) => (j.id || j._firestore_id) === cand.job_id);

    setConvertForm({
      employee_id: generatedEmpId,
      designation: matchingJob ? matchingJob.title : 'Software Engineer',
      department: matchingJob ? matchingJob.department : 'Engineering',
      joining_date: new Date().toISOString().split('T')[0],
      basic_salary: 25000,
      hra: 10000,
      other_allowances: 5000,
    });
    setIsConvertModalOpen(true);
  };

  const handleConvertSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const res = await recruitmentService.convertToEmployee(
        selectedCandidate.id || selectedCandidate._firestore_id,
        convertForm
      );
      setSuccessMsg(res.message || 'Candidate converted to employee successfully!');
      setIsConvertModalOpen(false);
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Conversion failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const filteredCandidates = candidates.filter((c) => {
    const matchesSearch =
      (c.full_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (c.email || '').toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStage = stageFilter === 'ALL' || (c.stage || '').toUpperCase() === stageFilter;
    return matchesSearch && matchesStage;
  });

  const getStageBadge = (stage) => {
    const s = (stage || 'Applied').toUpperCase();
    if (s === 'HIRED') return <span className="hrms-badge hrms-badge-success">HIRED</span>;
    if (s === 'OFFERED') return <span className="hrms-badge hrms-badge-info">OFFERED</span>;
    if (s === 'INTERVIEW') return <span className="hrms-badge hrms-badge-warning">INTERVIEW</span>;
    if (s === 'SCREENING') return <span className="hrms-badge hrms-badge-neutral">SCREENING</span>;
    return <span className="hrms-badge hrms-badge-neutral">APPLIED</span>;
  };

  return (
    <div className="hrms-page-container">
      {/* Header */}
      <div className="hrms-page-header">
        <div className="hrms-page-title-group">
          <h1><Briefcase size={28} className="text-forest" /> Recruitment & Onboarding Pipeline</h1>
          <p className="hrms-page-subtitle">
            Manage job requisitions, track candidate progression across stages, and seamlessly convert hired candidates to active employee records.
          </p>
        </div>

        <div className="hrms-actions-group">
          <button type="button" className="hrms-btn-secondary" onClick={fetchData} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
          <button type="button" className="hrms-btn-secondary" onClick={() => setIsJobModalOpen(true)}>
            <Plus size={16} /> New Job Requisition
          </button>
          <button type="button" className="hrms-btn-primary" onClick={() => setIsCandidateModalOpen(true)}>
            <UserPlus size={16} /> Add Candidate
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
            <span className="hrms-metric-label">Open Requisitions</span>
            <div className="hrms-metric-icon-wrap"><Briefcase size={18} /></div>
          </div>
          <div className="hrms-metric-value">{jobs.length}</div>
          <div className="hrms-metric-subtext">Active open vacancies</div>
        </div>

        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Talent Pipeline</span>
            <div className="hrms-metric-icon-wrap"><Users size={18} /></div>
          </div>
          <div className="hrms-metric-value">{candidates.length}</div>
          <div className="hrms-metric-subtext">Active applicants tracked</div>
        </div>

        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Hired & Converted</span>
            <div className="hrms-metric-icon-wrap"><CheckCircle2 size={18} /></div>
          </div>
          <div className="hrms-metric-value">
            {candidates.filter((c) => (c.stage || '').toUpperCase() === 'HIRED').length}
          </div>
          <div className="hrms-metric-subtext">Successfully onboarded</div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '1rem', borderBottom: '1px solid #e2e8f0', marginBottom: '1.25rem' }}>
        <button
          type="button"
          onClick={() => setActiveTab('CANDIDATES')}
          style={{
            padding: '0.625rem 1rem',
            borderBottom: activeTab === 'CANDIDATES' ? '2px solid #134e4a' : 'none',
            color: activeTab === 'CANDIDATES' ? '#134e4a' : '#64748b',
            fontWeight: activeTab === 'CANDIDATES' ? '700' : '500',
            cursor: 'pointer',
          }}
        >
          Candidate Pipeline ({candidates.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('JOBS')}
          style={{
            padding: '0.625rem 1rem',
            borderBottom: activeTab === 'JOBS' ? '2px solid #134e4a' : 'none',
            color: activeTab === 'JOBS' ? '#134e4a' : '#64748b',
            fontWeight: activeTab === 'JOBS' ? '700' : '500',
            cursor: 'pointer',
          }}
        >
          Open Positions ({jobs.length})
        </button>
      </div>

      {/* Candidates View */}
      {activeTab === 'CANDIDATES' && (
        <>
          <div className="hrms-card">
            <div className="hrms-card-body" style={{ padding: '1rem 1.5rem' }}>
              <div className="hrms-filter-bar" style={{ margin: 0 }}>
                <div className="hrms-search-input-wrap">
                  <Search size={16} />
                  <input
                    type="text"
                    className="hrms-input"
                    placeholder="Search candidates by name or email..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>

                <select
                  className="hrms-select"
                  value={stageFilter}
                  onChange={(e) => setStageFilter(e.target.value)}
                >
                  <option value="ALL">All Stages</option>
                  <option value="APPLIED">Applied</option>
                  <option value="SCREENING">Screening</option>
                  <option value="INTERVIEW">Interview</option>
                  <option value="OFFERED">Offered</option>
                  <option value="HIRED">Hired</option>
                </select>
              </div>
            </div>
          </div>

          <div className="hrms-card">
            <div className="hrms-table-container">
              <table className="hrms-table">
                <thead>
                  <tr>
                    <th>Candidate</th>
                    <th>Experience</th>
                    <th>Expected CTC</th>
                    <th>Notice Period</th>
                    <th>Stage</th>
                    <th>Next Pipeline Action</th>
                    <th>Onboard Employee</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredCandidates.length === 0 ? (
                    <tr>
                      <td colSpan="7">
                        <div className="hrms-empty-state">
                          <Users className="hrms-empty-icon" />
                          <p>No candidates found in this stage.</p>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    filteredCandidates.map((c) => {
                      const cId = c.id || c._firestore_id;
                      const stage = c.stage || 'Applied';
                      const isConverted = c.converted_to_employee;
                      return (
                        <tr key={cId}>
                          <td>
                            <strong>{c.full_name}</strong>
                            <div className="hrms-metric-subtext">{c.email} • {c.phone}</div>
                          </td>
                          <td>{c.experience_years} Years</td>
                          <td>₹{parseFloat(c.expected_ctc || 0).toLocaleString('en-IN')}</td>
                          <td>{c.notice_period_days || 30} Days</td>
                          <td>{getStageBadge(c.stage)}</td>
                          <td>
                            <div style={{ display: 'flex', gap: '0.35rem' }}>
                              {stage === 'Applied' && (
                                <button
                                  type="button"
                                  className="hrms-btn-secondary"
                                  style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                                  onClick={() => handleStageChange(cId, 'Screening')}
                                >
                                  Screen
                                </button>
                              )}
                              {stage === 'Screening' && (
                                <button
                                  type="button"
                                  className="hrms-btn-secondary"
                                  style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                                  onClick={() => handleStageChange(cId, 'Interview')}
                                >
                                  Interview
                                </button>
                              )}
                              {stage === 'Interview' && (
                                <button
                                  type="button"
                                  className="hrms-btn-secondary"
                                  style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                                  onClick={() => handleStageChange(cId, 'Offered')}
                                >
                                  Make Offer
                                </button>
                              )}
                              {stage === 'Offered' && (
                                <button
                                  type="button"
                                  className="hrms-btn-primary"
                                  style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                                  onClick={() => handleStageChange(cId, 'Hired')}
                                >
                                  Mark Hired
                                </button>
                              )}
                              {stage === 'Hired' && (
                                <span style={{ fontSize: '0.75rem', color: '#16a34a', fontWeight: '600' }}>Ready</span>
                              )}
                            </div>
                          </td>
                          <td>
                            {isConverted ? (
                              <span className="hrms-badge hrms-badge-success">
                                <CheckCircle2 size={12} /> {c.employee_id}
                              </span>
                            ) : (
                              <button
                                type="button"
                                className="hrms-btn-primary"
                                style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem', backgroundColor: '#0f766e' }}
                                onClick={() => handleOpenConvert(c)}
                                disabled={stage !== 'Hired'}
                                title={stage !== 'Hired' ? 'Candidate must reach Hired stage first' : 'Convert to Employee'}
                              >
                                <UserPlus size={13} /> Onboard
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Jobs View */}
      {activeTab === 'JOBS' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1rem' }}>
          {jobs.map((j) => (
            <div key={j.id || j._firestore_id} className="hrms-card" style={{ marginBottom: 0 }}>
              <div className="hrms-card-body">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: '#0f172a', margin: 0 }}>{j.title}</h3>
                  <span className="hrms-badge hrms-badge-success">{j.status || 'OPEN'}</span>
                </div>
                <div className="hrms-metric-subtext" style={{ marginBottom: '0.75rem' }}>
                  {j.department} • {j.location} • {j.employment_type}
                </div>
                <p style={{ fontSize: '0.85rem', color: '#475569', marginBottom: '1rem' }}>{j.description}</p>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#64748b', borderTop: '1px solid #f1f5f9', paddingTop: '0.75rem' }}>
                  <span>Vacancies: <strong>{j.vacancies}</strong></span>
                  <span>Posted: {j.created_at?.split('T')[0]}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Job Modal */}
      {isJobModalOpen && (
        <div className="hrms-modal-overlay" onClick={() => setIsJobModalOpen(false)}>
          <div className="hrms-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="hrms-modal-header">
              <h3 className="hrms-modal-title">Create Job Requisition</h3>
              <button type="button" className="hrms-modal-close" onClick={() => setIsJobModalOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleCreateJob}>
              <div className="hrms-modal-body">
                <div className="hrms-form-group">
                  <label>Position Title *</label>
                  <input
                    type="text"
                    className="hrms-input"
                    placeholder="e.g. Senior Full-Stack Engineer"
                    value={jobForm.title}
                    onChange={(e) => setJobForm({ ...jobForm, title: e.target.value })}
                    required
                  />
                </div>

                <div className="hrms-form-row">
                  <div className="hrms-form-group">
                    <label>Department</label>
                    <select
                      className="hrms-select"
                      style={{ width: '100%' }}
                      value={jobForm.department}
                      onChange={(e) => setJobForm({ ...jobForm, department: e.target.value })}
                    >
                      <option value="Engineering">Engineering</option>
                      <option value="Human Resources">Human Resources</option>
                      <option value="Finance & Payroll">Finance & Payroll</option>
                      <option value="Product & Design">Product & Design</option>
                      <option value="Operations">Operations</option>
                    </select>
                  </div>

                  <div className="hrms-form-group">
                    <label>Open Vacancies</label>
                    <input
                      type="number"
                      className="hrms-input"
                      value={jobForm.vacancies}
                      onChange={(e) => setJobForm({ ...jobForm, vacancies: e.target.value })}
                      min="1"
                      required
                    />
                  </div>
                </div>

                <div className="hrms-form-group">
                  <label>Job Description *</label>
                  <textarea
                    rows="3"
                    className="hrms-input"
                    value={jobForm.description}
                    onChange={(e) => setJobForm({ ...jobForm, description: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="hrms-modal-footer">
                <button type="button" className="hrms-btn-secondary" onClick={() => setIsJobModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="hrms-btn-primary" disabled={submitting}>
                  {submitting ? 'Creating...' : 'Post Requisition'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Candidate Modal */}
      {isCandidateModalOpen && (
        <div className="hrms-modal-overlay" onClick={() => setIsCandidateModalOpen(false)}>
          <div className="hrms-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="hrms-modal-header">
              <h3 className="hrms-modal-title">Register Candidate</h3>
              <button type="button" className="hrms-modal-close" onClick={() => setIsCandidateModalOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleCreateCandidate}>
              <div className="hrms-modal-body">
                <div className="hrms-form-group">
                  <label>Candidate Full Name *</label>
                  <input
                    type="text"
                    className="hrms-input"
                    placeholder="e.g. Priya Sharma"
                    value={candidateForm.full_name}
                    onChange={(e) => setCandidateForm({ ...candidateForm, full_name: e.target.value })}
                    required
                  />
                </div>

                <div className="hrms-form-row">
                  <div className="hrms-form-group">
                    <label>Email Address *</label>
                    <input
                      type="email"
                      className="hrms-input"
                      placeholder="priya@example.com"
                      value={candidateForm.email}
                      onChange={(e) => setCandidateForm({ ...candidateForm, email: e.target.value })}
                      required
                    />
                  </div>

                  <div className="hrms-form-group">
                    <label>Phone Number *</label>
                    <input
                      type="tel"
                      className="hrms-input"
                      placeholder="+91 98765 43210"
                      value={candidateForm.phone}
                      onChange={(e) => setCandidateForm({ ...candidateForm, phone: e.target.value })}
                      required
                    />
                  </div>
                </div>

                <div className="hrms-form-row">
                  <div className="hrms-form-group">
                    <label>Experience (Years)</label>
                    <input
                      type="number"
                      className="hrms-input"
                      value={candidateForm.experience_years}
                      onChange={(e) => setCandidateForm({ ...candidateForm, experience_years: e.target.value })}
                    />
                  </div>

                  <div className="hrms-form-group">
                    <label>Expected CTC (₹/Year)</label>
                    <input
                      type="number"
                      className="hrms-input"
                      value={candidateForm.expected_ctc}
                      onChange={(e) => setCandidateForm({ ...candidateForm, expected_ctc: e.target.value })}
                    />
                  </div>
                </div>
              </div>

              <div className="hrms-modal-footer">
                <button type="button" className="hrms-btn-secondary" onClick={() => setIsCandidateModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="hrms-btn-primary" disabled={submitting}>
                  {submitting ? 'Adding...' : 'Add Candidate'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Convert Candidate to Employee Modal */}
      {isConvertModalOpen && selectedCandidate && (
        <div className="hrms-modal-overlay" onClick={() => setIsConvertModalOpen(false)}>
          <div className="hrms-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="hrms-modal-header">
              <h3 className="hrms-modal-title">Convert Candidate to Active Employee</h3>
              <button type="button" className="hrms-modal-close" onClick={() => setIsConvertModalOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleConvertSubmit}>
              <div className="hrms-modal-body">
                <p style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '1.25rem' }}>
                  Onboarding {selectedCandidate.full_name} will automatically create their Employee Directory record and configure their initial salary structure for payroll.
                </p>

                <div className="hrms-form-row">
                  <div className="hrms-form-group">
                    <label>Assigned Employee ID *</label>
                    <input
                      type="text"
                      className="hrms-input"
                      value={convertForm.employee_id}
                      onChange={(e) => setConvertForm({ ...convertForm, employee_id: e.target.value })}
                      required
                    />
                  </div>

                  <div className="hrms-form-group">
                    <label>Joining Date *</label>
                    <input
                      type="date"
                      className="hrms-input"
                      value={convertForm.joining_date}
                      onChange={(e) => setConvertForm({ ...convertForm, joining_date: e.target.value })}
                      required
                    />
                  </div>
                </div>

                <div className="hrms-form-row">
                  <div className="hrms-form-group">
                    <label>Designation *</label>
                    <input
                      type="text"
                      className="hrms-input"
                      value={convertForm.designation}
                      onChange={(e) => setConvertForm({ ...convertForm, designation: e.target.value })}
                      required
                    />
                  </div>

                  <div className="hrms-form-group">
                    <label>Department</label>
                    <select
                      className="hrms-select"
                      style={{ width: '100%' }}
                      value={convertForm.department}
                      onChange={(e) => setConvertForm({ ...convertForm, department: e.target.value })}
                    >
                      <option value="Engineering">Engineering</option>
                      <option value="Human Resources">Human Resources</option>
                      <option value="Finance & Payroll">Finance & Payroll</option>
                      <option value="Product & Design">Product & Design</option>
                      <option value="Operations">Operations</option>
                    </select>
                  </div>
                </div>

                <div className="hrms-form-row">
                  <div className="hrms-form-group">
                    <label>Basic Pay (₹/Month)</label>
                    <input
                      type="number"
                      className="hrms-input"
                      value={convertForm.basic_salary}
                      onChange={(e) => setConvertForm({ ...convertForm, basic_salary: e.target.value })}
                    />
                  </div>

                  <div className="hrms-form-group">
                    <label>HRA (₹/Month)</label>
                    <input
                      type="number"
                      className="hrms-input"
                      value={convertForm.hra}
                      onChange={(e) => setConvertForm({ ...convertForm, hra: e.target.value })}
                    />
                  </div>
                </div>
              </div>

              <div className="hrms-modal-footer">
                <button type="button" className="hrms-btn-secondary" onClick={() => setIsConvertModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="hrms-btn-primary" disabled={submitting}>
                  {submitting ? 'Onboarding...' : 'Onboard & Generate Profile'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
