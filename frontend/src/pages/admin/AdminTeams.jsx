import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Trash2, CheckCircle2, AlertCircle, MessageSquare } from 'lucide-react';
import PageHeader from '../../components/common/PageHeader';
import { employeeService } from '../../services/employeeService';
import { teamService } from '../../services/teamService';

export default function AdminTeams() {
  const navigate = useNavigate();
  const [teamName, setTeamName] = useState('');
  const [selectedEmployees, setSelectedEmployees] = useState([]);
  const [availableEmployees, setAvailableEmployees] = useState([]);
  const [teams, setTeams] = useState([]);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Load available registered employees and saved teams from PostgreSQL
  const loadData = async () => {
    try {
      setIsLoading(true);
      const [empData, teamData] = await Promise.all([
        employeeService.getEmployees(),
        teamService.getTeams(),
      ]);
      const cleanEmps = (Array.isArray(empData) ? empData : []).filter(
        (e) => e && e.name && e.name.trim().toLowerCase() !== 'unnamed employee'
      );
      setAvailableEmployees(cleanEmps);
      setTeams(Array.isArray(teamData) ? teamData : []);
    } catch (err) {
      setErrorMessage(err.message || 'Failed to fetch teams or employees');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleToggleEmployee = (empName) => {
    setSelectedEmployees((prev) =>
      prev.includes(empName) ? prev.filter((name) => name !== empName) : [...prev, empName]
    );
  };

  const handleCreateTeam = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');

    const trimmedName = teamName.trim();

    if (!trimmedName) {
      setErrorMessage('Team name is required.');
      return;
    }

    if (selectedEmployees.length === 0) {
      setErrorMessage('Please select at least one employee for the team.');
      return;
    }

    const duplicate = teams.some(
      (t) => (t.name || t.teamName || '').toLowerCase() === trimmedName.toLowerCase()
    );
    if (duplicate) {
      setErrorMessage(`A team named "${trimmedName}" already exists.`);
      return;
    }

    try {
      setIsSubmitting(true);
      await teamService.createTeam({
        teamName: trimmedName,
        department: 'Operations',
        members: selectedEmployees,
      });

      setTeamName('');
      setSelectedEmployees([]);
      setSuccessMessage(`Team "${trimmedName}" successfully created in database.`);
      setTimeout(() => setSuccessMessage(''), 3500);
      loadData();
    } catch (err) {
      setErrorMessage(err.message || 'Failed to create team');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteTeam = async (id, name) => {
    if (window.confirm(`Are you sure you want to delete the team "${name}"?`)) {
      try {
        await teamService.deleteTeam(id);
        setSuccessMessage(`Team "${name}" deleted.`);
        setTimeout(() => setSuccessMessage(''), 3000);
        loadData();
      } catch (err) {
        setErrorMessage(err.message || 'Failed to delete team');
      }
    }
  };

  return (
    <div className="teams-management-view animate-fade-in" style={{ maxWidth: '680px', margin: '0 auto' }}>
      {/* Page Heading matching Screenshot 3 */}
      <div style={{ marginBottom: '20px' }}>
        <h1 style={{ fontSize: '1.45rem', fontWeight: '700', color: '#0b3d2b', margin: '0 0 4px 0' }}>
          Team Management
        </h1>
        <p style={{ fontSize: '0.875rem', color: '#64748b', margin: 0 }}>
          Create teams by selecting registered employees.
        </p>
      </div>


      {/* Feedback Banners */}
      {successMessage && (
        <div
          style={{
            backgroundColor: '#ecfdf5',
            border: '1px solid #a7f3d0',
            color: '#065f46',
            padding: '10px 14px',
            borderRadius: '10px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '0.85rem',
            fontWeight: '600',
          }}
        >
          <CheckCircle2 size={16} />
          <span>{successMessage}</span>
        </div>
      )}

      {errorMessage && (
        <div
          style={{
            backgroundColor: '#fef2f2',
            border: '1px solid #fecaca',
            color: '#b91c1c',
            padding: '10px 14px',
            borderRadius: '10px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '0.85rem',
            fontWeight: '600',
          }}
        >
          <AlertCircle size={16} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Create New Team Card matching Screenshot 3 */}
      <div
        style={{
          backgroundColor: '#ffffff',
          borderRadius: '16px',
          padding: '24px 22px',
          border: '1px solid #e2e8f0',
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.02)',
          marginBottom: '28px',
        }}
      >
        <h2 style={{ fontSize: '1.15rem', fontWeight: '700', color: '#0f172a', margin: '0 0 18px 0' }}>
          Create New Team
        </h2>

        <form onSubmit={handleCreateTeam} noValidate>
          {/* Team Name Input */}
          <div style={{ marginBottom: '22px' }}>
            <input
              type="text"
              placeholder="Enter team name"
              value={teamName}
              onChange={(e) => setTeamName(e.target.value)}
              disabled={isSubmitting}
              style={{
                width: '100%',
                padding: '10px 0',
                border: 'none',
                borderBottom: '1.5px solid #cbd5e1',
                fontSize: '0.95rem',
                color: '#1e293b',
                outline: 'none',
                backgroundColor: 'transparent',
                transition: 'border-color 0.15s ease',
                boxSizing: 'border-box',
              }}
              onFocus={(e) => (e.target.style.borderBottomColor = '#6941c6')}
              onBlur={(e) => (e.target.style.borderBottomColor = '#cbd5e1')}
            />
          </div>

          {/* Select Employees Section matching Screenshot 3 */}
          <div style={{ marginBottom: '24px' }}>
            <label
              style={{
                display: 'block',
                fontSize: '0.95rem',
                fontWeight: '700',
                color: '#0f172a',
                marginBottom: '12px',
              }}
            >
              Select Employees
            </label>

            {availableEmployees.length === 0 ? (
              <div
                style={{
                  padding: '16px',
                  backgroundColor: '#f8fafc',
                  borderRadius: '10px',
                  color: '#64748b',
                  fontSize: '0.85rem',
                  border: '1px dashed #cbd5e1',
                }}
              >
                No registered employees found. Please register employees first to create a team.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {availableEmployees.map((emp) => {
                  const name = emp.name || emp.fullName || '';
                  const isChecked = selectedEmployees.includes(name);

                  return (
                    <label
                      key={emp.id || emp.email}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        cursor: 'pointer',
                        padding: '6px 8px',
                        borderRadius: '8px',
                        transition: 'background-color 0.12s ease',
                        userSelect: 'none',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#f8fafc')}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => handleToggleEmployee(name)}
                        disabled={isSubmitting}
                        style={{
                          width: '18px',
                          height: '18px',
                          accentColor: '#6941c6',
                          cursor: 'pointer',
                        }}
                      />
                      <span style={{ fontSize: '0.925rem', color: '#1e293b', fontWeight: isChecked ? '600' : '400' }}>
                        {name}
                      </span>
                      {emp.id && (
                        <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>({emp.id})</span>
                      )}
                    </label>
                  );
                })}
              </div>
            )}
          </div>

          {/* Submit Button matching Screenshot 3 */}
          <button
            type="submit"
            disabled={isSubmitting}
            style={{
              width: '100%',
              padding: '12px',
              backgroundColor: '#6941c6',
              color: '#ffffff',
              fontSize: '0.85rem',
              fontWeight: '700',
              letterSpacing: '0.5px',
              textTransform: 'uppercase',
              borderRadius: '8px',
              border: 'none',
              cursor: isSubmitting ? 'not-allowed' : 'pointer',
              opacity: isSubmitting ? 0.7 : 1,
              transition: 'background-color 0.15s ease',
            }}
          >
            {isSubmitting ? 'CREATING TEAM...' : 'CREATE TEAM'}
          </button>
        </form>
      </div>

      {/* Existing Teams Section matching Screenshot 3 */}
      <section>
        <h2 style={{ fontSize: '1.25rem', fontWeight: '700', color: '#0b3d2b', margin: '0 0 12px 0' }}>
          Existing Teams
        </h2>

        {teams.length === 0 ? (
          <div style={{ color: '#64748b', fontSize: '0.9rem', padding: '8px 0' }}>
            No teams created yet.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {teams.map((t) => (
              <div
                key={t.id}
                style={{
                  backgroundColor: '#ffffff',
                  borderRadius: '14px',
                  padding: '16px 18px',
                  border: '1px solid #e2e8f0',
                  boxShadow: '0 2px 6px rgba(0, 0, 0, 0.02)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  gap: '12px',
                }}
              >
                <div>
                  <h3 style={{ margin: '0 0 4px 0', fontSize: '1.05rem', fontWeight: '700', color: '#0b3d2b' }}>
                    {t.name}
                  </h3>
                  <div style={{ fontSize: '0.825rem', color: '#64748b' }}>
                    <strong>Members ({t.members?.length || 0}):</strong>{' '}
                    {t.members?.join(', ') || 'No members assigned'}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <button
                    type="button"
                    onClick={() => navigate(`/admin/chat?team=${encodeURIComponent(t.id)}`)}
                    style={{
                      backgroundColor: '#eef2ff',
                      border: '1px solid #c7d2fe',
                      color: '#4f46e5',
                      padding: '6px 12px',
                      borderRadius: '8px',
                      fontSize: '0.75rem',
                      fontWeight: '600',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                    title="Open Team Chat Channel"
                  >
                    <MessageSquare size={13} />
                    <span>Channel</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleDeleteTeam(t.id, t.name)}
                    style={{
                      backgroundColor: '#fff1f2',
                      border: '1px solid #fecdd3',
                      color: '#e11d48',
                      padding: '6px 10px',
                      borderRadius: '8px',
                      fontSize: '0.75rem',
                      fontWeight: '600',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                    title="Delete team"
                  >
                    <Trash2 size={13} />
                    <span>Delete</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
