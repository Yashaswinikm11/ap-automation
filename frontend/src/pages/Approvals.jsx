import { useEffect, useState } from 'react';
import {
  CheckCircle,
  Clock,
  Shield,
  Layers,
  Check,
  X,
  FileText,
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import api from '../services/api';
import StatusBadge from '../components/StatusBadge';

const Approvals = () => {
  const [tab, setTab] = useState('pending'); // 'pending' or 'all'
  const [pendingList, setPendingList] = useState([]);
  const [allList, setAllList] = useState([]);
  const [approvalMatrices, setApprovalMatrices] = useState([]);
  const [loading, setLoading] = useState(true);

  // Modals state
  const [activeModal, setActiveModal] = useState(null); // { type: 'approve' | 'reject', item: obj }
  const [comments, setComments] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const fetchApprovalRequests = async () => {
    setLoading(true);
    try {
      const [allResponse, pendingResponse, matrixResponse] = await Promise.all([
        api.get('/approvals/requests/'),
        api.get('/approvals/requests/pending_for_me/'),
        api.get('/approvals/matrices/'),
      ]);
      const requests = allResponse.data.results || allResponse.data;
      const pendingRequests = pendingResponse.data.results || pendingResponse.data;
      const mapRequest = (request) => ({
        ...request,
        vendor: request.vendor_name || 'Unknown vendor',
        amount: Number(request.invoice_amount || 0),
        submitted_by: request.submitted_by_username || 'System',
        days_pending: request.submitted_at
          ? Math.max(0, Math.floor((Date.now() - new Date(request.submitted_at).getTime()) / 86400000))
          : 0,
      });
      setAllList(requests.map(mapRequest));
      setPendingList(pendingRequests.map(mapRequest));
      setApprovalMatrices(matrixResponse.data.results || matrixResponse.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Could not load approval requests.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovalRequests();
  }, []);

  const handleOpenApprove = (item) => {
    setActiveModal({ type: 'approve', item });
    setComments('');
  };

  const handleOpenReject = (item) => {
    setActiveModal({ type: 'reject', item });
    setComments('');
  };

  const closeModal = () => {
    setActiveModal(null);
    setComments('');
  };

  const handleConfirmAction = async () => {
    if (activeModal.type === 'reject' && !comments.trim()) {
      toast.error('Rejection reason is required.');
      return;
    }

    setActionLoading(true);
    const { type, item } = activeModal;

    try {
      const response = await api.post(`/approvals/requests/${item.id}/${type}/`, {
        decision: type,
        comments,
      });
      toast.success(response.data.message || `Invoice ${item.invoice_number} ${type}d.`);
      await fetchApprovalRequests();
      closeModal();
    } catch (error) {
      toast.error(
        error.response?.data?.error ||
        error.response?.data?.detail ||
        `Could not ${type} invoice ${item.invoice_number}.`
      );
    } finally {
      setActionLoading(false);
    }
  };

  const formatAmount = (val) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
    }).format(val);
  };

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div>
          <h1>Approval Workflow Management</h1>
          <p className="subtitle">
            Authorize or reject validated invoices based on enterprise delegation of authority thresholds
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs-nav">
        <button
          onClick={() => setTab('pending')}
          className={`tab-btn ${tab === 'pending' ? 'active' : ''}`}
        >
          <Clock size={16} style={{ display: 'inline', marginRight: '6px' }} />
          Pending Approvals ({pendingList.length})
        </button>
        <button
          onClick={() => setTab('all')}
          className={`tab-btn ${tab === 'all' ? 'active' : ''}`}
        >
          <Layers size={16} style={{ display: 'inline', marginRight: '6px' }} />
          All Historical Requests ({allList.length})
        </button>
      </div>

      {/* Pending Tab */}
      {tab === 'pending' && (
        <div className="card" style={{ marginBottom: '2rem' }}>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Invoice #</th>
                  <th>Vendor</th>
                  <th>Amount</th>
                  <th>Submitted By</th>
                  <th>Days Pending</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={6} style={{ textAlign: 'center', padding: '2rem' }}>Loading approval requests...</td></tr>
                ) : pendingList.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '3rem 1rem', color: '#94a3b8' }}>
                      <CheckCircle size={32} color="#22c55e" style={{ margin: '0 auto 0.5rem auto' }} />
                      <p style={{ fontWeight: 600, color: '#f8fafc' }}>All Caught Up!</p>
                      <p style={{ fontSize: '0.85rem' }}>No invoices are currently awaiting your signature.</p>
                    </td>
                  </tr>
                ) : (
                  pendingList.map((item) => (
                    <tr key={item.id}>
                      <td style={{ fontWeight: 600, color: '#f8fafc' }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <FileText size={15} color="#6366f1" />
                          {item.invoice_number}
                        </span>
                      </td>
                      <td>{item.vendor}</td>
                      <td style={{ fontWeight: 700, color: '#f8fafc' }}>
                        {formatAmount(item.amount)}
                      </td>
                      <td style={{ color: '#cbd5e1' }}>{item.submitted_by}</td>
                      <td>
                        <span
                          className={`badge ${item.escalate_after_days && item.days_pending >= item.escalate_after_days ? 'badge-rejected' : 'badge-pending'}`}
                        >
                          {item.days_pending} {item.days_pending === 1 ? 'day' : 'days'}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: '0.5rem' }}>
                          <button
                            onClick={() => handleOpenApprove(item)}
                            className="btn btn-success btn-sm"
                          >
                            <Check size={14} /> Approve
                          </button>
                          <button
                            onClick={() => handleOpenReject(item)}
                            className="btn btn-danger btn-sm"
                          >
                            <X size={14} /> Reject
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* All Tab */}
      {tab === 'all' && (
        <div className="card" style={{ marginBottom: '2rem' }}>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Invoice #</th>
                  <th>Vendor</th>
                  <th>Amount</th>
                  <th>Submitted By</th>
                  <th>Workflow Step</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={6} style={{ textAlign: 'center', padding: '2rem' }}>Loading approval requests...</td></tr>
                ) : allList.length === 0 ? (
                  <tr><td colSpan={6} style={{ textAlign: 'center', padding: '2rem 1rem', color: '#94a3b8' }}>No approval requests yet.</td></tr>
                ) : allList.map((item) => (
                  <tr key={item.id}>
                    <td style={{ fontWeight: 600, color: '#f8fafc' }}>{item.invoice_number}</td>
                    <td>{item.vendor}</td>
                    <td style={{ fontWeight: 700 }}>{formatAmount(item.amount)}</td>
                    <td style={{ color: '#cbd5e1' }}>{item.submitted_by}</td>
                    <td>Step {item.current_step}</td>
                    <td>
                      <StatusBadge status={item.status || 'pending_approval'} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Approval Matrix Configuration Table */}
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">
              <Shield size={18} color="#6366f1" />
              Corporate Approval Matrix Policy
            </h3>
            <p className="card-subtitle">
              Configured authorization tiers, roles, and SLA escalation thresholds
            </p>
          </div>
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Authorization Tier</th>
                <th>Min Spend</th>
                <th>Max Spend</th>
                <th>Mandated Approver Role</th>
                <th>Escalation Threshold</th>
              </tr>
            </thead>
            <tbody>
              {approvalMatrices.length === 0 ? (
                <tr><td colSpan={5} style={{ textAlign: 'center', color: '#94a3b8' }}>No approval matrices are configured.</td></tr>
              ) : approvalMatrices.flatMap((matrix) => (matrix.steps || []).map((step) => (
                <tr key={`${matrix.id}-${step.id}`}>
                  <td style={{ fontWeight: 600, color: '#f8fafc' }}>{matrix.name}</td>
                  <td>{formatAmount(Number(matrix.min_amount || 0))}</td>
                  <td>{matrix.max_amount == null ? 'No upper limit' : formatAmount(Number(matrix.max_amount))}</td>
                  <td style={{ color: '#a5b4fc', fontWeight: 500 }}>
                    {step.approver_role}{step.is_parallel ? ' (parallel; all active role holders must approve)' : ''}
                  </td>
                  <td>{step.escalate_after_days} days</td>
                </tr>
              )))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal for Approve / Reject */}
      {activeModal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>
                {activeModal.type === 'approve' ? 'Approve Invoice' : 'Reject Invoice'}
              </h3>
              <button onClick={closeModal} className="btn btn-ghost btn-sm btn-icon">
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              <div
                style={{
                  padding: '0.85rem 1rem',
                  backgroundColor: 'rgba(15, 23, 42, 0.5)',
                  borderRadius: 'var(--radius-md)',
                  marginBottom: '1.25rem',
                  border: '1px solid var(--card-border)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                  <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>Invoice:</span>
                  <strong style={{ color: '#f8fafc' }}>{activeModal.item.invoice_number}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                  <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>Vendor:</span>
                  <strong style={{ color: '#f8fafc' }}>{activeModal.item.vendor}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>Amount:</span>
                  <strong style={{ color: '#22c55e', fontSize: '1.05rem' }}>
                    {formatAmount(activeModal.item.amount)}
                  </strong>
                </div>
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label>
                  {activeModal.type === 'approve'
                    ? 'Comments / Approval Notes (Optional)'
                    : 'Rejection Reason (Required)'}
                </label>
                <textarea
                  rows={4}
                  placeholder={
                    activeModal.type === 'approve'
                      ? 'Add any audit notes or GL coding confirmations...'
                      : 'State clear justification for rejecting this invoice request...'
                  }
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  autoFocus
                />
              </div>
            </div>

            <div className="modal-footer">
              <button type="button" onClick={closeModal} className="btn btn-secondary">
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmAction}
                disabled={actionLoading}
                className={`btn ${activeModal.type === 'approve' ? 'btn-success' : 'btn-danger'}`}
              >
                {activeModal.type === 'approve' ? 'Confirm Approval' : 'Confirm Rejection'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Approvals;
