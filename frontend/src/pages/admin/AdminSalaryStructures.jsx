import React, { useState, useEffect } from 'react';
import { 
  CreditCard, Search, Edit3, History, Plus, RefreshCw, 
  DollarSign, CheckCircle2, Shield, X, AlertCircle 
} from 'lucide-react';
import payrollService from '../../services/payrollService';

export default function AdminSalaryStructures() {
  const [structures, setStructures] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDept, setSelectedDept] = useState('ALL');
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Edit / Add Modal state
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingStructure, setEditingStructure] = useState(null);
  const [historyModalOpen, setHistoryModalOpen] = useState(false);
  const [historyData, setHistoryData] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  // Form state
  const [formState, setFormState] = useState({
    employee_id: '',
    basic_salary: 20000,
    hra: 8000,
    other_allowances: 4000,
    special_allowance: 0,
    pf_applicable: true,
    pf_wage_base: 18000,
    esi_applicable: false,
    professional_tax: 200,
    tds_monthly: 0,
    effective_date: new Date().toISOString().split('T')[0],
    reason: 'Annual Increment / Compensation Revision',
  });

  const fetchStructures = async () => {
    setLoading(true);
    try {
      const data = await payrollService.getSalaryStructures();
      setStructures(data);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch salary structures.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStructures();
  }, []);

  const handleOpenEdit = (s) => {
    setEditingStructure(s);
    setFormState({
      employee_id: s.employee_id,
      basic_salary: s.basic_salary || 20000,
      hra: s.hra || 8000,
      other_allowances: s.other_allowances || 4000,
      special_allowance: s.special_allowance || 0,
      pf_applicable: s.pf_applicable !== undefined ? s.pf_applicable : true,
      pf_wage_base: s.pf_wage_base || 18000,
      esi_applicable: s.esi_applicable || false,
      professional_tax: s.professional_tax !== undefined ? s.professional_tax : 200,
      tds_monthly: s.tds_monthly || 0,
      effective_date: s.effective_date || new Date().toISOString().split('T')[0],
      reason: 'Compensation Adjustment',
    });
    setIsEditModalOpen(true);
  };

  const handleViewHistory = async (empId) => {
    try {
      const history = await payrollService.getSalaryHistory(empId);
      setHistoryData(history);
      setHistoryModalOpen(true);
    } catch (err) {
      setError('Could not load revision history.');
    }
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await payrollService.saveSalaryStructure({
        employee_id: formState.employee_id,
        basic_salary: parseFloat(formState.basic_salary) || 0,
        hra: parseFloat(formState.hra) || 0,
        other_allowances: parseFloat(formState.other_allowances) || 0,
        special_allowance: parseFloat(formState.special_allowance) || 0,
        pf_applicable: Boolean(formState.pf_applicable),
        pf_wage_base: parseFloat(formState.pf_wage_base) || 15000,
        esi_applicable: Boolean(formState.esi_applicable),
        professional_tax: parseFloat(formState.professional_tax) || 0,
        tds_monthly: parseFloat(formState.tds_monthly) || 0,
        effective_date: formState.effective_date,
        reason: formState.reason,
      });
      setSuccessMsg(`Salary structure updated for ${formState.employee_id}`);
      setIsEditModalOpen(false);
      fetchStructures();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save salary structure.');
    } finally {
      setSubmitting(false);
    }
  };

  // Real-time calculation of preview gross
  const computedGross =
    (parseFloat(formState.basic_salary) || 0) +
    (parseFloat(formState.hra) || 0) +
    (parseFloat(formState.other_allowances) || 0) +
    (parseFloat(formState.special_allowance) || 0);

  const filteredStructures = structures.filter((s) => {
    const matchesSearch =
      (s.employee_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (s.employee_id || '').toLowerCase().includes(searchTerm.toLowerCase());
    const matchesDept = selectedDept === 'ALL' || s.department === selectedDept;
    return matchesSearch && matchesDept;
  });

  const avgGross = structures.length
    ? structures.reduce((acc, s) => acc + (parseFloat(s.gross_salary) || 0), 0) / structures.length
    : 0;

  return (
    <div className="hrms-page-container">
      {/* Header */}
      <div className="hrms-page-header">
        <div className="hrms-page-title-group">
          <h1><CreditCard size={28} className="text-forest" /> Salary Structure Governance</h1>
          <p className="hrms-page-subtitle">
            Define basic pay, allowances, statutory EPF/ESIC eligibility, and income tax withholdings per employee.
          </p>
        </div>

        <div className="hrms-actions-group">
          <button type="button" className="hrms-btn-secondary" onClick={fetchStructures} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {/* Messages */}
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

      {/* Metric Cards */}
      <div className="hrms-metrics-grid">
        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Configured Employees</span>
            <div className="hrms-metric-icon-wrap"><CreditCard size={18} /></div>
          </div>
          <div className="hrms-metric-value">{structures.length}</div>
          <div className="hrms-metric-subtext">Active salary structures</div>
        </div>

        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">Average Monthly Gross</span>
            <div className="hrms-metric-icon-wrap"><DollarSign size={18} /></div>
          </div>
          <div className="hrms-metric-value">₹{avgGross.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
          <div className="hrms-metric-subtext">Per employee baseline</div>
        </div>

        <div className="hrms-metric-card">
          <div className="hrms-metric-header">
            <span className="hrms-metric-label">EPF Covered Ratio</span>
            <div className="hrms-metric-icon-wrap"><Shield size={18} /></div>
          </div>
          <div className="hrms-metric-value">
            {structures.filter((s) => s.pf_applicable).length} / {structures.length}
          </div>
          <div className="hrms-metric-subtext">Statutory EPF participation</div>
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
                placeholder="Search by employee name or ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            <select
              className="hrms-select"
              value={selectedDept}
              onChange={(e) => setSelectedDept(e.target.value)}
            >
              <option value="ALL">All Departments</option>
              <option value="Engineering">Engineering</option>
              <option value="Human Resources">Human Resources</option>
              <option value="Finance & Payroll">Finance & Payroll</option>
              <option value="Operations">Operations</option>
            </select>
          </div>
        </div>
      </div>

      {/* Structures Table */}
      <div className="hrms-card">
        <div className="hrms-table-container">
          <table className="hrms-table">
            <thead>
              <tr>
                <th>Employee</th>
                <th>Basic Pay</th>
                <th>HRA</th>
                <th>Allowances</th>
                <th>Gross Salary</th>
                <th>PF Base</th>
                <th>PT Tax</th>
                <th>Effective Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredStructures.length === 0 ? (
                <tr>
                  <td colSpan="9">
                    <div className="hrms-empty-state">
                      <CreditCard className="hrms-empty-icon" />
                      <p>No matching employee salary structures found.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredStructures.map((s) => (
                  <tr key={s.id || s.employee_id}>
                    <td>
                      <strong>{s.employee_name}</strong>
                      <div className="hrms-metric-subtext">{s.employee_id} • {s.department}</div>
                    </td>
                    <td>₹{parseFloat(s.basic_salary || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                    <td>₹{parseFloat(s.hra || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                    <td>₹{parseFloat(s.other_allowances || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                    <td>
                      <strong style={{ color: '#134e4a', fontSize: '0.95rem' }}>
                        ₹{parseFloat(s.gross_salary || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </strong>
                    </td>
                    <td>
                      {s.pf_applicable ? (
                        <span style={{ fontSize: '0.85rem' }}>₹{parseFloat(s.pf_wage_base || 15000).toLocaleString('en-IN')} (12%)</span>
                      ) : (
                        <span style={{ color: '#94a3b8' }}>Exempt</span>
                      )}
                    </td>
                    <td>₹{parseFloat(s.professional_tax || 0).toLocaleString('en-IN')}</td>
                    <td>{s.effective_date}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          type="button"
                          className="hrms-btn-primary"
                          style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
                          onClick={() => handleOpenEdit(s)}
                        >
                          <Edit3 size={13} /> Edit
                        </button>
                        <button
                          type="button"
                          className="hrms-btn-secondary"
                          style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
                          onClick={() => handleViewHistory(s.employee_id)}
                          title="View revision history"
                        >
                          <History size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit Salary Structure Modal */}
      {isEditModalOpen && (
        <div className="hrms-modal-overlay" onClick={() => setIsEditModalOpen(false)}>
          <div className="hrms-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="hrms-modal-header">
              <h3 className="hrms-modal-title">Configure Salary Structure ({formState.employee_id})</h3>
              <button type="button" className="hrms-modal-close" onClick={() => setIsEditModalOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleFormSubmit}>
              <div className="hrms-modal-body">
                {/* Live Gross Preview Card */}
                <div style={{ backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', padding: '0.75rem 1rem', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '0.875rem', fontWeight: '600', color: '#166534' }}>Computed Monthly Gross:</span>
                  <span style={{ fontSize: '1.25rem', fontWeight: '700', color: '#134e4a' }}>
                    ₹{computedGross.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>

                <div className="hrms-form-row">
                  <div className="hrms-form-group">
                    <label>Basic Salary (₹)</label>
                    <input
                      type="number"
                      className="hrms-input"
                      value={formState.basic_salary}
                      onChange={(e) => setFormState({ ...formState, basic_salary: e.target.value })}
                      required
                    />
                  </div>

                  <div className="hrms-form-group">
                    <label>House Rent Allowance - HRA (₹)</label>
                    <input
                      type="number"
                      className="hrms-input"
                      value={formState.hra}
                      onChange={(e) => setFormState({ ...formState, hra: e.target.value })}
                    />
                  </div>
                </div>

                <div className="hrms-form-row">
                  <div className="hrms-form-group">
                    <label>Other / Special Allowances (₹)</label>
                    <input
                      type="number"
                      className="hrms-input"
                      value={formState.other_allowances}
                      onChange={(e) => setFormState({ ...formState, other_allowances: e.target.value })}
                    />
                  </div>

                  <div className="hrms-form-group">
                    <label>Professional Tax - PT (₹)</label>
                    <input
                      type="number"
                      className="hrms-input"
                      value={formState.professional_tax}
                      onChange={(e) => setFormState({ ...formState, professional_tax: e.target.value })}
                    />
                  </div>
                </div>

                <div className="hrms-form-row">
                  <div className="hrms-form-group">
                    <label>PF Wage Base (₹)</label>
                    <input
                      type="number"
                      className="hrms-input"
                      value={formState.pf_wage_base}
                      onChange={(e) => setFormState({ ...formState, pf_wage_base: e.target.value })}
                    />
                  </div>

                  <div className="hrms-form-group">
                    <label>Monthly TDS Tax Withholding (₹)</label>
                    <input
                      type="number"
                      className="hrms-input"
                      value={formState.tds_monthly}
                      onChange={(e) => setFormState({ ...formState, tds_monthly: e.target.value })}
                    />
                  </div>
                </div>

                <div className="hrms-form-row" style={{ marginTop: '0.5rem', marginBottom: '0.75rem' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.85rem' }}>
                    <input
                      type="checkbox"
                      checked={formState.pf_applicable}
                      onChange={(e) => setFormState({ ...formState, pf_applicable: e.target.checked })}
                    />
                    Employee Provident Fund (EPF 12%) Applicable
                  </label>

                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.85rem' }}>
                    <input
                      type="checkbox"
                      checked={formState.esi_applicable}
                      onChange={(e) => setFormState({ ...formState, esi_applicable: e.target.checked })}
                    />
                    ESIC Applicable (Gross ≤ ₹21,000)
                  </label>
                </div>

                <div className="hrms-form-group">
                  <label>Effective Date</label>
                  <input
                    type="date"
                    className="hrms-input"
                    value={formState.effective_date}
                    onChange={(e) => setFormState({ ...formState, effective_date: e.target.value })}
                  />
                </div>

                <div className="hrms-form-group">
                  <label>Revision Reason / Justification</label>
                  <input
                    type="text"
                    className="hrms-input"
                    value={formState.reason}
                    onChange={(e) => setFormState({ ...formState, reason: e.target.value })}
                  />
                </div>
              </div>

              <div className="hrms-modal-footer">
                <button type="button" className="hrms-btn-secondary" onClick={() => setIsEditModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="hrms-btn-primary" disabled={submitting}>
                  {submitting ? 'Saving...' : 'Save Structure'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Revision History Modal */}
      {historyModalOpen && (
        <div className="hrms-modal-overlay" onClick={() => setHistoryModalOpen(false)}>
          <div className="hrms-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="hrms-modal-header">
              <h3 className="hrms-modal-title">Salary Revision Audit History</h3>
              <button type="button" className="hrms-modal-close" onClick={() => setHistoryModalOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <div className="hrms-modal-body">
              {historyData.length === 0 ? (
                <p style={{ textAlign: 'center', color: '#64748b', padding: '1.5rem' }}>No past revisions recorded.</p>
              ) : (
                <ul style={{ listStyle: 'none', padding: 0 }}>
                  {historyData.map((h, i) => (
                    <li key={i} style={{ borderBottom: '1px solid #e2e8f0', padding: '0.75rem 0' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: '600' }}>
                        <span>New Gross: ₹{parseFloat(h.new_gross || 0).toLocaleString('en-IN')}</span>
                        <span style={{ fontSize: '0.75rem', color: '#64748b' }}>{h.revised_at?.split('T')[0]}</span>
                      </div>
                      <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                        Previous: ₹{parseFloat(h.previous_gross || 0).toLocaleString('en-IN')} • By: {h.revised_by}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: '#334155', marginTop: '0.25rem' }}>
                        Reason: {h.reason}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="hrms-modal-footer">
              <button type="button" className="hrms-btn-secondary" onClick={() => setHistoryModalOpen(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
