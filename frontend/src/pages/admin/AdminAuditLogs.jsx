import React, { useState, useEffect } from 'react';
import { 
  Shield, Search, RefreshCw, Clock, Filter, Eye, UserCheck 
} from 'lucide-react';
import auditService from '../../services/auditService';

export default function AdminAuditLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedEntity, setSelectedEntity] = useState('ALL');
  const [error, setError] = useState(null);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const data = await auditService.getLogs({ limit: 150 });
      setLogs(data);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch audit trail records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const filteredLogs = logs.filter((l) => {
    const textMatch =
      (l.action || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (l.actor_uid || l.user_email || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (l.target_record || '').toLowerCase().includes(searchTerm.toLowerCase());
    const entityMatch = selectedEntity === 'ALL' || (l.entity_type || '').toLowerCase() === selectedEntity.toLowerCase();
    return textMatch && entityMatch;
  });

  return (
    <div className="hrms-page-container">
      {/* Header */}
      <div className="hrms-page-header">
        <div className="hrms-page-title-group">
          <h1><Shield size={28} className="text-forest" /> Security & Compliance Audit Trail</h1>
          <p className="hrms-page-subtitle">
            Immutable log of administrative operations, salary changes, attendance overrides, and approval authorizations.
          </p>
        </div>

        <div className="hrms-actions-group">
          <button type="button" className="hrms-btn-secondary" onClick={fetchLogs} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="hrms-card" style={{ borderColor: '#fca5a5', backgroundColor: '#fef2f2', padding: '1rem', marginBottom: '1rem' }}>
          <span style={{ color: '#991b1b' }}>{error}</span>
        </div>
      )}

      {/* Filter Bar */}
      <div className="hrms-card">
        <div className="hrms-card-body" style={{ padding: '1rem 1.5rem' }}>
          <div className="hrms-filter-bar" style={{ margin: 0 }}>
            <div className="hrms-search-input-wrap">
              <Search size={16} />
              <input
                type="text"
                className="hrms-input"
                placeholder="Search audit trail by actor, action or target..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            <select
              className="hrms-select"
              value={selectedEntity}
              onChange={(e) => setSelectedEntity(e.target.value)}
            >
              <option value="ALL">All Categories</option>
              <option value="payroll">Payroll</option>
              <option value="salary">Salary Structures</option>
              <option value="attendance">Attendance</option>
              <option value="leaves">Leaves</option>
              <option value="users">User Authentication</option>
            </select>
          </div>
        </div>
      </div>

      {/* Logs Table */}
      <div className="hrms-card">
        <div className="hrms-table-container">
          <table className="hrms-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Actor / User</th>
                <th>Action</th>
                <th>Target Record</th>
                <th>Details / Metadata</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan="5">
                    <div className="hrms-empty-state">
                      <Shield className="hrms-empty-icon" />
                      <p>No audit trail records found.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log, idx) => (
                  <tr key={log.id || idx}>
                    <td style={{ whiteSpace: 'nowrap', fontSize: '0.8rem', color: '#64748b' }}>
                      <Clock size={12} style={{ display: 'inline', marginRight: '4px' }} />
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : log.created_at || 'Recent'}
                    </td>
                    <td>
                      <strong>{log.actor_uid || log.user_email || 'Administrator'}</strong>
                    </td>
                    <td>
                      <span className="hrms-badge hrms-badge-info">{log.action || 'MODIFY'}</span>
                    </td>
                    <td>{log.target_record || log.entity_id || 'System'}</td>
                    <td>
                      <code style={{ fontSize: '0.75rem', backgroundColor: '#f1f5f9', padding: '0.2rem 0.4rem', borderRadius: '4px' }}>
                        {JSON.stringify(log.metadata || log.old_values || {}).substring(0, 80)}
                      </code>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
