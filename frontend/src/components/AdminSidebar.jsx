import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { X } from 'lucide-react';
import BrandLogo from './common/BrandLogo';

/**
 * AdminSidebar - Administrator Navigation Sidebar & Drawer
 *
 * Implements the exact 14 navigation items in strict requested order:
 * 1. Dashboard
 * 2. Attendance
 * 3. Leave Management
 * 4. Holiday Management
 * 5. Meeting Management
 * 6. Announcements
 * 7. Employees
 * 8. Employee List
 * 9. Teams
 * 10. Work Assignments
 * 11. Work Updates
 * 12. Registration Requests
 * 13. Office Timings
 * 14. Attendance Reports
 *
 * Requirements:
 * - Branded header with ARSHITH Connect logo, Administrator, Admin
 * - Pure white drawer/sidebar body with readable dark text (#1e293b)
 * - Internal scrolling ensuring all 14 items are visible and accessible
 * - Active route highlighting
 * - NO Sign Out / Logout menu item in the sidebar
 */
export default function AdminSidebar({ onClose }) {
  const navigate = useNavigate();
  const location = useLocation();

  const navSections = [
    {
      title: 'Core Operations',
      items: [
        { label: 'Dashboard', path: '/admin/dashboard', aliases: ['/admin', '/admin/dashboard'] },
        { label: 'Attendance', path: '/admin/attendance', aliases: ['/admin/attendance'] },
        { label: 'Leave Management', path: '/admin/leaves', aliases: ['/admin/leaves', '/admin/leave-management'] },
        { label: 'Holiday Management', path: '/admin/holidays', aliases: ['/admin/holidays', '/admin/holiday-management'] },
        { label: 'Meeting Management', path: '/admin/meetings', aliases: ['/admin/meetings', '/admin/meeting-management'] },
        { label: 'Announcements', path: '/admin/announcements', aliases: ['/admin/announcements'] },
        { label: 'Employees', path: '/admin/employees', aliases: ['/admin/employees'] },
        { label: 'Employee List', path: '/admin/employees/list', aliases: ['/admin/employees/list', '/admin/employee-list'] },
        { label: 'Teams', path: '/admin/teams', aliases: ['/admin/teams'] },
        { label: 'Work Assignments', path: '/admin/assignments', aliases: ['/admin/assignments', '/admin/work-assignments'] },
        { label: 'Work Updates', path: '/admin/updates', aliases: ['/admin/updates', '/admin/work-updates'] },
        { label: 'Registration Requests', path: '/admin/registration-requests', aliases: ['/admin/registration-requests'] },
        { label: 'Office Timings', path: '/admin/office-timings', aliases: ['/admin/office-timings'] },
        { label: 'Attendance Reports', path: '/admin/reports', aliases: ['/admin/reports', '/admin/attendance-reports'] },
      ],
    },
    {
      title: 'Payroll & Finance',
      items: [
        { label: 'Payroll Engine', path: '/admin/payroll', aliases: ['/admin/payroll'] },
        { label: 'Salary Structures', path: '/admin/salary-structures', aliases: ['/admin/salary-structures'] },
        { label: 'Payslip Generation', path: '/admin/payslips', aliases: ['/admin/payslips'] },
        { label: 'Salary Payments', path: '/admin/payments', aliases: ['/admin/payments'] },
        { label: 'Employee Loans', path: '/admin/loans', aliases: ['/admin/loans'] },
      ],
    },
    {
      title: 'HR Operations & Governance',
      items: [
        { label: 'Departments & Designations', path: '/admin/departments', aliases: ['/admin/departments'] },
        { label: 'Performance Appraisals', path: '/admin/performance', aliases: ['/admin/performance'] },
        { label: 'Resignation & Settlement', path: '/admin/separation', aliases: ['/admin/separation'] },
        { label: 'Payroll & HR Settings', path: '/admin/settings', aliases: ['/admin/settings'] },
      ],
    },
  ];

  const handleSelectRoute = (path) => {
    navigate(path);
    if (onClose) {
      onClose();
    }
  };

  return (
    <div className="admin-sidebar-inner">
      {/* Branded Header: Fixed at top of sidebar, never scrolls */}
      <div className="admin-drawer-header admin-sidebar-header">
        <div className="admin-drawer-header-top">
          <div
            style={{ cursor: 'pointer' }}
            onClick={() => handleSelectRoute('/admin/dashboard')}
            title="Arshith Connect Administrator Portal"
          >
            <BrandLogo size="compact" />
          </div>

          {onClose && (
            <button
              type="button"
              className="admin-drawer-close-btn"
              onClick={onClose}
              aria-label="Close navigation drawer"
            >
              <X size={20} />
            </button>
          )}
        </div>

        <div className="admin-drawer-branding-titles">
          <h2 className="admin-drawer-title">Administrator</h2>
          <div className="admin-drawer-subtitle">Admin</div>
        </div>
      </div>

      {/* Pure White Drawer Body with Navigation Sections and Smooth Independent Internal Scrolling */}
      <nav className="admin-drawer-menu admin-sidebar-nav" aria-label="Administrator Navigation Links" style={{ paddingBottom: '32px' }}>
        {navSections.map((section, sIdx) => (
          <div key={sIdx} className="admin-drawer-section" style={{ marginBottom: '14px' }}>
            <div
              style={{
                padding: '10px 20px 4px 20px',
                fontSize: '0.68rem',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                color: '#64748b',
              }}
            >
              {section.title}
            </div>
            {section.items.map((item, idx) => {
              const isActive =
                item.aliases.some((alias) => location.pathname === alias) ||
                location.pathname === item.path;

              return (
                <button
                  key={idx}
                  type="button"
                  className={`admin-drawer-item ${isActive ? 'active' : ''}`}
                  onClick={() => handleSelectRoute(item.path)}
                  aria-current={isActive ? 'page' : undefined}
                >
                  <span className="admin-drawer-item-label">{item.label}</span>
                </button>
              );
            })}
          </div>
        ))}
      </nav>
      {/* Note: Sign Out / Logout item is intentionally excluded from the sidebar as required */}
    </div>
  );
}
