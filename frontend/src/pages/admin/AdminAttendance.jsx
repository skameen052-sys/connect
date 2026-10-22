import React, { useState, useEffect, useCallback } from 'react';
import { Search, Filter, Edit2, Eye, Calendar, UserCheck, CheckCircle2, AlertCircle } from 'lucide-react';
import PageHeader from '../../components/common/PageHeader';
import EmptyState from '../../components/common/EmptyState';
import Modal from '../../components/common/Modal';
import { attendanceService } from '../../services/attendanceService';

export default function AdminAttendance() {
  const [records, setRecords] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [modeFilter, setModeFilter] = useState('ALL');
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Edit record form state
  const [editStatus, setEditStatus] = useState('');
  const [editWorkMode, setEditWorkMode] = useState('');
  const [editCheckIn, setEditCheckIn] = useState('');
  const [editCheckOut, setEditCheckOut] = useState('');
  const [editLateReason, setEditLateReason] = useState('');

  // View verification details state
  const [viewRecord, setViewRecord] = useState(null);
  const [isViewModalOpen, setIsViewModalOpen] = useState(false);
  const [viewPhotoUrl, setViewPhotoUrl] = useState(null);
  const [isPhotoLoading, setIsPhotoLoading] = useState(false);

  const loadAttendanceRecords = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await attendanceService.getRecords();
      setRecords(data || []);
    } catch (err) {
      console.error('Failed to load attendance records', err);
      setRecords([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAttendanceRecords();
  }, [loadAttendanceRecords]);

  const filteredRecords = records.filter((rec) => {
    const matchesSearch =
      (rec.employeeName || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (rec.employeeId || '').toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus =
      statusFilter === 'ALL' ||
      (statusFilter === 'LATE'
        ? (rec.status || '').toUpperCase() === 'LATE' || Boolean(rec.isLate)
        : (rec.status || '').toUpperCase() === statusFilter);
    const matchesMode = modeFilter === 'ALL' || (rec.workMode || '').toUpperCase() === modeFilter;
    return matchesSearch && matchesStatus && matchesMode;
  });

  const handleOpenEdit = (rec) => {
    setSelectedRecord(rec);
    setEditStatus(rec.status);
    setEditWorkMode(rec.workMode);
    setEditCheckIn(rec.checkIn);
    setEditCheckOut(rec.checkOut);
    setEditLateReason(rec.lateReason || '');
    setIsEditModalOpen(true);
  };

  const handleOpenView = async (rec) => {
    setViewRecord(rec);
    setIsViewModalOpen(true);
    setViewPhotoUrl(null);
    if (rec.hasCheckInPhoto) {
      setIsPhotoLoading(true);
      try {
        const blob = await attendanceService.getPhotoBlob(rec.id, 'check-in');
        setViewPhotoUrl(URL.createObjectURL(blob));
      } catch (err) {
        console.warn('Failed to load employee photo for admin:', err);
      } finally {
        setIsPhotoLoading(false);
      }
    }
  };

  const handleSaveEdit = async (e) => {
    e.preventDefault();
    if (!selectedRecord) return;
    try {
      await attendanceService.updateRecord(selectedRecord.id, {
        status: editStatus,
        workMode: editWorkMode,
        checkIn: editCheckIn,
        checkOut: editCheckOut,
        lateReason: editLateReason,
      });
      await loadAttendanceRecords();
      setIsEditModalOpen(false);
    } catch (err) {
      console.error('Failed to update attendance record', err);
    }
  };

  return (
    <div className="attendance-management-view animate-fade-in">
      <PageHeader
        title="Attendance Management"
        subtitle="Monitor, verify and adjust daily employee attendance records"
        breadcrumb={[
          { label: 'Admin', path: '/admin/dashboard' },
          { label: 'Attendance' },
        ]}
      />

      <div className="management-page-card">
        {/* Filter Toolbar */}
        <div className="filter-toolbar">
          <div className="search-input-box">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search by Employee Name or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="filter-actions-group">
            <select
              className="filter-select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="ALL">All Statuses</option>
              <option value="PRESENT">Present</option>
              <option value="LATE">Late</option>
              <option value="ABSENT">Absent</option>
            </select>

            <select
              className="filter-select"
              value={modeFilter}
              onChange={(e) => setModeFilter(e.target.value)}
            >
              <option value="ALL">All Work Modes</option>
              <option value="WFO">WFO</option>
              <option value="WFH">WFH</option>
            </select>
          </div>
        </div>

        {/* Attendance Records Table */}
        {filteredRecords.length === 0 ? (
          <EmptyState
            title="No Attendance Records Found"
            description="No employee attendance records match your current filter criteria."
          />
        ) : (
          <div className="table-responsive-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Department</th>
                  <th>Work Mode</th>
                  <th>Check-In</th>
                  <th>Check-Out</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredRecords.map((rec) => {
                  let statusBadgeClass = 'badge-absent';
                  if (rec.status.toUpperCase() === 'PRESENT') statusBadgeClass = 'badge-present';
                  if (rec.status.toUpperCase() === 'LATE') statusBadgeClass = 'badge-late';

                  return (
                    <tr key={rec.id}>
                      <td>
                        <div style={{ fontWeight: '700', color: '#0b3d2b' }}>
                          {rec.employeeName}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                          {rec.employeeId}
                        </div>
                      </td>
                      <td>{rec.department}</td>
                      <td>
                        <span
                          style={{
                            fontSize: '0.78rem',
                            fontWeight: '700',
                            padding: '2px 8px',
                            borderRadius: '6px',
                            backgroundColor: rec.workMode === 'WFO' ? '#f0fdf4' : '#eff6ff',
                            color: rec.workMode === 'WFO' ? '#15803d' : '#1d4ed8',
                          }}
                        >
                          {rec.workMode}
                        </span>
                      </td>
                      <td style={{ fontWeight: '600' }}>{rec.checkIn}</td>
                      <td style={{ color: '#64748b' }}>{rec.checkOut}</td>
                      <td>
                        {rec.isLate || (rec.status || '').toUpperCase() === 'LATE' ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', alignItems: 'flex-start' }}>
                            <span className="badge-status badge-late">
                              Late
                            </span>
                            {rec.lateReason ? (
                              <span
                                style={{
                                  fontSize: '0.68rem',
                                  color: '#166534',
                                  backgroundColor: '#f0fdf4',
                                  border: '1px solid #bbf7d0',
                                  borderRadius: '4px',
                                  padding: '1px 5px',
                                  maxWidth: '130px',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap',
                                }}
                                title={`Reason: ${rec.lateReason}`}
                              >
                                {rec.lateReason}
                              </span>
                            ) : (
                              <span
                                style={{
                                  fontSize: '0.68rem',
                                  color: '#b91c1c',
                                  backgroundColor: '#fef2f2',
                                  border: '1px solid #fecaca',
                                  borderRadius: '4px',
                                  padding: '1px 5px',
                                  whiteSpace: 'nowrap',
                                }}
                              >
                                Reason Pending
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className={`badge-status ${statusBadgeClass}`}>
                            {rec.status}
                          </span>
                        )}
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <button
                            type="button"
                            className="table-action-btn"
                            onClick={() => handleOpenView(rec)}
                            title="View Verification Details & Photo"
                            style={{ backgroundColor: '#f0fdf4', color: '#166534', border: '1px solid #bbf7d0' }}
                          >
                            <Eye size={14} />
                            <span>View</span>
                          </button>
                          <button
                            type="button"
                            className="table-action-btn"
                            onClick={() => handleOpenEdit(rec)}
                            title="Adjust Attendance Record"
                          >
                            <Edit2 size={14} />
                            <span>Adjust</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Adjust Attendance Modal */}
      <Modal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        title="Adjust Attendance Record"
        subtitle={`Editing log for ${selectedRecord?.employeeName} (${selectedRecord?.employeeId})`}
      >
        {selectedRecord && (
          <form onSubmit={handleSaveEdit}>
            <div className="form-group">
              <label className="form-label">Attendance Status</label>
              <select
                className="form-input-auth"
                value={editStatus}
                onChange={(e) => setEditStatus(e.target.value)}
              >
                <option value="Present">Present</option>
                <option value="Late">Late</option>
                <option value="Absent">Absent</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Work Mode</label>
              <select
                className="form-input-auth"
                value={editWorkMode}
                onChange={(e) => setEditWorkMode(e.target.value)}
              >
                <option value="WFO">Work From Office (WFO)</option>
                <option value="WFH">Work From Home (WFH)</option>
                <option value="--">None / Absent</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Check-In Time</label>
              <input
                type="text"
                className="form-input-auth"
                placeholder="e.g. 09:15 AM"
                value={editCheckIn}
                onChange={(e) => setEditCheckIn(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Check-Out Time</label>
              <input
                type="text"
                className="form-input-auth"
                placeholder="e.g. 06:30 PM or --"
                value={editCheckOut}
                onChange={(e) => setEditCheckOut(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Late Arrival Reason</label>
              <textarea
                className="form-input-auth"
                rows={2}
                placeholder="Reason provided for late arrival..."
                value={editLateReason}
                onChange={(e) => setEditLateReason(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '16px' }}>
              <button
                type="button"
                className="btn-secondary-gray"
                style={{ width: 'auto', padding: '0 16px', height: '38px' }}
                onClick={() => setIsEditModalOpen(false)}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn-primary-purple"
                style={{ width: 'auto', padding: '0 18px', height: '38px' }}
              >
                Save Changes
              </button>
            </div>
          </form>
        )}
      </Modal>

      {/* View Attendance Verification Details Modal */}
      <Modal
        isOpen={isViewModalOpen}
        onClose={() => setIsViewModalOpen(false)}
        title="Attendance Verification Details"
        subtitle={viewRecord ? `${viewRecord.employeeName} (${viewRecord.employeeId}) • ${viewRecord.date}` : ''}
      >
        {viewRecord && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div style={{ backgroundColor: '#f8fafc', padding: '10px 14px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: '0.72rem', color: '#64748b', fontWeight: '600' }}>CHECK-IN TIME</div>
                <div style={{ fontSize: '0.95rem', fontWeight: '700', color: '#0b3d2b', marginTop: '2px' }}>
                  {viewRecord.checkIn}
                </div>
              </div>
              <div style={{ backgroundColor: '#f8fafc', padding: '10px 14px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: '0.72rem', color: '#64748b', fontWeight: '600' }}>CHECK-OUT TIME</div>
                <div style={{ fontSize: '0.95rem', fontWeight: '700', color: '#0b3d2b', marginTop: '2px' }}>
                  {viewRecord.checkOut}
                </div>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div style={{ backgroundColor: '#f8fafc', padding: '10px 14px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: '0.72rem', color: '#64748b', fontWeight: '600' }}>STATUS & MODE</div>
                <div style={{ fontSize: '0.9rem', fontWeight: '700', color: '#0b3d2b', marginTop: '2px' }}>
                  {viewRecord.status} • {viewRecord.workMode}
                </div>
              </div>
              <div style={{ backgroundColor: '#f8fafc', padding: '10px 14px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: '0.72rem', color: '#64748b', fontWeight: '600' }}>DURATION</div>
                <div style={{ fontSize: '0.9rem', fontWeight: '700', color: '#0b3d2b', marginTop: '2px' }}>
                  {viewRecord.duration || '--'}
                </div>
              </div>
            </div>

            {/* Late Check-In Reason Section (Section 7) */}
            {(viewRecord.isLate || (viewRecord.status || '').toUpperCase() === 'LATE' || viewRecord.lateReason) && (
              <div
                style={{
                  backgroundColor: '#fffbeb',
                  border: '1px solid #fde68a',
                  padding: '12px 14px',
                  borderRadius: '12px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <AlertCircle size={16} color="#b45309" />
                    <span style={{ fontSize: '0.8rem', fontWeight: '700', color: '#92400e' }}>
                      LATE CHECK-IN (After 09:30 AM IST)
                    </span>
                  </div>
                  <span
                    style={{
                      fontSize: '0.72rem',
                      fontWeight: '700',
                      padding: '2px 8px',
                      borderRadius: '6px',
                      backgroundColor: viewRecord.lateReason ? '#ecfdf5' : '#fef2f2',
                      color: viewRecord.lateReason ? '#047857' : '#b91c1c',
                      border: `1px solid ${viewRecord.lateReason ? '#a7f3d0' : '#fecaca'}`,
                    }}
                  >
                    {viewRecord.lateReason ? 'Reason Submitted' : 'Reason Pending'}
                  </span>
                </div>
                {viewRecord.lateReason ? (
                  <div>
                    <div style={{ fontSize: '0.72rem', color: '#78350f', fontWeight: '600', marginBottom: '4px' }}>
                      Official Reason:
                    </div>
                    <p
                      style={{
                        fontSize: '0.85rem',
                        color: '#451a03',
                        margin: 0,
                        fontStyle: 'italic',
                        backgroundColor: '#ffffff',
                        padding: '8px 12px',
                        borderRadius: '8px',
                        border: '1px solid #fef3c7',
                        lineHeight: 1.4,
                      }}
                    >
                      "{viewRecord.lateReason}"
                    </p>
                    {viewRecord.lateReasonSubmittedAt && (
                      <div style={{ fontSize: '0.7rem', color: '#b45309', marginTop: '6px' }}>
                        Recorded at: {new Date(viewRecord.lateReasonSubmittedAt).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ fontSize: '0.8rem', color: '#b91c1c' }}>
                    No late check-in explanation has been submitted by the employee yet.
                  </div>
                )}
              </div>
            )}

            {/* GPS Location Details */}
            {viewRecord.checkInLatitude !== null && viewRecord.checkInLongitude !== null && (
              <div style={{ backgroundColor: '#f0fdfa', border: '1px solid #99f6e4', padding: '12px 14px', borderRadius: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: '700', color: '#0f766e' }}>
                    GPS Coordinates Captured:
                  </span>
                  <a
                    href={`https://www.google.com/maps?q=${viewRecord.checkInLatitude},${viewRecord.checkInLongitude}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ fontSize: '0.72rem', color: '#0d9488', fontWeight: '700', textDecoration: 'underline' }}
                  >
                    View on Maps &rarr;
                  </a>
                </div>
                <div style={{ fontSize: '0.85rem', fontWeight: '700', color: '#134e4a' }}>
                  {Number(viewRecord.checkInLatitude).toFixed(6)}°, {Number(viewRecord.checkInLongitude).toFixed(6)}°
                </div>
                {viewRecord.checkInLocationAccuracy && (
                  <div style={{ fontSize: '0.72rem', color: '#0d9488', marginTop: '2px' }}>
                    Location Accuracy: ±{Math.round(viewRecord.checkInLocationAccuracy)} meters
                  </div>
                )}
              </div>
            )}

            {/* Photo Section */}
            <div>
              <div style={{ fontSize: '0.8rem', fontWeight: '700', color: '#0b3d2b', marginBottom: '8px' }}>
                Captured Attendance Photo:
              </div>
              {isPhotoLoading ? (
                <div style={{ padding: '24px', textAlign: 'center', color: '#64748b', backgroundColor: '#f8fafc', borderRadius: '12px' }}>
                  Loading photo...
                </div>
              ) : viewPhotoUrl ? (
                <div style={{ width: '100%', maxHeight: '280px', borderRadius: '12px', overflow: 'hidden', backgroundColor: '#0f172a', display: 'flex', justifyContent: 'center' }}>
                  <img src={viewPhotoUrl} alt="Employee Check-in Selfie" style={{ maxHeight: '280px', maxWidth: '100%', objectFit: 'contain' }} />
                </div>
              ) : (
                <div style={{ padding: '20px', textAlign: 'center', color: '#94a3b8', backgroundColor: '#f8fafc', borderRadius: '12px', fontSize: '0.85rem' }}>
                  No photo stored for this entry.
                </div>
              )}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '8px' }}>
              <button
                type="button"
                className="btn-modal-cancel"
                onClick={() => setIsViewModalOpen(false)}
                style={{ width: 'auto', padding: '0 20px', height: '38px' }}
              >
                Close
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
