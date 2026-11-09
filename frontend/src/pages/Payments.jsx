import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Plus,
  Filter,
  CheckCircle2,
  AlertTriangle,
  Clock,
  X,
  FileCheck,
  Send,
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import api from '../services/api';
import StatusBadge from '../components/StatusBadge';

const Payments = () => {
  const [searchParams] = useSearchParams();
  const preselectedInvoiceId = searchParams.get('invoiceId');

  const [payments, setPayments] = useState([]);
  const [approvedInvoices, setApprovedInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');

  // Modals
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [markPaidModal, setMarkPaidModal] = useState(null); // payment item

  // Form states
  const [newRequest, setNewRequest] = useState({
    invoice: preselectedInvoiceId || '',
    amount: '',
    payment_method: 'bank_transfer',
    due_date: '',
  });

  const [paidForm, setPaidForm] = useState({
    reference: '',
    bank_reference: '',
    paid_date: new Date().toISOString().split('T')[0],
  });

  const fetchPayments = async () => {
    setLoading(true);
    try {
      const [paymentsResponse, invoicesResponse] = await Promise.all([
        api.get('/payments/requests/'),
        api.get('/invoices/?status=approved'),
      ]);
      const paymentData = paymentsResponse.data.results || paymentsResponse.data;
      const allInvoices = invoicesResponse.data.results || invoicesResponse.data;
      const activePaymentInvoiceIds = new Set(
        paymentData
          .filter((payment) => !['cancelled', 'failed'].includes(payment.status))
          .map((payment) => String(payment.invoice))
      );
      const invoiceData = allInvoices.filter((invoice) => !activePaymentInvoiceIds.has(String(invoice.id)));
      setPayments(paymentData.map((payment) => ({
        ...payment,
        vendor: payment.vendor_name || payment.invoice_details?.effective_vendor_name || 'Unknown vendor',
      })));
      setApprovedInvoices(invoiceData);
      setNewRequest((current) => {
        const selectedInvoice = invoiceData.find(
          (invoice) => String(invoice.id) === String(current.invoice)
        ) || invoiceData[0];
        return {
          ...current,
          invoice: selectedInvoice ? String(selectedInvoice.id) : '',
          amount: selectedInvoice?.total_amount || '',
          due_date: selectedInvoice?.due_date || '',
        };
      });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Could not load payment requests.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPayments();
  }, []);

  const formatAmount = (val) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
    }).format(val);
  };

  const isOverdue = (dueDate, status) => {
    if (status === 'paid' || !dueDate) return false;
    const due = new Date(dueDate);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return due < today;
  };

  // Calculations
  const totalPending = payments
    .filter((p) => p.status === 'pending' || p.status === 'processing')
    .reduce((acc, curr) => acc + Number(curr.amount), 0);

  const totalPaid = payments
    .filter((p) => p.status === 'paid')
    .reduce((acc, curr) => acc + Number(curr.amount), 0);

  const overdueAmount = payments
    .filter((p) => isOverdue(p.due_date, p.status))
    .reduce((acc, curr) => acc + Number(curr.amount), 0);

  const handleCreatePayment = async (e) => {
    e.preventDefault();
    try {
      const response = await api.post('/payments/requests/', {
        ...newRequest,
        invoice: Number(newRequest.invoice),
        amount: Number(newRequest.amount),
      });
      toast.success(`Payment request ${response.data.id} created.`);
      setCreateModalOpen(false);
      await fetchPayments();
    } catch (error) {
      toast.error(
        error.response?.data?.detail ||
        error.response?.data?.invoice?.[0] ||
        'Could not create the payment request.'
      );
    }
  };

  const handleMarkPaid = async (e) => {
    e.preventDefault();
    if (!paidForm.reference.trim()) {
      toast.error('Transaction reference number is required.');
      return;
    }

    try {
      const response = await api.post(`/payments/requests/${markPaidModal.id}/mark_paid/`, {
        reference: paidForm.reference,
        bank_reference: paidForm.bank_reference,
        paid_at: paidForm.paid_date
          ? new Date(`${paidForm.paid_date}T12:00:00`).toISOString()
          : undefined,
      });
      toast.success(response.data.message || `Payment ${markPaidModal.reference} marked as paid.`);
      setMarkPaidModal(null);
      await fetchPayments();
    } catch (error) {
      toast.error(
        error.response?.data?.error ||
        error.response?.data?.detail ||
        'Could not record the payment.'
      );
    }
  };

  const filtered = payments.filter((p) => {
    if (statusFilter === 'all') return true;
    return (p.status || '').toLowerCase() === statusFilter.toLowerCase();
  });

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div>
          <h1>Payment Disbursement & Remittance</h1>
          <p className="subtitle">
            Authorize banking payment requests, reconcile early pay discounts, and issue remittance advices
          </p>
        </div>
        <div className="header-actions">
          <button onClick={() => setCreateModalOpen(true)} className="btn btn-primary">
            <Plus size={16} /> Create Payment Request
          </button>
        </div>
      </div>

      {/* 3 Summary Cards */}
      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}>
        <div className="stat-card">
          <div className="stat-top">
            <span className="stat-label">Total Pending Release</span>
            <div className="stat-icon-wrapper" style={{ backgroundColor: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24' }}>
              <Clock size={18} />
            </div>
          </div>
          <div className="stat-value" style={{ color: '#fbbf24' }}>
            {formatAmount(totalPending)}
          </div>
          <div className="stat-subtext">Awaiting banking batch cycle</div>
        </div>

        <div className="stat-card">
          <div className="stat-top">
            <span className="stat-label">Total Disbursed (Paid)</span>
            <div className="stat-icon-wrapper" style={{ backgroundColor: 'rgba(34, 197, 94, 0.15)', color: '#4ade80' }}>
              <CheckCircle2 size={18} />
            </div>
          </div>
          <div className="stat-value" style={{ color: '#4ade80' }}>
            {formatAmount(totalPaid)}
          </div>
          <div className="stat-subtext">Fully reconciled to ledger</div>
        </div>

        <div className="stat-card">
          <div className="stat-top">
            <span className="stat-label">Overdue Invoices</span>
            <div className="stat-icon-wrapper" style={{ backgroundColor: 'rgba(239, 68, 68, 0.15)', color: '#f87171' }}>
              <AlertTriangle size={18} />
            </div>
          </div>
          <div className="stat-value" style={{ color: '#f87171' }}>
            {formatAmount(overdueAmount)}
          </div>
          <div className="stat-subtext">Requires immediate clearance</div>
        </div>
      </div>

      {/* Filter Bar */}
      <div
        className="card"
        style={{
          padding: '1rem 1.25rem',
          marginBottom: '1.5rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Filter size={16} color="#94a3b8" />
          <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Filter by Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{ width: 'auto', minWidth: '160px' }}
          >
            <option value="all">All Transactions</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
            <option value="paid">Paid</option>
          </select>
        </div>
      </div>

      {/* Payment Requests Table */}
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Invoice #</th>
              <th>Vendor</th>
              <th>Amount</th>
              <th>Due Date</th>
              <th>Status</th>
              <th>Payment Method</th>
              <th>Reference #</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
          <tr><td colSpan={8} style={{ textAlign: 'center', padding: '2rem' }}>Loading payment requests...</td></tr>
            ) : filtered.length === 0 ? (
          <tr>
            <td colSpan={8} style={{ textAlign: 'center', padding: '2rem', color: '#94a3b8' }}>
              No payment requests found. Create one from an approved invoice.
            </td>
          </tr>
            ) : filtered.map((item) => {
              const overdue = isOverdue(item.due_date, item.status);
              return (
                <tr key={item.id}>
                  <td style={{ fontWeight: 600, color: '#f8fafc' }}>{item.invoice_number}</td>
                  <td>{item.vendor}</td>
                  <td style={{ fontWeight: 700, color: '#f8fafc' }}>
                    {formatAmount(item.amount)}
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <span style={{ color: overdue ? '#f87171' : '#cbd5e1' }}>
                        {item.due_date}
                      </span>
                      {overdue && (
                        <span className="badge badge-rejected" style={{ fontSize: '0.7rem' }}>
                          Overdue
                        </span>
                      )}
                    </div>
                  </td>
                  <td>
                    <StatusBadge status={item.status} />
                  </td>
                  <td style={{ color: '#cbd5e1' }}>{item.payment_method}</td>
                  <td>
                    <span style={{ fontFamily: 'monospace', color: '#94a3b8' }}>
                      {item.reference}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    {['pending', 'processing'].includes(item.status) ? (
                      <button
                        onClick={() => {
                          setMarkPaidModal(item);
                          setPaidForm({
                                reference: '',
                                bank_reference: '',
                            paid_date: new Date().toISOString().split('T')[0],
                          });
                        }}
                        className="btn btn-success btn-sm"
                      >
                        <FileCheck size={14} /> Mark as Paid
                      </button>
                    ) : item.status === 'paid' ? (
                      <span className="badge badge-paid">Settled</span>
                    ) : (
                      <StatusBadge status={item.status} />
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Modal: Create Payment Request */}
      {createModalOpen && (
        <div className="modal-overlay" onClick={() => setCreateModalOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Create Payment Request</h3>
              <button onClick={() => setCreateModalOpen(false)} className="btn btn-ghost btn-sm btn-icon">
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleCreatePayment}>
              <div className="modal-body">
                <div className="form-group">
                  <label>Approved Invoice</label>
                  <select
                    required
                    value={newRequest.invoice}
                    onChange={(e) => {
                      const invoice = approvedInvoices.find((item) => item.id === Number(e.target.value));
                      setNewRequest({
                        ...newRequest,
                        invoice: e.target.value,
                        amount: invoice?.total_amount || '',
                        due_date: invoice?.due_date || '',
                      });
                    }}
                  >
                    <option value="">Select an approved invoice</option>
                    {approvedInvoices.map((invoice) => (
                      <option key={invoice.id} value={invoice.id}>
                        {invoice.invoice_number} — {invoice.effective_vendor_name} ({formatAmount(invoice.total_amount)})
                      </option>
                    ))}
                  </select>
                  {approvedInvoices.length === 0 && (
                    <small>No approved invoices are available for payment.</small>
                  )}
                </div>
                <div className="form-group">
                  <label>Authorized Amount (INR)</label>
                  <input
                    type="number"
                    required
                    readOnly
                    value={newRequest.amount}
                  />
                </div>
                <div className="form-group">
                  <label>Payment Method</label>
                  <select
                    value={newRequest.payment_method}
                    onChange={(e) => setNewRequest({ ...newRequest, payment_method: e.target.value })}
                  >
                    <option value="bank_transfer">Bank Transfer</option>
                    <option value="cheque">Cheque</option>
                    <option value="upi">UPI</option>
                    <option value="neft">NEFT</option>
                    <option value="rtgs">RTGS</option>
                    <option value="imps">IMPS</option>
                  </select>
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label>Scheduled Due Date</label>
                  <input
                    type="date"
                    required
                    value={newRequest.due_date}
                    onChange={(e) => setNewRequest({ ...newRequest, due_date: e.target.value })}
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" onClick={() => setCreateModalOpen(false)} className="btn btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={approvedInvoices.length === 0}>
                  <Send size={15} /> Submit Request
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Mark as Paid */}
      {markPaidModal && (
        <div className="modal-overlay" onClick={() => setMarkPaidModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Record Bank Payment Clearance</h3>
              <button onClick={() => setMarkPaidModal(null)} className="btn btn-ghost btn-sm btn-icon">
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleMarkPaid}>
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
                  <p style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
                    Invoice: <strong style={{ color: '#f8fafc' }}>{markPaidModal.invoice_number}</strong>
                  </p>
                  <p style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
                    Payee: <strong style={{ color: '#f8fafc' }}>{markPaidModal.vendor}</strong>
                  </p>
                  <p style={{ fontSize: '1.05rem', fontWeight: 700, color: '#4ade80', marginTop: '0.25rem' }}>
                    Disbursement: {formatAmount(markPaidModal.amount)}
                  </p>
                </div>

                <div className="form-group">
                  <label>Bank Transaction UTR / Reference *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. UTR-9928172645"
                    value={paidForm.reference}
                    onChange={(e) => setPaidForm({ ...paidForm, reference: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label>Disbursement Bank Gateway</label>
                  <input
                    type="text"
                    placeholder="HDFC Corporate NetBanking"
                    value={paidForm.bank_reference}
                    onChange={(e) => setPaidForm({ ...paidForm, bank_reference: e.target.value })}
                  />
                </div>

                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label>Settlement Date</label>
                  <input
                    type="date"
                    value={paidForm.paid_date}
                    onChange={(e) => setPaidForm({ ...paidForm, paid_date: e.target.value })}
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" onClick={() => setMarkPaidModal(null)} className="btn btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn btn-success">
                  <CheckCircle2 size={15} /> Confirm Settlement
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Payments;
