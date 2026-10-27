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

  const handleLogout = () => {
    localStorage.removeItem('arshith_role');
    localStorage.removeItem('arshith_user');
    localStorage.removeItem('arshith_auth_token');
    navigate('/login', { replace: true });
  };

  useEffect(() => {
    let isMounted = true;
    const fetchUnread = async () => {
      try {
        const count = await chatService.getUnreadCount();
        if (isMounted) setUnreadCount(count);
      } catch {}
    };
    fetchUnread();
    const interval = setInterval(fetchUnread, 8000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

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

      {/* Right: Chat, User Avatar & Logout Button matching Screenshot 4 */}
      <div className="portal-nav-right">
        {/* Teams Chat Icon with Unread Badge */}
        <button
          type="button"
          onClick={() => navigate('/employee/chat')}
          style={{
            position: 'relative',
            background: 'transparent',
            border: 'none',
            padding: '7px 9px',
            cursor: 'pointer',
            color: '#1e293b',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: '8px',
            transition: 'background-color 0.15s ease',
          }}
          className="navbar-chat-trigger"
          title="Open Teams Chat & Channels"
        >
          <MessageSquare size={19} />
          {unreadCount > 0 && (
            <span
              style={{
                position: 'absolute',
                top: '0px',
                right: '0px',
                backgroundColor: '#ef4444',
                color: '#ffffff',
                fontSize: '0.65rem',
                fontWeight: 700,
                borderRadius: '10px',
                padding: '1px 5px',
                lineHeight: 1.2,
                boxShadow: '0 0 0 2px #ffffff',
              }}
            >
              {unreadCount > 99 ? '99+' : unreadCount}
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
