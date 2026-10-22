import React, { useState, useEffect } from 'react';
import { UserCheck, Check, X, ShieldAlert, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import PageHeader from '../../components/common/PageHeader';
import EmptyState from '../../components/common/EmptyState';
import Modal from '../../components/common/Modal';
import { registrationRequestService } from '../../services/registrationRequestService';
import { subscribeToPendingEmployees } from '../../firebase/firestore';

export default function AdminRegistrationRequests() {
  const [requests, setRequests] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const [activeTab, setActiveTab] = useState('PENDING'); // Default to PENDING as required
  const [notification, setNotification] = useState('');
  const [processingId, setProcessingId] = useState(null);

  // Rejection Modal State
  const [rejectingItem, setRejectingItem] = useState(null);
  const [rejectionReason, setRejectionReason] = useState('');

  const fetchRequests = async () => {
    try {
      setIsLoading(true);
      setErrorMessage('');
      const data = await registrationRequestService.getRegistrationRequests();
      setRequests(Array.isArray(data) ? data : []);
    } catch (err) {
      setErrorMessage(err.message || 'Failed to fetch registration requests');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
    let unsubscribe = () => {};
    try {
      unsubscribe = subscribeToPendingEmployees(() => {
        fetchRequests();
      });
    } catch {
      // Fallback to fetchRequests
    }
    return () => {
      if (typeof unsubscribe === 'function') {
        unsubscribe();
      }
    };
  }, []);

  const handleApprove = async (req) => {
    if (processingId) return; // Prevent double-clicks
    try {
      setProcessingId(req.id);
      setErrorMessage('');
      await registrationRequestService.approveRequest(req.id);
      setNotification(`Application for ${req.name} (${req.employeeId}) was approved successfully. Employee account is now active.`);
      setTimeout(() => setNotification(''), 5000);
      await fetchRequests();
    } catch (err) {
      setErrorMessage(err.message || 'Failed to approve registration request');
    } finally {
      setProcessingId(null);
    }
  };

  const openRejectModal = (req) => {
    setRejectingItem(req);
    setRejectionReason('Registration does not meet company onboarding requirements.');
  };

  const handleConfirmReject = async (e) => {
    e.preventDefault();
    if (!rejectingItem || processingId) return;

    try {
      setProcessingId(rejectingItem.id);
      setErrorMessage('');
      await registrationRequestService.rejectRequest(rejectingItem.id, rejectionReason.trim());
      setNotification(`Application for ${rejectingItem.name} (${rejectingItem.employeeId}) was rejected.`);
      setTimeout(() => setNotification(''), 5000);
      setRejectingItem(null);
      await fetchRequests();
    } catch (err) {
      setErrorMessage(err.message || 'Failed to reject registration request');
    } finally {
      setProcessingId(null);
    }
  };

  const pendingCount = requests.filter((r) => r.status === 'Pending').length;
  const processedCount = requests.filter((r) => r.status !== 'Pending').length;

  const filtered = requests.filter((r) => {
    if (activeTab === 'PENDING') return r.status === 'Pending';
    if (activeTab === 'PROCESSED') return r.status !== 'Pending';
    return true;
  });

  return (
    <div className="registration-requests-view animate-fade-in">
      <PageHeader
        title="Employee Registration Requests"
        subtitle="Review, authorize, or decline employee account registration applications"
        breadcrumb={[{ label: 'Admin', path: '/admin/dashboard' }, { label: 'Registration Requests' }]}
      />

      {notification && (
        <div
          style={{
            backgroundColor: '#ecfdf5',
            border: '1px solid #a7f3d0',
            color: '#065f46',
            padding: '12px 16px',
            borderRadius: '12px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '0.88rem',
            fontWeight: '600',
          }}
        >
          <CheckCircle2 size={16} />
          <span>{notification}</span>
        </div>
      )}

      {errorMessage && (
        <div
          style={{
            backgroundColor: '#fef2f2',
            border: '1px solid #fecaca',
            color: '#b91c1c',
            padding: '12px 16px',
            borderRadius: '12px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '0.88rem',
          }}
        >
          <AlertCircle size={16} />
          <span>{errorMessage}</span>
        </div>
      )}

      <div className="management-page-card">
        {/* Tabs */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', borderBottom: '1px solid #f1f5f9', paddingBottom: '12px' }}>
          {[
            { id: 'PENDING', label: `Pending Approval (${pendingCount})` },
            { id: 'PROCESSED', label: `Processed (${processedCount})` },
            { id: 'ALL', label: `All Requests (${requests.length})` },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '6px 14px',
                borderRadius: '8px',
                fontSize: '0.85rem',
                fontWeight: activeTab === tab.id ? '700' : '600',
                border: 'none',
                cursor: 'pointer',
                backgroundColor: activeTab === tab.id ? '#0b3d2b' : '#f8fafc',
                color: activeTab === tab.id ? '#ffffff' : '#64748b',
                transition: 'all 0.15s ease',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {isLoading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
            <Loader2 size={24} className="animate-spin" style={{ margin: '0 auto 8px auto' }} />
            <p style={{ fontSize: '0.875rem' }}>Loading registration requests...</p>
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            title="No registration requests found"
            description={
              activeTab === 'PENDING'
                ? 'There are currently no new employee registration requests awaiting approval.'
                : 'No registration requests match the selected view.'
            }
          />
        ) : (
          <div className="table-responsive-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Applicant</th>
                  <th>Employee Code</th>
                  <th>Phone</th>
                  <th>Request Date</th>
                  <th>Status</th>
                  <th>Decision / Audit</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((req) => (
                  <tr key={req.id}>
                    <td>
                      <div style={{ fontWeight: '700', color: '#0b3d2b' }}>{req.name}</div>
                      <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{req.email}</div>
                    </td>
                    <td>
                      <span style={{ fontWeight: '600', color: '#1e293b' }}>{req.employeeId}</span>
                    </td>
                    <td>{req.phone || '--'}</td>
                    <td>{req.requestedDate}</td>
                    <td>
                      <span
                        className={`badge-status ${req.status === 'Pending'
                            ? 'badge-pending'
                            : req.status === 'Approved'
                              ? 'badge-approved'
                              : 'badge-rejected'
                          }`}
                      >
                        {req.status}
                      </span>
                    </td>
                    <td>
                      {req.status === 'Pending' ? (
                        <span style={{ fontSize: '0.78rem', color: '#d97706', fontWeight: '500' }}>
                          Awaiting Review
                        </span>
                      ) : req.status === 'Approved' ? (
                        <div style={{ fontSize: '0.75rem', color: '#059669' }}>
                          <div>Approved by {req.reviewedBy || 'Admin'}</div>
                          {req.reviewedAt && (
                            <div style={{ color: '#64748b' }}>{new Date(req.reviewedAt).toLocaleDateString()}</div>
                          )}
                        </div>
                      ) : (
                        <div style={{ fontSize: '0.75rem', color: '#dc2626' }}>
                          <div>Rejected by {req.reviewedBy || 'Admin'}</div>
                          {req.rejectionReason && (
                            <div style={{ color: '#64748b', maxWidth: '200px' }}>Reason: {req.rejectionReason}</div>
                          )}
                        </div>
                      )}
                    </td>
                    <td>
                      {req.status === 'Pending' ? (
                        <div style={{ display: 'flex', gap: '6px' }}>
                          <button
                            type="button"
                            className="table-action-btn btn-approve"
                            onClick={() => handleApprove(req)}
                            disabled={processingId === req.id}
                            title="Authorize employee registration"
                          >
                            {processingId === req.id ? (
                              <Loader2 size={14} className="animate-spin" />
                            ) : (
                              <Check size={14} />
                            )}
                            <span>Approve</span>
                          </button>
                          <button
                            type="button"
                            className="table-action-btn btn-reject"
                            onClick={() => openRejectModal(req)}
                            disabled={processingId === req.id}
                            title="Decline registration request"
                          >
                            <X size={14} />
                            <span>Reject</span>
                          </button>
                        </div>
                      ) : (
                        <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                          Decided
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Reject Modal */}
      <Modal
        isOpen={!!rejectingItem}
        onClose={() => setRejectingItem(null)}
        title="Reject Registration Request"
        subtitle={`Decline onboarding request for ${rejectingItem?.name} (${rejectingItem?.employeeId})`}
      >
        <form onSubmit={handleConfirmReject}>
          <div className="form-group" style={{ marginBottom: '16px' }}>
            <label className="form-label" style={{ fontWeight: '600', marginBottom: '6px', display: 'block' }}>
              Rejection Reason
            </label>
            <textarea
              required
              rows={3}
              className="form-input-auth"
              style={{ width: '100%', resize: 'vertical', padding: '10px 12px' }}
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder="State reason for rejecting this registration application..."
            />
          </div>

          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '24px' }}>
            <button
              type="button"
              className="btn-secondary-gray"
              onClick={() => setRejectingItem(null)}
              disabled={!!processingId}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="table-action-btn btn-reject"
              style={{ padding: '8px 18px', height: 'auto', borderRadius: '8px' }}
              disabled={!!processingId}
            >
              {processingId ? <Loader2 size={16} className="animate-spin" /> : <X size={16} />}
              <span>Confirm Rejection</span>
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
