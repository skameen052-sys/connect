import React from 'react';
import TeamsChatWorkspace from '../../components/chat/TeamsChatWorkspace';

/**
 * EmployeeChat - Microsoft Teams Real-Time Collaboration Workspace for Employees
 * Allows staff members to collaborate in their team channels and message colleagues/admin directly.
 */
export default function EmployeeChat() {
  return (
    <div className="employee-chat-page animate-fade-in" style={{ padding: '0 4px 10px 4px', height: 'calc(100vh - 85px)', display: 'flex', flexDirection: 'column' }}>
      <TeamsChatWorkspace />
    </div>
  );
}
