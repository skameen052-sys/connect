import React from 'react';
import TeamsChatWorkspace from '../../components/chat/TeamsChatWorkspace';

/**
 * AdminChat - Microsoft Teams Real-Time Collaboration Workspace for Administrators
 * Allows administrators to chat with any individual employee or post/manage all team channels.
 */
export default function AdminChat() {
  return (
    <div className="admin-chat-page animate-fade-in" style={{ padding: '0 4px 10px 4px', height: 'calc(100vh - 85px)', display: 'flex', flexDirection: 'column' }}>
      <TeamsChatWorkspace />
    </div>
  );
}
