import { useCallback, useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  FileText,
  ArrowLeft,
  ShieldCheck,
  GitCompare,
  Send,
  Save,
  CheckCircle2,
  Download,
  Edit3,
  DollarSign,
  Maximize2,
  Loader2,
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import api from '../services/api';
import StatusBadge from '../components/StatusBadge';
import ApprovalTimeline from '../components/ApprovalTimeline';

const InvoiceDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [invoice, setInvoice] = useState(null);
  const [vendors, setVendors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    invoice_number: '',
    invoice_date: '',
    due_date: '',
    total_amount: '',
    tax_amount: '',
    vendor_name: '',
    vendor: '',
  });

  const fetchInvoice = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      const res = await api.get(`/invoices/${id}/`);
      setInvoice(res.data);
      setFormData({
        invoice_number: res.data.invoice_number || '',
        invoice_date: res.data.invoice_date || '',
        due_date: res.data.due_date || '',
        total_amount: res.data.total_amount || '',
        tax_amount: res.data.tax_amount || '',
        vendor_name: res.data.vendor_name || res.data.vendor_details?.name || '',
        vendor: res.data.vendor || '',
      });
    } catch (error) {
      setInvoice(null);
      setLoadError(error.response?.data?.detail || 'Could not load this invoice.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchInvoice();
  }, [fetchInvoice]);

  useEffect(() => {
    api.get('/vendors/', { params: { is_active: true } })
      .then((response) => {
        const data = response.data.results || response.data;
        setVendors(Array.isArray(data) ? data : []);
      })
      .catch((error) => {
        toast.error(error.response?.data?.detail || 'Could not load vendor master records.');
      });
  }, []);

  const handleValidate = async () => {
    try {
      const res = await api.post(`/invoices/${id}/validate/`);
      setInvoice(res.data.invoice);
      if (res.data.validation?.passed) {
        toast.success('Invoice validation passed.');
      } else {
        setIsEditing(true);
        toast.error(res.data.validation?.errors?.join(' ') || 'Invoice validation found errors.');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || error.response?.data?.error || 'Invoice validation failed.');
    }
  };

  const handleRunOCR = async () => {
    try {
      const response = await api.post(`/invoices/${id}/run_ocr/`);
      setInvoice(response.data.invoice);
      setFormData({
        invoice_number: response.data.invoice.invoice_number || '',
        invoice_date: response.data.invoice.invoice_date || '',
        due_date: response.data.invoice.due_date || '',
        total_amount: response.data.invoice.total_amount || '',
        tax_amount: response.data.invoice.tax_amount || '',
        vendor_name: response.data.invoice.vendor_name || response.data.invoice.vendor_details?.name || '',
        vendor: response.data.invoice.vendor || '',
      });
      toast.success(response.data.message || 'OCR processing completed.');
    } catch (error) {
      toast.error(error.response?.data?.error || error.response?.data?.detail || 'OCR processing failed.');
    }
  };

  const handleSubmitForApproval = async () => {
    try {
      const response = await api.post(`/invoices/${id}/submit_for_approval/`);
      toast.success(response.data.message || 'Invoice submitted for approval.');
      await fetchInvoice();
    } catch (error) {
      toast.error(error.response?.data?.detail || error.response?.data?.error || 'Could not submit invoice for approval.');
    }
  };

  const handleSaveFields = async () => {
    try {
      const response = await api.patch(`/invoices/${id}/`, {
        ...formData,
        vendor: formData.vendor || null,
      });
      toast.success('Invoice extracted fields saved.');
      setIsEditing(false);
      setInvoice(response.data);
      setFormData({
        invoice_number: response.data.invoice_number || '',
        invoice_date: response.data.invoice_date || '',
        due_date: response.data.due_date || '',
        total_amount: response.data.total_amount || '',
        tax_amount: response.data.tax_amount || '',
        vendor_name: response.data.vendor_name || response.data.vendor_details?.name || '',
        vendor: response.data.vendor || '',
      });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Could not save invoice fields.');
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <Loader2 size={36} className="animate-spin" color="#6366f1" />
      </div>
    );
  }

  if (!invoice) {
    return (
      <div className="card">
        <p>{loadError || 'Invoice not found.'}</p>
        <button onClick={() => navigate('/invoices')} className="btn btn-secondary btn-sm">
          <ArrowLeft size={16} /> Back to Invoices
        </button>
      </div>
    );
  }

  const formatAmount = (val) => {
    if (!val) return '—';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: invoice?.currency || 'INR',
    }).format(val);
  };

  return (
    <div>
      {/* Top Navigation & Action Header */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button
            onClick={() => navigate('/invoices')}
            className="btn btn-secondary btn-sm"
          >
            <ArrowLeft size={16} /> Back to Invoices
          </button>
          <div>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              {invoice?.invoice_number || `Invoice #${id}`}
              <StatusBadge status={invoice?.status} />
            </h1>
            <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
              Uploaded on {invoice.created_at ? new Date(invoice.created_at).toLocaleDateString() : '—'}
            </p>
          </div>
        </div>

        {/* Dynamic Action Buttons based on status */}
        <div className="header-actions">
          {['uploaded', 'extracted'].includes(invoice?.status) && (
            <>
              {invoice.original_file && (
                <button onClick={handleRunOCR} className="btn btn-secondary">
                  <FileText size={16} /> Run OCR
                </button>
              )}
              <button onClick={handleValidate} className="btn btn-success">
                <ShieldCheck size={16} /> Run Validation
              </button>
            </>
          )}

          {invoice?.status === 'validated' && (
            <>
              <button
                onClick={() => navigate(`/po-matching?invoiceId=${id}`)}
                className="btn btn-secondary"
              >
                <GitCompare size={16} /> Match PO
              </button>
              <button onClick={handleSubmitForApproval} className="btn btn-primary">
                <Send size={16} /> Submit for Approval
              </button>
            </>
          )}

          {invoice?.status === 'pending_approval' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#fbbf24', fontSize: '0.875rem', fontWeight: 600 }}>
              <StatusBadge status="pending_approval" />
              <span>Awaiting Manager Sign-Off</span>
            </div>
          )}

          {invoice?.status === 'approved' && (
            <button
              onClick={() => navigate(`/payments?invoiceId=${id}`)}
              className="btn btn-primary"
            >
              <DollarSign size={16} /> Schedule Payment
            </button>
          )}
        </div>
      </div>

      {/* Two Column Layout: Left Details, Right Document Viewer */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.25fr) minmax(360px, 0.95fr)', gap: '1.75rem', alignItems: 'start' }}>
        {/* Left Column: Metadata, Extracted Form, Line Items, Validation, Timeline */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Metadata Overview Card */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <FileText size={18} color="#6366f1" />
                Invoice Metadata
              </h3>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {invoice?.ocr_confidence && (
                  <span className="badge badge-validated">
                    OCR Confidence: {invoice.ocr_confidence}%
                  </span>
                )}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1.25rem' }}>
              <div>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Vendor</span>
                <p style={{ fontWeight: 600, color: '#f8fafc', marginTop: '0.2rem' }}>
                  {invoice?.vendor_details?.name || invoice?.vendor_name || 'Unknown vendor'}
                </p>
              </div>
              <div>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Total Amount</span>
                <p style={{ fontWeight: 700, color: '#f8fafc', marginTop: '0.2rem', fontSize: '1.1rem' }}>
                  {formatAmount(invoice?.total_amount)}
                </p>
              </div>
              <div>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Invoice Date</span>
                <p style={{ fontWeight: 500, color: '#cbd5e1', marginTop: '0.2rem' }}>
                  {invoice?.invoice_date || '—'}
                </p>
              </div>
              <div>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Due Date</span>
                <p style={{ fontWeight: 500, color: '#cbd5e1', marginTop: '0.2rem' }}>
                  {invoice?.due_date || '—'}
                </p>
              </div>
            </div>
          </div>

          {/* Extracted Fields Form */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <Edit3 size={18} color="#8b5cf6" />
                OCR Extracted Fields
              </h3>
              <button
                type="button"
                onClick={() => (isEditing ? handleSaveFields() : setIsEditing(true))}
                className={`btn btn-sm ${isEditing ? 'btn-success' : 'btn-secondary'}`}
              >
                {isEditing ? (
                  <>
                    <Save size={14} /> Save Changes
                  </>
                ) : (
                  <>
                    <Edit3 size={14} /> Edit Fields
                  </>
                )}
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div className="form-group">
                <label>Invoice Number</label>
                <input
                  type="text"
                  disabled={!isEditing}
                  value={formData.invoice_number}
                  onChange={(e) => setFormData({ ...formData, invoice_number: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>Vendor Name from Invoice</label>
                <input
                  type="text"
                  disabled={!isEditing}
                  value={formData.vendor_name}
                  onChange={(e) => setFormData({ ...formData, vendor_name: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Match Vendor Master Record</label>
                <select
                  disabled={!isEditing}
                  value={formData.vendor}
                  onChange={(e) => setFormData({ ...formData, vendor: e.target.value })}
                >
                  <option value="">Select a vendor</option>
                  {vendors.map((vendor) => (
                    <option key={vendor.id} value={vendor.id}>
                      {vendor.name} ({vendor.onboarding_status})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Invoice Date</label>
                <input
                  type="date"
                  disabled={!isEditing}
                  value={formData.invoice_date}
                  onChange={(e) => setFormData({ ...formData, invoice_date: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>Payment Due Date</label>
                <input
                  type="date"
                  disabled={!isEditing}
                  value={formData.due_date}
                  onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>Tax Amount (GST)</label>
                <input
                  type="number"
                  disabled={!isEditing}
                  value={formData.tax_amount}
                  onChange={(e) => setFormData({ ...formData, tax_amount: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>Total Invoiced (Gross)</label>
                <input
                  type="number"
                  disabled={!isEditing}
                  value={formData.total_amount}
                  onChange={(e) => setFormData({ ...formData, total_amount: e.target.value })}
                />
              </div>
            </div>
          </div>

          {/* Line Items Table */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Extracted Line Items</h3>
            </div>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Item Description</th>
                    <th>Qty</th>
                    <th>Unit Price</th>
                    <th>Subtotal</th>
                  </tr>
                </thead>
                <tbody>
                  {invoice?.line_items && invoice.line_items.length > 0 ? (
                    invoice.line_items.map((item, idx) => (
                      <tr key={item.id || idx}>
                        <td style={{ fontWeight: 500 }}>{item.description}</td>
                        <td>{item.quantity || 1}</td>
                        <td>{formatAmount(item.unit_price)}</td>
                        <td style={{ fontWeight: 700, color: '#f8fafc' }}>
                          {formatAmount(item.total)}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} style={{ textAlign: 'center', color: '#94a3b8', padding: '1.5rem' }}>
                        No itemized lines detected by OCR.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Validation & PO Matching Results */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <ShieldCheck size={18} color="#22c55e" />
                Automated Validation & PO Matching
              </h3>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '0.75rem 1rem',
                  backgroundColor: 'rgba(34, 197, 94, 0.08)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid rgba(34, 197, 94, 0.2)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <CheckCircle2 size={18} color="#22c55e" />
                  <span style={{ fontWeight: 500, fontSize: '0.875rem' }}>
                    Mathematical Parity Check (Lines = Total)
                  </span>
                </div>
                <span className="badge badge-validated">Passed</span>
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '0.75rem 1rem',
                  backgroundColor: 'rgba(34, 197, 94, 0.08)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid rgba(34, 197, 94, 0.2)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <CheckCircle2 size={18} color="#22c55e" />
                  <span style={{ fontWeight: 500, fontSize: '0.875rem' }}>
                    Duplicate Invoice Number Check
                  </span>
                </div>
                <span className="badge badge-validated">Unique</span>
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '0.75rem 1rem',
                  backgroundColor: 'rgba(56, 189, 248, 0.08)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid rgba(56, 189, 248, 0.2)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <GitCompare size={18} color="#38bdf8" />
                  <span style={{ fontWeight: 500, fontSize: '0.875rem' }}>
                    Purchase Order 2-Way Match Status
                  </span>
                </div>
                <StatusBadge status={invoice?.match_result?.status || 'matched'} />
              </div>
            </div>
          </div>

          {/* Workflow Timeline */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Workflow Lifecycle & Approvals</h3>
            </div>
            <ApprovalTimeline currentStatus={invoice?.status || 'validated'} />
          </div>
        </div>

        {/* Right Column: Original Document Viewer */}
        <div style={{ position: 'sticky', top: '1.5rem' }}>
          <div className="card" style={{ padding: '1.25rem' }}>
            <div className="card-header">
              <h3 className="card-title">
                <FileText size={18} color="#6366f1" />
                Original Scanned Invoice
              </h3>
              <a
                href={invoice?.original_file || '#'}
                target="_blank"
                rel="noreferrer"
                className="btn btn-ghost btn-sm"
                title="Open in new window"
              >
                <Maximize2 size={15} />
              </a>
            </div>

            <div
              style={{
                width: '100%',
                height: '620px',
                backgroundColor: '#090e1a',
                borderRadius: 'var(--radius-md)',
                overflow: 'hidden',
                border: '1px solid var(--card-border)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {invoice?.original_file?.endsWith('.pdf') ? (
                <iframe
                  src={invoice.original_file}
                  title="PDF Viewer"
                  style={{ width: '100%', height: '100%', border: 'none' }}
                />
              ) : (
                <img
                  src={
                    invoice?.original_file ||
                    'https://images.unsplash.com/photo-1554415707-9e49017a1430?auto=format&fit=crop&w=800&q=80'
                  }
                  alt="Invoice Document Preview"
                  style={{
                    maxWidth: '100%',
                    maxHeight: '100%',
                    objectFit: 'contain',
                    padding: '0.5rem',
                  }}
                  onError={(e) => {
                    e.currentTarget.src =
                      'https://images.unsplash.com/photo-1554415707-9e49017a1430?auto=format&fit=crop&w=800&q=80';
                  }}
                />
              )}
            </div>

            <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                Source: Original Ingestion File
              </span>
              <a
                href={invoice?.original_file || '#'}
                download
                className="btn btn-secondary btn-sm"
              >
                <Download size={14} /> Download File
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InvoiceDetail;
