import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bell,
  Calendar,
  Briefcase,
  FileText,
  LogOut,
  CheckCircle,
  Plus,
  CalendarDays,
  Clock,
  AlertCircle,
  Receipt,
  Coins,
  Award,
  UserMinus,
  ChevronRight,
  Star,
  Sparkles,
} from 'lucide-react';
import AttendanceCard from '../../components/employee/AttendanceCard';
import QuickActionCard from '../../components/employee/QuickActionCard';
import ApplyLeaveModal from '../../components/employee/ApplyLeaveModal';
import Modal from '../../components/common/Modal';
import { announcementService } from '../../services/announcementService';
import { meetingService } from '../../services/meetingService';
import { assignmentService } from '../../services/assignmentService';
import { holidayService } from '../../services/holidayService';
import { leaveService } from '../../services/leaveService';
import { performanceService } from '../../services/performanceService';
import { authService } from '../../services/authService';

export default function EmployeeDashboard() {
  const navigate = useNavigate();

  // Modals for Quick Actions
  const [activeModal, setActiveModal] = useState(null); // 'announcements' | 'meetings' | 'assignments' | 'leaves'

  // Live data states
  const [announcements, setAnnouncements] = useState([]);
  const [meetings, setMeetings] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [holidays, setHolidays] = useState([]);
  const [latestReview, setLatestReview] = useState(null);

  const storedUser = (() => {
    try {
      return JSON.parse(localStorage.getItem('arshith_user')) || null;
    } catch {
      return null;
    }
  })();
  const userGreetingName = storedUser?.name ? storedUser.name.split(' ')[0].toLowerCase() : 'employee';
  const employeeId = storedUser?.employeeId || storedUser?.employee_id || 'EMP-1001';

  useEffect(() => {
    const loadData = async () => {
      try {
        const [annRes, mtgRes, asgRes, holRes, perfRes] = await Promise.allSettled([
          announcementService.getAnnouncements(),
          meetingService.getMeetings(),
          assignmentService.getAssignments(),
          holidayService.getHolidays(),
          performanceService.getReviews(employeeId),
        ]);
        if (annRes.status === 'fulfilled' && Array.isArray(annRes.value)) setAnnouncements(annRes.value);
        if (mtgRes.status === 'fulfilled' && Array.isArray(mtgRes.value)) setMeetings(mtgRes.value);
        if (asgRes.status === 'fulfilled' && Array.isArray(asgRes.value)) setAssignments(asgRes.value);
        if (holRes.status === 'fulfilled' && Array.isArray(holRes.value)) setHolidays(holRes.value);
        if (perfRes.status === 'fulfilled' && Array.isArray(perfRes.value) && perfRes.value.length > 0) {
          setLatestReview(perfRes.value[0]);
        }
      } catch (err) {
        console.warn('Dashboard data fetch error', err);
      }
    };
    loadData();
  }, [employeeId]);

  const handleLogout = async () => {
    await authService.logout();
    navigate('/login');
  };

  return (
    <div className="employee-dashboard-content animate-fade-in">
      {/* Welcome Greeting (matches screenshot) */}
      <h1 className="employee-greeting-title">
        <span>Welcome,</span>
        <span style={{ textTransform: 'lowercase' }}>{userGreetingName}</span>
      </h1>

      {/* Main Today's Attendance Card */}
      <AttendanceCard />

      {/* Official Performance Appraisal Banner (when admin has submitted an appraisal) */}
      {latestReview && (
        <div
          onClick={() => navigate('/employee/performance')}
          style={{
            backgroundColor: '#ffffff',
            border: '1.5px solid #a7f3d0',
            borderRadius: '16px',
            padding: '16px 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
            marginBottom: '24px',
            background: 'linear-gradient(135deg, #ffffff 0%, #f0fdf4 100%)',
            boxShadow: '0 2px 10px rgba(11, 61, 43, 0.04)',
            transition: 'all 0.2s ease',
          }}
          title="Click to view your full performance scorecard & manager feedback"
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div
              style={{
                width: '42px',
                height: '42px',
                borderRadius: '12px',
                backgroundColor: '#d1fae5',
                color: '#047857',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <Award size={22} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '0.925rem', fontWeight: 800, color: '#0b3d2b' }}>
                  Performance Appraisal Published
                </span>
                <span
                  style={{
                    fontSize: '0.75rem',
                    fontWeight: 800,
                    color: '#d97706',
                    backgroundColor: '#fef3c7',
                    padding: '2px 8px',
                    borderRadius: '999px',
                  }}
                >
                  ⭐ {Number(latestReview.rating).toFixed(1)} / 5.0
                </span>
                {latestReview.recommended_increment_pct > 0 && (
                  <span
                    style={{
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      color: '#047857',
                      backgroundColor: '#d1fae5',
                      padding: '2px 8px',
                      borderRadius: '999px',
                    }}
                  >
                    +{latestReview.recommended_increment_pct}% Increment
                  </span>
                )}
              </div>
              <div style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '2px' }}>
                {latestReview.review_period} &bull; Evaluated by {latestReview.evaluated_by || 'Management'}
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#047857', fontWeight: 700, fontSize: '0.8rem', flexShrink: 0 }}>
            <span>View Appraisal</span>
            <ChevronRight size={18} />
          </div>
        </div>
      )}

      {/* Payroll & Employee Self-Service Section (matching user screenshot) */}
      <section style={{ marginBottom: '28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
          <div>
            <h2 style={{ fontSize: '1.15rem', fontWeight: '700', color: '#0b3d2b', margin: 0 }}>
              Payroll & Self-Service
            </h2>
            <p style={{ fontSize: '0.8rem', color: '#64748b', margin: '2px 0 0 0' }}>
              Access your payslips, loans, performance and settlement
            </p>
          </div>
          <span style={{ fontSize: '0.8rem', color: '#0d9488', fontWeight: '600' }}>HRMS Portal</span>
        </div>

        <div className="quick-actions-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))' }}>
          <QuickActionCard
            title="My Payslips"
            icon={Receipt}
            iconBg="#ecfdf5"
            iconColor="#059669"
            onClick={() => navigate('/employee/payslips')}
          />
          <QuickActionCard
            title="My Loans & Advances"
            icon={Coins}
            iconBg="#fffbeb"
            iconColor="#d97706"
            onClick={() => navigate('/employee/loans')}
          />
          <QuickActionCard
            title="My Performance"
            icon={Award}
            iconBg="#f0fdf4"
            iconColor="#047857"
            onClick={() => navigate('/employee/performance')}
          />
          <QuickActionCard
            title="Resignation & Settlement"
            icon={UserMinus}
            iconBg="#fef2f2"
            iconColor="#dc2626"
            onClick={() => navigate('/employee/resignation')}
          />
        </div>
      </section>

      {/* Quick Actions Section */}
      <section className="quick-actions-section">
        <h2 className="section-title">Quick Actions</h2>
        <p className="section-desc">Everything you need, in one place</p>

        <div className="quick-actions-grid">
          <QuickActionCard
            title="Announcements"
            icon={Bell}
            iconBg="#f3f0ff"
            iconColor="#6941c6"
            onClick={() => setActiveModal('announcements')}
          />
          <QuickActionCard
            title="Meetings"
            icon={Calendar}
            iconBg="#e0f2fe"
            iconColor="#0284c7"
            onClick={() => setActiveModal('meetings')}
          />
          <QuickActionCard
            title="Work Assignments"
            icon={Briefcase}
            iconBg="#ecfdf5"
            iconColor="#0d9488"
            onClick={() => setActiveModal('assignments')}
          />
          <QuickActionCard
            title="Leave Management"
            icon={FileText}
            iconBg="#fff7ed"
            iconColor="#ea580c"
            onClick={() => setActiveModal('leaves')}
          />
        </div>
      </section>

      {/* Upcoming Holidays Strip */}
      <section style={{ marginBottom: '28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
          <h2 style={{ fontSize: '1.15rem', fontWeight: '700', color: '#0b3d2b', margin: 0 }}>
            Upcoming Company Holidays
          </h2>
          <span style={{ fontSize: '0.8rem', color: '#0d9488', fontWeight: '600' }}>2026 Calendar</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {(holidays.length > 0 ? holidays.slice(0, 2) : []).map((holiday) => (
            <div
              key={holiday.id}
              style={{
                backgroundColor: '#ffffff',
                borderRadius: '16px',
                padding: '14px 18px',
                border: '1px solid #e2e8f0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div
                  style={{
                    width: '38px',
                    height: '38px',
                    borderRadius: '10px',
                    backgroundColor: '#fff7ed',
                    color: '#ea580c',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  <CalendarDays size={18} />
                </div>
                <div>
                  <div style={{ fontSize: '0.9rem', fontWeight: '700', color: '#1e293b' }}>
                    {holiday.name}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                    {holiday.type} &bull; {holiday.description}
                  </div>
                </div>
              </div>
              <span
                style={{
                  fontSize: '0.8rem',
                  fontWeight: '700',
                  color: '#ea580c',
                  backgroundColor: '#fff7ed',
                  padding: '4px 10px',
                  borderRadius: '999px'
                }}
              >
                {holiday.date}
              </span>
            </div>
          ))}
          {holidays.length === 0 && (
            <div style={{ padding: '16px', color: '#64748b', fontSize: '0.85rem' }}>
              No upcoming company holidays listed.
            </div>
          )}
        </div>
      </section>

      {/* Log Out Button (matches screenshot) */}
      <button
        type="button"
        className="btn-logout-bottom"
        onClick={handleLogout}
      >
        <LogOut size={16} />
        <span>Log Out</span>
      </button>

      {/* Quick Action Modals */}
      {/* 1. Announcements Modal */}
      <Modal
        isOpen={activeModal === 'announcements'}
        onClose={() => setActiveModal(null)}
        title="Company Announcements"
        subtitle="Latest updates from management & HR"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {announcements.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#64748b', padding: '16px' }}>No announcements found.</div>
          ) : (
            announcements.map((item) => (
              <div
                key={item.id}
                style={{
                  backgroundColor: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '14px',
                  padding: '16px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#6941c6', fontWeight: '700' }}>{item.author}</span>
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{item.date}</span>
                </div>
                <h3 style={{ fontSize: '0.95rem', fontWeight: '700', color: '#0b3d2b', marginBottom: '6px' }}>
                  {item.title}
                </h3>
                <p style={{ fontSize: '0.825rem', color: '#475569', lineHeight: 1.45, margin: 0 }}>
                  {item.message}
                </p>
              </div>
            ))
          )}
        </div>
      </Modal>

      {/* 2. Meetings Modal */}
      <Modal
        isOpen={activeModal === 'meetings'}
        onClose={() => setActiveModal(null)}
        title="Your Scheduled Meetings"
        subtitle="Today & upcoming team briefings"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {meetings.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#64748b', padding: '16px' }}>No scheduled meetings.</div>
          ) : (
            meetings.map((item) => (
              <div
                key={item.id}
                style={{
                  backgroundColor: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '14px',
                  padding: '16px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#0284c7', fontWeight: '700' }}>{item.time}</span>
                  <span style={{ fontSize: '0.75rem', color: '#64748b' }}>{item.date}</span>
                </div>
                <h3 style={{ fontSize: '0.95rem', fontWeight: '700', color: '#0b3d2b', marginBottom: '4px' }}>
                  {item.title}
                </h3>
                <p style={{ fontSize: '0.8rem', color: '#475569', marginBottom: '8px' }}>
                  {item.description}
                </p>
                <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                  Location / Link: <strong>{item.room || item.link || 'Online'}</strong>
                </div>
              </div>
            ))
          )}
        </div>
      </Modal>

      {/* 3. Work Assignments Modal */}
      <Modal
        isOpen={activeModal === 'assignments'}
        onClose={() => setActiveModal(null)}
        title="Work Assignments"
        subtitle="Current sprint tasks and deliverables"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {assignments.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#64748b', padding: '16px' }}>No tasks assigned.</div>
          ) : (
            assignments.map((task) => (
              <div
                key={task.id}
                style={{
                  backgroundColor: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '14px',
                  padding: '16px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#059669', fontWeight: '700' }}>
                    Deadline: {task.deadline}
                  </span>
                  <span
                    style={{
                      fontSize: '0.7rem',
                      fontWeight: '700',
                      color: task.priority === 'High' ? '#dc2626' : '#2563eb',
                      backgroundColor: task.priority === 'High' ? '#fef2f2' : '#eff6ff',
                      padding: '2px 8px',
                      borderRadius: '999px'
                    }}
                  >
                    {task.priority} Priority
                  </span>
                </div>
                <h3 style={{ fontSize: '0.95rem', fontWeight: '700', color: '#0b3d2b', marginBottom: '8px' }}>
                  {task.title}
                </h3>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ flex: 1, height: '6px', backgroundColor: '#e2e8f0', borderRadius: '999px', overflow: 'hidden' }}>
                    <div style={{ width: `${task.progress || 0}%`, height: '100%', backgroundColor: '#10b981' }} />
                  </div>
                  <span style={{ fontSize: '0.75rem', fontWeight: '700', color: '#475569' }}>
                    {task.progress || 0}%
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </Modal>

      {/* 4. Leave Management & Apply Modal (Authoritative Apply for Leave form from screenshot 1) */}
      <ApplyLeaveModal
        isOpen={activeModal === 'leaves'}
        onClose={() => setActiveModal(null)}
      />
    </div>
  );
}
