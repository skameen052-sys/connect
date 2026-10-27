import React, { useState, useEffect } from 'react';
import { 
  Settings, Building, DollarSign, Clock, ShieldCheck, 
  Save, RefreshCw, X 
} from 'lucide-react';
import settingsService from '../../services/settingsService';

export default function AdminSettings() {
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const [formState, setFormState] = useState({
    company_name: 'Arshith Connect',
    company_email: 'payroll@arshith.com',
    company_phone: '+91 98765 43210',
    company_address: 'Tech Center, HITEC City, Hyderabad, India',
    daily_rate_denominator: 30,
    attendance_cutoff_day: 25,
    pf_wage_ceiling: 15000,
    esi_wage_ceiling: 21000,
    overtime_multiplier: 1.5,
    currency: 'INR',
    currency_symbol: '₹',
  });

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const data = await settingsService.getSettings();
      setFormState(data);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch company settings.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await settingsService.updateSettings({
        ...formState,
        daily_rate_denominator: parseInt(formState.daily_rate_denominator, 10),
        attendance_cutoff_day: parseInt(formState.attendance_cutoff_day, 10),
        pf_wage_ceiling: parseFloat(formState.pf_wage_ceiling),
        esi_wage_ceiling: parseFloat(formState.esi_wage_ceiling),
        overtime_multiplier: parseFloat(formState.overtime_multiplier),
      });
      setSuccessMsg('Settings updated successfully.');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update settings.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="hrms-page-container">
      {/* Header */}
      <div className="hrms-page-header">
        <div className="hrms-page-title-group">
          <h1><Settings size={28} className="text-forest" /> Company & Payroll Configuration</h1>
          <p className="hrms-page-subtitle">
            Configure enterprise profile, attendance cutoff thresholds, statutory ceilings, and compensation policies.
          </p>
        </div>

        <div className="hrms-actions-group">
          <button type="button" className="hrms-btn-secondary" onClick={fetchSettings} disabled={loading}>
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

      <form onSubmit={handleSubmit}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.5rem' }}>
          {/* Company Profile Card */}
          <div className="hrms-card" style={{ marginBottom: 0 }}>
            <div className="hrms-card-header">
              <h2 className="hrms-card-title"><Building size={20} /> Corporate Identity</h2>
            </div>
            <div className="hrms-card-body">
              <div className="hrms-form-group">
                <label>Company Legal Name *</label>
                <input
                  type="text"
                  className="hrms-input"
                  value={formState.company_name}
                  onChange={(e) => setFormState({ ...formState, company_name: e.target.value })}
                  required
                />
              </div>

              <div className="hrms-form-group">
                <label>Corporate Payroll Email</label>
                <input
                  type="email"
                  className="hrms-input"
                  value={formState.company_email}
                  onChange={(e) => setFormState({ ...formState, company_email: e.target.value })}
                  required
                />
              </div>

              <div className="hrms-form-group">
                <label>Contact Phone</label>
                <input
                  type="text"
                  className="hrms-input"
                  value={formState.company_phone}
                  onChange={(e) => setFormState({ ...formState, company_phone: e.target.value })}
                />
              </div>

              <div className="hrms-form-group">
                <label>Registered Headquarters Address</label>
                <textarea
                  rows="3"
                  className="hrms-input"
                  value={formState.company_address}
                  onChange={(e) => setFormState({ ...formState, company_address: e.target.value })}
                />
              </div>
            </div>
          </div>

          {/* Payroll Rules Card */}
          <div className="hrms-card" style={{ marginBottom: 0 }}>
            <div className="hrms-card-header">
              <h2 className="hrms-card-title"><DollarSign size={20} /> Payroll Engine Rules & Cutoff</h2>
            </div>
            <div className="hrms-card-body">
              <div className="hrms-form-group">
                <label>Daily Salary Rate Denominator</label>
                <select
                  className="hrms-select"
                  style={{ width: '100%' }}
                  value={formState.daily_rate_denominator}
                  onChange={(e) => setFormState({ ...formState, daily_rate_denominator: e.target.value })}
                >
                  <option value="26">Working Days Basis (26 Days) • Recommended</option>
                  <option value="30">Standard 30 Days Basis</option>
                  <option value="31">Calendar Days Basis (31 Days)</option>
                </select>
                <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                  Standard company rule: 30 days minus 4 Sundays = 26 working days. Used to derive Daily Rate: Gross / Denominator for LOP deductions.
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1rem' }}>
                <div style={{ padding: '0.75rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#0f766e', textTransform: 'uppercase' }}>Weekly Offs</div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#1e293b', marginTop: '0.2rem' }}>4 Sundays (Paid)</div>
                  <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Included in payable days calculation</div>
                </div>

                <div style={{ padding: '0.75rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#0f766e', textTransform: 'uppercase' }}>Festival Holidays</div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#1e293b', marginTop: '0.2rem' }}>Fully Paid</div>
                  <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Sankranthi, Diwali, etc. counted as paid days</div>
                </div>
              </div>

              <div className="hrms-form-group">
                <label>Monthly Attendance Cutoff Day (1 - 31)</label>
                <input
                  type="number"
                  min="1"
                  max="31"
                  className="hrms-input"
                  value={formState.attendance_cutoff_day}
                  onChange={(e) => setFormState({ ...formState, attendance_cutoff_day: e.target.value })}
                  required
                />
              </div>

              <div className="hrms-form-group">
                <label>Statutory EPF Mandatory Wage Ceiling (₹)</label>
                <input
                  type="number"
                  className="hrms-input"
                  value={formState.pf_wage_ceiling}
                  onChange={(e) => setFormState({ ...formState, pf_wage_ceiling: e.target.value })}
                  required
                />
                <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                  Statutory 12% EPF calculated on Basic wage capped at this ceiling (standard ₹15,000).
                </span>
              </div>

              <div className="hrms-form-group">
                <label>Statutory ESIC Wage Coverage Ceiling (₹)</label>
                <input
                  type="number"
                  className="hrms-input"
                  value={formState.esi_wage_ceiling}
                  onChange={(e) => setFormState({ ...formState, esi_wage_ceiling: e.target.value })}
                  required
                />
              </div>

              <div className="hrms-form-group">
                <label>Overtime Multiplier (Standard: 1.5x)</label>
                <input
                  type="number"
                  step="0.1"
                  min="1.0"
                  max="3.0"
                  className="hrms-input"
                  value={formState.overtime_multiplier}
                  onChange={(e) => setFormState({ ...formState, overtime_multiplier: e.target.value })}
                  required
                />
              </div>
            </div>
          </div>
        </div>

        <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
          <button type="submit" className="hrms-btn-primary" disabled={submitting}>
            <Save size={16} /> {submitting ? 'Saving Configuration...' : 'Save Company Settings'}
          </button>
        </div>
      </form>
    </div>
  );
}
