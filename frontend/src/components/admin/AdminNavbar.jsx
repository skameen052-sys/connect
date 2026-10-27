import React, { useCallback, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, MessageSquare } from 'lucide-react';
import BrandLogo from '../common/BrandLogo';
import { chatService } from '../../services/chatService';

export default function AdminNavbar({ onToggleSidebar }) {
  const navigate = useNavigate();
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    let isMounted = true;
    chatService.getUnreadCount().then((count) => {
      if (isMounted) setUnreadCount(count);
    }).catch(() => {});

    const interval = setInterval(() => {
      chatService.getUnreadCount().then((count) => {
        if (isMounted) setUnreadCount(count);
      }).catch(() => {});
    }, 6000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleLogout = useCallback(() => {
    localStorage.removeItem('arshith_role');
    localStorage.removeItem('arshith_user');
    navigate('/admin/login');
  }, [navigate]);

  const storedUser = (() => {
    try {
      return JSON.parse(localStorage.getItem('arshith_user')) || null;
    } catch {
      return null;
    }
  })();
  const adminName = storedUser?.name || 'Administrator';
  const adminEmail = storedUser?.email || 'admin@arshith.com';

  return (
    <header className="portal-navbar">
      <div className="portal-nav-left">
        <button
          type="button"
          className="nav-hamburger-btn"
          onClick={onToggleSidebar}
          aria-label="Toggle admin navigation menu"
          title="Toggle Navigation Menu"
        >
          <span className="hamburger-line" />
          <span className="hamburger-line" />
          <span className="hamburger-line" />
        </button>
      </div>

      <div
        style={{ cursor: 'pointer' }}
        onClick={() => navigate('/admin/dashboard')}
        title="Arshith Connect Admin Portal"
      >
        <BrandLogo size="medium" />
      </div>

      <div className="portal-nav-right">
        <button
          type="button"
          onClick={() => navigate('/admin/chat')}
          style={{
            position: 'relative',
            padding: '7px 12px',
            borderRadius: '8px',
            backgroundColor: '#eef2ff',
            color: '#4f46e5',
            fontSize: '0.8rem',
            fontWeight: '700',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            border: '1px solid #c7d2fe',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          title="Open Teams Chat"
        >
          <MessageSquare size={16} />
          <span>Teams Chat</span>
          {unreadCount > 0 && (
            <span
              style={{
                position: 'absolute',
                top: '-6px',
                right: '-6px',
                backgroundColor: '#ef4444',
                color: '#ffffff',
                fontSize: '0.65rem',
                fontWeight: '800',
                padding: '1px 6px',
                borderRadius: '10px',
                border: '2px solid #ffffff',
              }}
            >
              {unreadCount}
            </span>
          )}
        </button>

        <div className="user-profile-badge" title={`${adminName} (${adminEmail})`}>
          <div className="user-avatar" style={{ backgroundColor: '#0b3d2b' }}>
            {adminName.charAt(0).toUpperCase()}
          </div>
          <div className="user-info-text">
            <div className="user-name">{adminName}</div>
            <div className="user-role">Admin</div>
          </div>
        </div>

        <button
          type="button"
          onClick={handleLogout}
          style={{
            padding: '7px 11px',
            borderRadius: '8px',
            backgroundColor: '#fee2e2',
            color: '#dc2626',
            fontSize: '0.8rem',
            fontWeight: '600',
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            border: 'none',
            cursor: 'pointer',
            transition: 'background-color 0.15s ease'
          }}
          title="Sign out of Administrator session"
        >
          <LogOut size={14} />
          <span className="navbar-logout-text">Logout</span>
        </button>
      </div>
    </header>
  );
}
