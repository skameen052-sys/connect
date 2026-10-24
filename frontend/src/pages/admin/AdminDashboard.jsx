import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckCircle,
  Star,
  FileText,
  Megaphone,
  Plus,
  ChevronRight,
  LogOut,
} from 'lucide-react';
import AdminStatCard from '../../components/admin/AdminStatCard';
import AdminManagementCard from '../../components/admin/AdminManagementCard';
import Modal from '../../components/common/Modal';
import { dashboardService } from '../../services/dashboardService';
import { announcementService } from '../../services/announcementService';
import { authService } from '../../services/authService';

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState({
    totalPresent: 0,
    wfo: 0,
    wfh: 0,
    late: 0,
    pendingLeaves: 0,
    thisMonthHolidays: 0,
  });
  const [announcements, setAnnouncements] = useState([]);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newMessage, setNewMessage] = useState('');
  const [newAuthor, setNewAuthor] = useState('Admin Office');
  const [isLoading, setIsLoading] = useState(true);

  const loadDashboardData = useCallback(async () => {
    try {
      const data = await dashboardService.getAdminDashboard();
      if (data && data.stats) {
        setStats(data.stats);
      }
      if (data && data.announcements) {
        setAnnouncements(data.announcements);
      }
    } catch (err) {
      console.error('Failed to load admin dashboard data', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  const handleLogout = useCallback(() => {
    authService.logout();
    navigate('/admin/login');
  }, [navigate]);

  const handleAddAnnouncement = async (e) => {
    e.preventDefault();
    if (!newTitle.trim() || !newMessage.trim()) return;

    try {
      await announcementService.createAnnouncement({
        title: newTitle.trim(),
        message: newMessage.trim(),
        author: newAuthor.trim() || 'Admin Office',
      });
      await loadDashboardData();
      setNewTitle('');
      setNewMessage('');
      setIsAddModalOpen(false);
    } catch (err) {
      console.error('Failed to save announcement', err);
    }
  };

  const storedUser = authService.getCurrentUser();
  const adminName = storedUser?.name || storedUser?.fullName || 'Administrator';
  const adminEmail = storedUser?.email || 'admin@arshith.com';

  return (
    <div className="admin-dashboard-view admin-main-page animate-fade-in">
      {/* Title Header matching Screenshot 2 */}
      <div style={{ marginBottom: '20px' }}>
        <h1 style={{ fontSize: '1.45rem', fontWeight: '700', color: '#0b3d2b', margin: 0, letterSpacing: '-0.3px' }}>
          Admin Dashboard
        </h1>
        <div style={{ marginTop: '4px' }}>
          <div style={{ fontSize: '0.925rem', fontWeight: '600', color: '#1e293b' }}>
            {adminName}
          </div>
          <div style={{ fontSize: '0.825rem', color: '#64748b' }}>
            {adminEmail}
          </div>
        </div>
      </div>

      {/* Section: Today's Attendance matching Screenshot 2 */}
      <section style={{ marginBottom: '26px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: '800', color: '#0b3d2b', margin: 0 }}>
            Today's Attendance
          </h2>
        </div>

        <div className="admin-today-stats-grid">
          {/* Large prominent Total Present */}
          <AdminStatCard
            label="TOTAL PRESENT"
            value={stats.totalPresent}
            colorClass="stat-val-present"
            widthClass="full-width"
          />

          {/* 3 Columns: WFO, WFH, LATE */}
          <AdminStatCard
            label="WFO"
            value={stats.wfo}
            colorClass="stat-val-wfo"
            widthClass="one-third"
          />
          <AdminStatCard
            label="WFH"
            value={stats.wfh}
            colorClass="stat-val-wfo"
            widthClass="one-third"
          />
          <AdminStatCard
            label="LATE"
            value={stats.late}
            colorClass="stat-val-late"
            widthClass="one-third"
          />

          {/* 2 Columns: PENDING LEAVES, THIS MONTH HOLIDAYS */}
          <AdminStatCard
            label="PENDING LEAVES"
            value={stats.pendingLeaves}
            colorClass="stat-val-pending"
            widthClass="half-width"
          />
          <AdminStatCard
            label="THIS MONTH HOLIDAYS"
            value={stats.thisMonthHolidays}
            colorClass="stat-val-holiday"
            widthClass="half-width"
          />
        </div>
      </section>

      {/* Section: Management (4 cards) */}
      <section style={{ marginBottom: '26px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: '800', color: '#0b3d2b', margin: 0 }}>
            Management
          </h2>
        </div>

        <div className="management-cards-grid">
          <AdminManagementCard
            title="Attendance"
            description="Manage attendance"
            icon={CheckCircle}
            colorScheme="green"
            onClick={() => navigate('/admin/attendance')}
          />
          <AdminManagementCard
            title="Leave"
            description="Review leave requests"
            icon={CheckCircle}
            colorScheme="green"
            onClick={() => navigate('/admin/leaves')}
          />
          <AdminManagementCard
            title="Holiday"
            description="Manage company holidays"
            icon={Star}
            colorScheme="orange"
            onClick={() => navigate('/admin/holidays')}
          />
          <AdminManagementCard
            title="Reports"
            description="View attendance reports"
            icon={FileText}
            colorScheme="blue"
            onClick={() => navigate('/admin/reports')}
          />
        </div>
      </section>

      {/* Section: Meeting Management matching Screenshot 2 */}
      <section style={{ marginBottom: '24px' }}>
        <div
          className="admin-action-card"
          onClick={() => navigate('/admin/meetings')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') navigate('/admin/meetings'); }}
        >
          <div className="admin-action-card-left">
            <div className="admin-action-avatar" style={{ backgroundColor: '#0284c7' }}>
              M
            </div>
            <div className="admin-action-card-info">
              <h3 className="admin-action-card-title">Meeting Management</h3>
              <p className="admin-action-card-desc">Schedule and manage employee meetings</p>
            </div>
          </div>
          <div className="admin-action-card-chevron">
            <ChevronRight size={20} />
          </div>
        </div>
      </section>

      {/* Section: Announcements matching Screenshot 2 */}
      <section style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: '800', color: '#0b3d2b', margin: 0 }}>
            Announcements
          </h2>
          <button
            type="button"
            className="btn-primary-action"
            onClick={() => setIsAddModalOpen(true)}
            style={{ height: '32px', fontSize: '0.78rem', padding: '0 10px' }}
          >
            <Plus size={14} />
            <span>Add Announcement</span>
          </button>
        </div>

        {/* Card: Announcement Management */}
        <div
          className="admin-action-card"
          onClick={() => navigate('/admin/announcements')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') navigate('/admin/announcements'); }}
        >
          <div className="admin-action-card-left">
            <div className="admin-action-avatar" style={{ backgroundColor: '#0d9488' }}>
              A
            </div>
            <div className="admin-action-card-info">
              <h3 className="admin-action-card-title">Announcement Management</h3>
              <p className="admin-action-card-desc">Publish announcements for employees</p>
            </div>
          </div>
          <div className="admin-action-card-chevron">
            <ChevronRight size={20} />
          </div>
        </div>

        {/* Card: Office Timings matching Screenshot 2 */}
        <div
          className="admin-action-card"
          onClick={() => navigate('/admin/office-timings')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') navigate('/admin/office-timings'); }}
        >
          <div className="admin-action-card-left">
            <div className="admin-action-avatar" style={{ backgroundColor: '#0284c7' }}>
              T
            </div>
            <div className="admin-action-card-info">
              <h3 className="admin-action-card-title">Office Timings</h3>
              <p className="admin-action-card-desc">Set office hours and notify employees</p>
            </div>
          </div>
          <div className="admin-action-card-chevron">
            <ChevronRight size={20} />
          </div>
        </div>

        {/* Announcements list items preview */}
        <div className="announcements-list" style={{ marginTop: '12px' }}>
          {announcements.length === 0 ? (
            <div
              style={{
                backgroundColor: '#ffffff',
                borderRadius: '14px',
                padding: '16px 18px',
                border: '1px dashed #cbd5e1',
                color: '#64748b',
                fontSize: '0.875rem',
                textAlign: 'center',
              }}
            >
              No announcements published.
            </div>
          ) : (
            announcements.map((ann) => (
              <div key={ann.id} className="announcement-item-card">
                <div className="announcement-top-meta">
                  <span style={{ fontWeight: '600', color: '#0b3d2b' }}>{ann.author}</span>
                  <span>{ann.date}</span>
                </div>
                <div className="announcement-item-title">{ann.title}</div>
                <div className="announcement-item-body">{ann.message}</div>
              </div>
            ))
          )}
        </div>
      </section>

      {/* Section: Work Management matching Screenshots 2 & 4 */}
      <section style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: '800', color: '#0b3d2b', marginBottom: '12px' }}>
          Work Management
        </h2>

        {/* 1. Employees */}
        <div
          className="admin-action-card"
          onClick={() => navigate('/admin/employees')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') navigate('/admin/employees'); }}
        >
          <div className="admin-action-card-left">
            <div className="admin-action-avatar" style={{ backgroundColor: '#059669' }}>
              E
            </div>
            <div className="admin-action-card-info">
              <h3 className="admin-action-card-title">Employees</h3>
              <p className="admin-action-card-desc">View all registered employees</p>
            </div>
          </div>
          <div className="admin-action-card-chevron">
            <ChevronRight size={20} />
          </div>
        </div>

        {/* 2. Employee List */}
        <div
          className="admin-action-card"
          onClick={() => navigate('/admin/employees/list')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') navigate('/admin/employees/list'); }}
        >
          <div className="admin-action-card-left">
            <div className="admin-action-avatar" style={{ backgroundColor: '#0d9488' }}>
              L
            </div>
            <div className="admin-action-card-info">
              <h3 className="admin-action-card-title">Employee List</h3>
              <p className="admin-action-card-desc">View and manage employee details</p>
            </div>
          </div>
          <div className="admin-action-card-chevron">
            <ChevronRight size={20} />
          </div>
        </div>

        {/* 3. Teams */}
        <div
          className="admin-action-card"
          onClick={() => navigate('/admin/teams')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') navigate('/admin/teams'); }}
        >
          <div className="admin-action-card-left">
            <div className="admin-action-avatar" style={{ backgroundColor: '#0d9488' }}>
              T
            </div>
            <div className="admin-action-card-info">
              <h3 className="admin-action-card-title">Teams</h3>
              <p className="admin-action-card-desc">Create teams from registered employees</p>
            </div>
          </div>
          <div className="admin-action-card-chevron">
            <ChevronRight size={20} />
          </div>
        </div>

        {/* 4. Registration Requests */}
        <div
          className="admin-action-card"
          onClick={() => navigate('/admin/registration-requests')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') navigate('/admin/registration-requests'); }}
        >
          <div className="admin-action-card-left">
            <div className="admin-action-avatar" style={{ backgroundColor: '#0d9488' }}>
              R
            </div>
            <div className="admin-action-card-info">
              <h3 className="admin-action-card-title">Registration Requests</h3>
              <p className="admin-action-card-desc">Review and approve new employee accounts</p>
            </div>
          </div>
          <div className="admin-action-card-chevron">
            <ChevronRight size={20} />
          </div>
        </div>

        {/* 5. Work Assignments matching Screenshot 4 */}
        <div
          className="admin-action-card"
          onClick={() => navigate('/admin/assignments')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') navigate('/admin/assignments'); }}
        >
          <div className="admin-action-card-left">
            <div className="admin-action-avatar" style={{ backgroundColor: '#0284c7' }}>
              W
            </div>
            <div className="admin-action-card-info">
              <h3 className="admin-action-card-title">Work Assignments</h3>
              <p className="admin-action-card-desc">Assign and manage employee work</p>
            </div>
          </div>
          <div className="admin-action-card-chevron">
            <ChevronRight size={20} />
          </div>
        </div>

        {/* 6. Work Updates matching Screenshot 4 */}
        <div
          className="admin-action-card"
          onClick={() => navigate('/admin/updates')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') navigate('/admin/updates'); }}
        >
          <div className="admin-action-card-left">
            <div className="admin-action-avatar" style={{ backgroundColor: '#1d4ed8' }}>
              U
            </div>
            <div className="admin-action-card-info">
              <h3 className="admin-action-card-title">Work Updates</h3>
              <p className="admin-action-card-desc">View employee daily work updates</p>
            </div>
          </div>
          <div className="admin-action-card-chevron">
            <ChevronRight size={20} />
          </div>
        </div>
      </section>

      {/* Section: Payroll & Finance */}
      <section style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: '800', color: '#0b3d2b', marginBottom: '12px' }}>
          Payroll & Finance
        </h2>

        {/* 1. Payroll Engine */}
        <div
          className="admin-action-card"
          onClick={() => navigate('/admin/payroll')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') navigate('/admin/payroll'); }}
        >
          <div className="admin-action-card-left">
            <div className="admin-action-avatar" style={{ backgroundColor: '#047857' }}>
              P
            </div>
            <div className="admin-action-card-info">
              <h3 className="admin-action-card-title">Payroll Engine</h3>
              <p className="admin-action-card-desc">Calculate monthly salary, loss of pay & automated statutory deductions</p>
            </div>
          </div>
          <div className="admin-action-card-chevron">
            <ChevronRight size={20} />
          </div>
        </div>

        {/* 2. Salary Structures */}
        <div
          className="admin-action-card"
          onClick={() => navigate('/admin/salary-structures')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') navigate('/admin/salary-structures'); }}
        >
          <div className="admin-action-card-left">
            <div className="admin-action-avatar" style={{ backgroundColor: '#0284c7' }}>
              S
            </div>
            <div className="admin-action-card-info">
              <h3 className="admin-action-card-title">Salary Structures</h3>
              <p className="admin-action-card-desc">Configure base salary, HRA, allowances, PF/ESI & deductions</p>
            </div>
          </div>
          <div className="admin-action-card-chevron">
            <ChevronRight size={20} />
          </div>
        </div>

        {/* 3. Payslip Generation */}
        <div
          className="admin-action-card"
          onClick={() => navigate('/admin/payslips')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') navigate('/admin/payslips'); }}
        >
          <div className="admin-action-card-left">
            <div className="admin-action-avatar" style={{ backgroundColor: '#0d9488' }}>
              G
            </div>
            <div className="admin-action-card-info">
              <h3 className="admin-action-card-title">Payslip Generation</h3>
              <p className="admin-action-card-desc">Generate, preview and download official branded monthly PDF payslips</p>
            </div>
          </div>
          <div className="admin-action-card-chevron">
            <ChevronRight size={20} />
          </div>
        </div>

        {/* 4. Salary Payments */}
        <div
          className="admin-action-card"
          onClick={() => navigate('/admin/payments')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') navigate('/admin/payments'); }}
        >
          <div className="admin-action-card-left">
            <div className="admin-action-avatar" style={{ backgroundColor: '#16a34a' }}>
              B
            </div>
            <div className="admin-action-card-info">
              <h3 className="admin-action-card-title">Salary Payments</h3>
              <p className="admin-action-card-desc">Export bank batch payment CSV (NEFT/RTGS) and record UTR confirmations</p>
            </div>
          </div>
          <div className="admin-action-card-chevron">
            <ChevronRight size={20} />
          </div>
        </div>

        {/* 5. Employee Loans */}
        <div
          className="admin-action-card"
          onClick={() => navigate('/admin/loans')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') navigate('/admin/loans'); }}
        >
          <div className="admin-action-card-left">
            <div className="admin-action-avatar" style={{ backgroundColor: '#ca8a04' }}>
              L
            </div>
            <div className="admin-action-card-info">
              <h3 className="admin-action-card-title">Employee Loans</h3>
              <p className="admin-action-card-desc">Manage loan applications, approvals and monthly payroll EMI deductions</p>
            </div>
          </div>
          <div className="admin-action-card-chevron">
            <ChevronRight size={20} />
          </div>
        </div>
      </section>

      {/* Section: HR Operations & Governance */}
      <section style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: '800', color: '#0b3d2b', marginBottom: '12px' }}>
          HR Operations & Governance
        </h2>

        {/* 1. Departments & Designations */}
        <div
          className="admin-action-card"
          onClick={() => navigate('/admin/departments')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') navigate('/admin/departments'); }}
        >
          <div className="admin-action-card-left">
            <div className="admin-action-avatar" style={{ backgroundColor: '#7c3aed' }}>
              D
            </div>
            <div className="admin-action-card-info">
              <h3 className="admin-action-card-title">Departments & Designations</h3>
              <p className="admin-action-card-desc">Manage organizational hierarchy, department codes and job titles</p>
            </div>
          </div>
          <div className="admin-action-card-chevron">
            <ChevronRight size={20} />
          </div>
        </div>

        {/* 2. Performance Appraisals */}
        <div
          className="admin-action-card"
          onClick={() => navigate('/admin/performance')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') navigate('/admin/performance'); }}
        >
          <div className="admin-action-card-left">
            <div className="admin-action-avatar" style={{ backgroundColor: '#2563eb' }}>
              A
            </div>
            <div className="admin-action-card-info">
              <h3 className="admin-action-card-title">Performance Appraisals</h3>
              <p className="admin-action-card-desc">Track review cycles, employee KPI ratings and increment recommendations</p>
            </div>
          </div>
          <div className="admin-action-card-chevron">
            <ChevronRight size={20} />
          </div>
        </div>

        {/* 3. Resignation & Settlement */}
        <div
          className="admin-action-card"
          onClick={() => navigate('/admin/separation')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') navigate('/admin/separation'); }}
        >
          <div className="admin-action-card-left">
            <div className="admin-action-avatar" style={{ backgroundColor: '#dc2626' }}>
              R
            </div>
            <div className="admin-action-card-info">
              <h3 className="admin-action-card-title">Resignation & Settlement</h3>
              <p className="admin-action-card-desc">Manage employee exits, notice periods & Full-and-Final (FnF) settlements</p>
            </div>
          </div>
          <div className="admin-action-card-chevron">
            <ChevronRight size={20} />
          </div>
        </div>

        {/* 4. Payroll & HR Settings */}
        <div
          className="admin-action-card"
          onClick={() => navigate('/admin/settings')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') navigate('/admin/settings'); }}
        >
          <div className="admin-action-card-left">
            <div className="admin-action-avatar" style={{ backgroundColor: '#475569' }}>
              S
            </div>
            <div className="admin-action-card-info">
              <h3 className="admin-action-card-title">Payroll & HR Settings</h3>
              <p className="admin-action-card-desc">Configure company profiles, daily salary divisor, cutoff days & statutory rules</p>
            </div>
          </div>
          <div className="admin-action-card-chevron">
            <ChevronRight size={20} />
          </div>
        </div>
      </section>

      {/* Prominent Red Logout Button matching Screenshot 4 */}
      <section style={{ marginTop: '16px' }}>
        <button
          type="button"
          className="btn-admin-logout"
          onClick={handleLogout}
        >
          <LogOut size={18} />
          <span>LOGOUT</span>
        </button>
      </section>

      {/* Add Announcement Modal */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Create New Announcement"
        subtitle="Broadcast an update across the company"
      >
        <form onSubmit={handleAddAnnouncement}>
          <div className="form-group">
            <label className="form-label">Announcement Title</label>
            <input
              type="text"
              required
              className="form-input-auth"
              placeholder="e.g. Quarterly Team Townhall"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Author / Department</label>
            <input
              type="text"
              required
              className="form-input-auth"
              placeholder="e.g. Admin Office or HR"
              value={newAuthor}
              onChange={(e) => setNewAuthor(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Message Content</label>
            <textarea
              rows={4}
              required
              className="form-input-auth"
              style={{ height: '90px', padding: '10px', resize: 'vertical' }}
              placeholder="Write the full announcement message..."
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '14px' }}>
            <button
              type="button"
              className="btn-secondary-gray"
              style={{ width: 'auto', padding: '0 16px', height: '38px' }}
              onClick={() => setIsAddModalOpen(false)}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary-purple"
              style={{ width: 'auto', padding: '0 18px', height: '38px' }}
            >
              Publish Announcement
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
