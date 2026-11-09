import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText,
  Search,
  Filter,
  Eye,
  Trash2,
  Plus,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import api from '../services/api';
import StatusBadge from '../components/StatusBadge';

const InvoiceList = () => {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [page, setPage] = useState(1);
  const pageSize = 6;

  const fetchInvoices = async () => {
    setLoading(true);
    setLoadError('');
    try {
      const response = await api.get('/invoices/');
      const data = response.data.results || response.data;
      setInvoices(Array.isArray(data) ? data : []);
    } catch (error) {
      setInvoices([]);
      setLoadError(error.response?.data?.detail || 'Could not load invoices.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInvoices();
  }, []);

  const handleValidate = async (id, e) => {
    e.stopPropagation();
    try {
      const res = await api.post(`/invoices/${id}/validate/`);
      setInvoices((prev) => prev.map((inv) => (inv.id === id ? res.data.invoice : inv)));
      if (res.data.validation?.passed) {
        toast.success(`Invoice #${id} validation passed.`);
      } else {
        toast.error(res.data.validation?.errors?.join(' ') || `Invoice #${id} failed validation.`);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || error.response?.data?.error || `Could not validate invoice #${id}.`);
    }
  };

  const handleSubmitForApproval = async (id, e) => {
    e.stopPropagation();
    try {
      await api.post(`/invoices/${id}/submit_for_approval/`);
      toast.success(`Invoice #${id} submitted for approval.`);
      await fetchInvoices();
    } catch (error) {
      toast.error(error.response?.data?.detail || error.response?.data?.error || `Could not submit invoice #${id}.`);
    }
  };

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete invoice record #${id}?`)) {
      return;
    }
    try {
      await api.delete(`/invoices/${id}/`);
      toast.success('Invoice deleted.');
      setInvoices((prev) => prev.filter((inv) => inv.id !== id));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Could not delete invoice.');
    }
  };

  // Filter and search logic
  const filtered = invoices.filter((inv) => {
    const matchesSearch =
      (inv.invoice_number || '').toLowerCase().includes(search.toLowerCase()) ||
      [inv.vendor_name, inv.vendor_details?.name]
        .filter(Boolean)
        .some((name) => name.toLowerCase().includes(search.toLowerCase()));

    const matchesStatus =
      statusFilter === 'all' || (inv.status || '').toLowerCase() === statusFilter.toLowerCase();

    return matchesSearch && matchesStatus;
  });

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const paginated = filtered.slice((page - 1) * pageSize, page * pageSize);

  const formatAmount = (val, currency = 'INR') => {
    if (!val) return '—';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: currency || 'INR',
    }).format(val);
  };

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1>Invoice Registry</h1>
          <p className="subtitle">
            Manage captured supplier invoices, run automated rule audits, and track approval states
          </p>
        </div>
        <div className="header-actions">
          <button onClick={fetchInvoices} className="btn btn-secondary" title="Refresh">
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <Link to="/upload" className="btn btn-primary">
            <Plus size={16} />
            Upload Invoice
          </Link>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div
        className="card"
        style={{
          padding: '1rem 1.25rem',
          marginBottom: '1.5rem',
          display: 'flex',
          gap: '1rem',
          alignItems: 'center',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ position: 'relative', flex: '1 1 240px' }}>
          <input
            type="text"
            placeholder="Search invoice number or vendor..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            style={{ paddingLeft: '2.4rem' }}
          />
          <Search
            size={18}
            style={{
              position: 'absolute',
              left: '0.85rem',
              top: '50%',
              transform: 'translateY(-50%)',
              color: '#64748b',
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: '0 0 auto' }}>
          <Filter size={16} color="#94a3b8" />
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            style={{ minWidth: '170px' }}
          >
            <option value="all">All Statuses</option>
            <option value="uploaded">Uploaded</option>
            <option value="extracted">OCR Extracted</option>
            <option value="validated">Validated</option>
            <option value="pending_approval">Pending Approval</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="paid">Paid</option>
          </select>
        </div>
      </div>

      {/* Table Section */}
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Invoice #</th>
              <th>Vendor</th>
              <th>Invoice Date</th>
              <th>Amount</th>
              <th>Status</th>
              <th>OCR Confidence</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loadError && (
              <tr><td colSpan={7} role="alert" style={{ textAlign: 'center', color: '#f87171' }}>{loadError}</td></tr>
            )}
            {loading ? (
              // Loading Skeleton
              [...Array(4)].map((_, i) => (
                <tr key={i}>
                  <td colSpan={7} style={{ padding: '1.25rem', textAlign: 'center' }}>
                    <div
                      style={{
                        height: '20px',
                        background: 'rgba(255, 255, 255, 0.05)',
                        borderRadius: '4px',
                        animation: 'pulse 1.5s infinite',
                      }}
                    />
                  </td>
                </tr>
              ))
            ) : paginated.length === 0 ? (
              // Empty State
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '3rem 1rem' }}>
                  <div
                    style={{
                      width: '48px',
                      height: '48px',
                      borderRadius: '50%',
                      background: 'rgba(99, 102, 241, 0.1)',
                      color: '#6366f1',
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      marginBottom: '1rem',
                    }}
                  >
                    <FileText size={24} />
                  </div>
                  <h4 style={{ color: '#f8fafc', fontWeight: 600, marginBottom: '0.35rem' }}>
                    No invoices found
                  </h4>
                  <p style={{ color: '#94a3b8', fontSize: '0.85rem', marginBottom: '1.25rem' }}>
                    Try adjusting your filters or upload a new invoice document
                  </p>
                  <Link to="/upload" className="btn btn-primary btn-sm">
                    <Plus size={15} /> Upload Invoice
                  </Link>
                </td>
              </tr>
            ) : (
              paginated.map((inv) => (
                <tr key={inv.id}>
                  <td>
                    <Link
                      to={`/invoices/${inv.id}`}
                      style={{
                        color: '#f8fafc',
                        fontWeight: 600,
                        textDecoration: 'none',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                      }}
                    >
                      <FileText size={16} color="#6366f1" />
                      {inv.invoice_number || `INV-DRAFT-${inv.id}`}
                    </Link>
                  </td>
                  <td>
                    <span style={{ fontWeight: 500 }}>
                      {inv.vendor_details?.name || inv.vendor_name || 'Pending Recognition'}
                    </span>
                  </td>
                  <td style={{ color: '#94a3b8' }}>
                    {inv.invoice_date || '—'}
                  </td>
                  <td style={{ fontWeight: 700, color: '#f8fafc' }}>
                    {formatAmount(inv.total_amount, inv.currency)}
                  </td>
                  <td>
                    <StatusBadge status={inv.status} />
                  </td>
                  <td>
                    {inv.ocr_confidence ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div
                          style={{
                            width: '50px',
                            height: '6px',
                            backgroundColor: '#0f172a',
                            borderRadius: '3px',
                            overflow: 'hidden',
                          }}
                        >
                          <div
                            style={{
                              width: `${inv.ocr_confidence}%`,
                              height: '100%',
                              backgroundColor:
                                inv.ocr_confidence >= 95
                                  ? '#22c55e'
                                  : inv.ocr_confidence >= 85
                                  ? '#f59e0b'
                                  : '#ef4444',
                            }}
                          />
                        </div>
                        <span style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
                          {inv.ocr_confidence}%
                        </span>
                      </div>
                    ) : (
                      <span style={{ color: '#64748b', fontSize: '0.8rem' }}>Pending</span>
                    )}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
                      <Link
                        to={`/invoices/${inv.id}`}
                        className="btn btn-secondary btn-sm"
                        title="View Details"
                      >
                        <Eye size={14} /> View
                      </Link>

                      {['uploaded', 'extracted'].includes(inv.status) && (
                        <button
                          onClick={(e) => handleValidate(inv.id, e)}
                          className="btn btn-success btn-sm"
                          title="Run Validation Rules"
                        >
                          <ShieldCheck size={14} /> Validate
                        </button>
                      )}

                      {inv.status === 'validated' && (
                        <button
                          onClick={(e) => handleSubmitForApproval(inv.id, e)}
                          className="btn btn-primary btn-sm"
                          title="Submit for approval"
                        >
                          Submit
                        </button>
                      )}

                      <button
                        onClick={(e) => handleDelete(inv.id, e)}
                        className="btn btn-ghost btn-sm btn-icon"
                        title="Delete Invoice"
                        style={{ color: '#ef4444' }}
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginTop: '1.25rem',
            padding: '0.5rem',
          }}
        >
          <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
            Showing page {page} of {totalPages} ({filtered.length} total invoices)
          </span>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="btn btn-secondary btn-sm"
            >
              <ChevronLeft size={16} /> Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="btn btn-secondary btn-sm"
            >
              Next <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default InvoiceList;
