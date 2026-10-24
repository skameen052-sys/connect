import React, { useState, useEffect } from 'react';
import { 
  Building2, Plus, Users, Briefcase, RefreshCw, X 
} from 'lucide-react';
import departmentService from '../../services/departmentService';

export default function AdminDepartments() {
  const [departments, setDepartments] = useState([]);
  const [designations, setDesignations] = useState([]);
  const [loading, setLoading] = useState(true);

  // Modals state
  const [isDeptModalOpen, setIsDeptModalOpen] = useState(false);
  const [isDesigModalOpen, setIsDesigModalOpen] = useState(false);

  const [deptForm, setDeptForm] = useState({
    name: '',
    code: '',
    description: '',
  });

  const [desigForm, setDesigForm] = useState({
    title: '',
    department: 'Engineering',
    level: 'Mid',
    description: '',
  });

  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [depts, desigs] = await Promise.all([
        departmentService.getDepartments(),
        departmentService.getDesignations(),
      ]);
      setDepartments(depts);
      setDesignations(desigs);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch departments and designations.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateDept = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await departmentService.createDepartment(deptForm);
      setSuccessMsg('Department created successfully.');
      setIsDeptModalOpen(false);
      setDeptForm({ name: '', code: '', description: '' });
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create department.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateDesig = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await departmentService.createDesignation(desigForm);
      setSuccessMsg('Job designation created successfully.');
      setIsDesigModalOpen(false);
      setDesigForm({ title: '', department: departments[0]?.name || 'Engineering', level: 'Mid', description: '' });
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create designation.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="hrms-page-container">
      {/* Header */}
      <div className="hrms-page-header">
        <div className="hrms-page-title-group">
          <h1><Building2 size={28} className="text-forest" /> Departments & Job Roles</h1>
          <p className="hrms-page-subtitle">
            Configure organizational functional divisions, job titles, seniority levels, and workforce allocation.
          </p>
        </div>

        <div className="hrms-actions-group">
          <button type="button" className="hrms-btn-secondary" onClick={fetchData} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
          <button type="button" className="hrms-btn-secondary" onClick={() => setIsDesigModalOpen(true)}>
            <Plus size={16} /> New Designation
          </button>
          <button type="button" className="hrms-btn-primary" onClick={() => setIsDeptModalOpen(true)}>
            <Building2 size={16} /> New Department
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

      {/* Departments Grid */}
      <h2 style={{ fontSize: '1.15rem', fontWeight: '700', marginBottom: '0.75rem', color: '#0f172a' }}>
        Operational Departments ({departments.length})
      </h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        {departments.map((d, i) => (
          <div key={i} className="hrms-card" style={{ marginBottom: 0 }}>
            <div className="hrms-card-body">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span className="hrms-badge hrms-badge-info">{d.code || 'DEPT'}</span>
                <span style={{ fontSize: '0.85rem', color: '#166534', fontWeight: '600' }}>
                  {d.employee_count || 0} Staff
                </span>
              </div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: '700', margin: '0 0 0.5rem 0', color: '#111827' }}>
                {d.name}
              </h3>
              <p style={{ fontSize: '0.825rem', color: '#64748b', margin: 0 }}>
                {d.description || 'Organizational functional unit'}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Designations Table */}
      <div className="hrms-card">
        <div className="hrms-card-header">
          <h2 className="hrms-card-title"><Briefcase size={20} /> Standard Designations & Job Titles</h2>
          <span className="hrms-metric-subtext">{designations.length} Active Positions</span>
        </div>

        <div className="hrms-table-container">
          <table className="hrms-table">
            <thead>
              <tr>
                <th>Job Title / Designation</th>
                <th>Department</th>
                <th>Seniority Level</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {designations.map((desig, idx) => (
                <tr key={idx}>
                  <td>
                    <strong>{desig.title}</strong>
                  </td>
                  <td>{desig.department}</td>
                  <td>
                    <span className="hrms-badge hrms-badge-neutral">{desig.level || 'Mid'}</span>
                  </td>
                  <td>
                    <span className="hrms-badge hrms-badge-success">Active</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Dept Modal */}
      {isDeptModalOpen && (
        <div className="hrms-modal-overlay" onClick={() => setIsDeptModalOpen(false)}>
          <div className="hrms-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="hrms-modal-header">
              <h3 className="hrms-modal-title">Create Department</h3>
              <button type="button" className="hrms-modal-close" onClick={() => setIsDeptModalOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleCreateDept}>
              <div className="hrms-modal-body">
                <div className="hrms-form-group">
                  <label>Department Name *</label>
                  <input
                    type="text"
                    className="hrms-input"
                    placeholder="e.g. Quality Assurance"
                    value={deptForm.name}
                    onChange={(e) => setDeptForm({ ...deptForm, name: e.target.value })}
                    required
                  />
                </div>

                <div className="hrms-form-group">
                  <label>Department Code</label>
                  <input
                    type="text"
                    className="hrms-input"
                    placeholder="e.g. QA"
                    value={deptForm.code}
                    onChange={(e) => setDeptForm({ ...deptForm, code: e.target.value })}
                  />
                </div>

                <div className="hrms-form-group">
                  <label>Description</label>
                  <textarea
                    rows="3"
                    className="hrms-input"
                    placeholder="Responsibilities and functional scope..."
                    value={deptForm.description}
                    onChange={(e) => setDeptForm({ ...deptForm, description: e.target.value })}
                  />
                </div>
              </div>

              <div className="hrms-modal-footer">
                <button type="button" className="hrms-btn-secondary" onClick={() => setIsDeptModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="hrms-btn-primary" disabled={submitting}>
                  {submitting ? 'Creating...' : 'Save Department'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create Desig Modal */}
      {isDesigModalOpen && (
        <div className="hrms-modal-overlay" onClick={() => setIsDesigModalOpen(false)}>
          <div className="hrms-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="hrms-modal-header">
              <h3 className="hrms-modal-title">Create Job Designation</h3>
              <button type="button" className="hrms-modal-close" onClick={() => setIsDesigModalOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleCreateDesig}>
              <div className="hrms-modal-body">
                <div className="hrms-form-group">
                  <label>Job Title *</label>
                  <input
                    type="text"
                    className="hrms-input"
                    placeholder="e.g. Principal Architect"
                    value={desigForm.title}
                    onChange={(e) => setDesigForm({ ...desigForm, title: e.target.value })}
                    required
                  />
                </div>

                <div className="hrms-form-row">
                  <div className="hrms-form-group">
                    <label>Department</label>
                    <select
                      className="hrms-select"
                      style={{ width: '100%' }}
                      value={desigForm.department}
                      onChange={(e) => setDesigForm({ ...desigForm, department: e.target.value })}
                    >
                      {departments.map((d, i) => (
                        <option key={i} value={d.name}>{d.name}</option>
                      ))}
                    </select>
                  </div>

                  <div className="hrms-form-group">
                    <label>Seniority Level</label>
                    <select
                      className="hrms-select"
                      style={{ width: '100%' }}
                      value={desigForm.level}
                      onChange={(e) => setDesigForm({ ...desigForm, level: e.target.value })}
                    >
                      <option value="Junior">Junior</option>
                      <option value="Mid">Mid</option>
                      <option value="Senior">Senior</option>
                      <option value="Lead">Lead</option>
                      <option value="Executive">Executive</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="hrms-modal-footer">
                <button type="button" className="hrms-btn-secondary" onClick={() => setIsDesigModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="hrms-btn-primary" disabled={submitting}>
                  {submitting ? 'Creating...' : 'Save Designation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
