import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, MessageSquare } from 'lucide-react';
import BrandLogo from '../common/BrandLogo';
import { chatService } from '../../services/chatService';

/**
 * EmployeeNavbar - Top application header for the Employee Portal
 * Matches the reference design in Screenshot 4.
 */
export default function EmployeeNavbar({ onOpenDrawer }) {
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

  const handleLogout = () => {
    localStorage.removeItem('arshith_role');
    localStorage.removeItem('arshith_user');
    localStorage.removeItem('arshith_auth_token');
    navigate('/login', { replace: true });
  };

  const storedUser = (() => {
    try {
      return JSON.parse(localStorage.getItem('arshith_user')) || null;
    } catch {
      return null;
    }
  })();
  const employeeName = storedUser?.name || 'Employee';
  const employeeId = storedUser?.employeeId || 'AFI-001';

  return (
    <header className="employee-top-navbar portal-navbar">
      {/* Left: Stepped Mint Hamburger Toggle Button matching Screenshot 4 */}
      <div className="portal-nav-left">
        <button
          type="button"
          className="employee-hamburger-btn"
          onClick={onOpenDrawer}
          aria-label="Open employee navigation menu"
          title="Open Menu"
        >
          <span className="employee-hamburger-line line-1" />
          <span className="employee-hamburger-line line-2" />
          <span className="employee-hamburger-line line-3" />
        </button>
      </div>

      {/* Center: ARSHITH Connect Logo matching Screenshot 4 */}
      <div
        className="employee-navbar-logo"
        style={{ cursor: 'pointer' }}
        onClick={() => navigate('/employee/dashboard')}
        title="Arshith Connect Employee Portal"
      >
        <BrandLogo size="medium" />
      </div>

      {/* Right: User Avatar & Logout Button matching Screenshot 4 */}
      <div className="portal-nav-right">
        <button
          type="button"
          onClick={() => navigate('/employee/chat')}
          style={{
            position: 'relative',
            padding: '6px 11px',
            borderRadius: '8px',
            backgroundColor: '#eef2ff',
            color: '#4f46e5',
            fontSize: '0.78rem',
            fontWeight: '700',
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            border: '1px solid #c7d2fe',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          title="Open Teams Chat"
        >
          <MessageSquare size={15} />
          <span>Teams</span>
          {unreadCount > 0 && (
            <span
              style={{
                position: 'absolute',
                top: '-5px',
                right: '-5px',
                backgroundColor: '#ef4444',
                color: '#ffffff',
                fontSize: '0.62rem',
                fontWeight: '800',
                padding: '1px 5px',
                borderRadius: '10px',
                border: '2px solid #ffffff',
              }}
            >
              {unreadCount}
            </span>
          )}
        </button>

        <div
          className="user-profile-badge"
          onClick={() => navigate('/employee/profile')}
          style={{ cursor: 'pointer' }}
          title={`${employeeName} (${employeeId}) - View Profile`}
        >
          <div className="user-avatar" style={{ backgroundColor: '#0b3d2b' }}>
            {employeeName.charAt(0).toUpperCase()}
          </div>
        </div>

        <button
          type="button"
          onClick={handleLogout}
          className="employee-logout-btn"
          title="Sign out of employee session"
          aria-label="Log Out"
        >
          <LogOut size={16} />
        </button>
      </div>
    </header>
  );
}
