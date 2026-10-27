import React from 'react';
import TeamsChatWorkspace from '../../components/chat/TeamsChatWorkspace';

/**
 * AdminChat - Microsoft Teams Real-Time Collaboration Workspace for Administrators
 * Allows administrators to chat with any individual employee or post/manage all team channels.
 */
export default function AdminChat() {
  return (
    <div className="admin-chat-page animate-fade-in" style={{ padding: '0 8px 16px 8px' }}>
      <div style={{ marginBottom: '14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '1.45rem', fontWeight: 800, color: '#0f172a', margin: '0 0 4px 0' }}>
            Microsoft Teams Chat
          </h1>
          <p style={{ fontSize: '0.85rem', color: '#64748b', margin: 0 }}>
            Real-time direct messaging with employees and enterprise team channels.
          </p>
        </div>
      </div>

      <TeamsChatWorkspace />
    </div>
  );
}
