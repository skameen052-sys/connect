import React from 'react';
import TeamsChatWorkspace from '../../components/chat/TeamsChatWorkspace';

/**
 * EmployeeChat - Microsoft Teams Real-Time Collaboration Workspace for Employees
 * Allows staff members to collaborate in their team channels and message colleagues/admin directly.
 */
export default function EmployeeChat() {
  return (
    <div className="employee-chat-page animate-fade-in" style={{ padding: '0 8px 16px 8px' }}>
      <div style={{ marginBottom: '14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '1.45rem', fontWeight: 800, color: '#0f172a', margin: '0 0 4px 0' }}>
            Teams Chat
          </h1>
          <p style={{ fontSize: '0.85rem', color: '#64748b', margin: 0 }}>
            Connect and collaborate with your teammates and management in real time.
          </p>
        </div>
      </div>

      <TeamsChatWorkspace />
    </div>
  );
}
