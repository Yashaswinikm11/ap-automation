import { useCallback, useEffect, useState } from 'react';
import { Download, FileText } from 'lucide-react';
import { toast } from 'react-hot-toast';
import api from '../services/api';

const REPORTS = {
  aging: {
    label: 'AP Aging',
    endpoint: '/reports/aging/',
    rowsKey: 'details',
    filename: 'ap_aging_report.csv',
    columns: [
      ['invoice_number', 'Invoice #'],
      ['vendor_name', 'Vendor'],
      ['invoice_date', 'Invoice Date'],
      ['due_date', 'Due Date'],
      ['amount', 'Amount'],
      ['status', 'Status'],
      ['days_past_due', 'Days Past Due'],
      ['aging_bucket', 'Aging Bucket'],
    ],
  },
  status: {
    label: 'Invoice Status',
    endpoint: '/reports/invoice-status/',
    rowsKey: 'invoices',
    filename: 'invoice_status_report.csv',
    columns: [
      ['invoice_number', 'Invoice #'],
      ['vendor_name', 'Vendor'],
      ['po_number', 'PO #'],
      ['invoice_date', 'Invoice Date'],
      ['due_date', 'Due Date'],
      ['total_amount', 'Total Amount'],
      ['tax_amount', 'Tax Amount'],
      ['currency', 'Currency'],
      ['status', 'Status'],
      ['is_duplicate', 'Duplicate'],
      ['uploaded_by', 'Uploaded By'],
    ],
  },
  exceptions: {
    label: 'Exceptions',
    endpoint: '/reports/exceptions/',
    rowsKey: 'exceptions',
    filename: 'exception_report.csv',
    columns: [
      ['invoice_number', 'Invoice #'],
      ['vendor_name', 'Vendor'],
      ['total_amount', 'Total Amount'],
      ['status', 'Status'],
      ['is_duplicate', 'Duplicate'],
      ['validation_errors', 'Validation Errors'],
      ['match_status', 'Match Status'],
      ['match_issues', 'Match Issues'],
      ['created_at', 'Created At'],
    ],
  },
  audit: {
    label: 'Audit Log',
    endpoint: '/reports/audit-log/',
    rowsKey: 'results',
    filename: 'audit_log_report.csv',
    columns: [
      ['created_at', 'Timestamp'],
      ['username', 'User'],
      ['action', 'Action'],
      ['entity_type', 'Entity'],
      ['entity_id', 'Entity ID'],
      ['description', 'Description'],
      ['ip_address', 'IP Address'],
    ],
  },
  gst: {
    label: 'GST / Tax',
    endpoint: '/reports/gst/',
    rowsKey: 'invoices',
    filename: 'gst_report.csv',
    columns: [
      ['invoice_number', 'Invoice #'],
      ['vendor_name', 'Vendor'],
      ['gstin', 'GSTIN'],
      ['invoice_date', 'Invoice Date'],
      ['taxable_amount', 'Taxable Amount'],
      ['tax_amount', 'Tax Amount'],
      ['total_amount', 'Total Amount'],
      ['status', 'Status'],
    ],
  },
};

const formatCell = (value) => {
  if (value == null || value === '') return '—';
  if (Array.isArray(value)) return value.join('; ') || '—';
  if (typeof value === 'object') return JSON.stringify(value);
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return String(value);
};

const Reports = () => {
  const [reportType, setReportType] = useState('aging');
  const [rows, setRows] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [pageCount, setPageCount] = useState(1);
  const report = REPORTS[reportType];

  const fetchReport = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get(report.endpoint, {
        params: reportType === 'audit' ? { page } : undefined,
      });
      setRows(response.data[report.rowsKey] || []);
      setSummary(response.data.summary || null);
      setPageCount(response.data.count ? Math.ceil(response.data.count / 50) : 1);
    } catch (requestError) {
      setRows([]);
      setSummary(null);
      setError(requestError.response?.data?.detail || `Could not load the ${report.label} report.`);
    } finally {
      setLoading(false);
    }
  }, [page, report.endpoint, report.label, report.rowsKey, reportType]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const exportCSV = async () => {
    try {
      const response = await api.get(report.endpoint, {
        params: { format: 'csv' },
        responseType: 'blob',
      });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = report.filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      toast.error(requestError.response?.data?.detail || `Could not export the ${report.label} report.`);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Accounts Payable Reports</h1>
          <p className="subtitle">Live reports generated from invoice, tax, exception, aging, and audit records.</p>
        </div>
        <div className="header-actions">
          <button onClick={exportCSV} className="btn btn-secondary" disabled={loading}>
            <Download size={15} /> Export CSV
          </button>
          <button
            onClick={() => {
              window.print();
              toast('Choose “Save as PDF” in the print dialog to create a PDF.');
            }}
            className="btn btn-primary"
          >
            <FileText size={15} /> Print / Save as PDF
          </button>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <label htmlFor="report-type">Report</label>
        <select
          id="report-type"
          value={reportType}
          onChange={(event) => {
            setPage(1);
            setReportType(event.target.value);
          }}
          style={{ marginTop: '0.5rem', maxWidth: '360px' }}
        >
          {Object.entries(REPORTS).map(([key, item]) => (
            <option key={key} value={key}>{item.label}</option>
          ))}
        </select>
      </div>

      {summary && (
        <div className="stats-grid" style={{ marginBottom: '1.5rem' }}>
          {Object.entries(summary).map(([key, value]) => (
            <div className="stat-card" key={key}>
              <span className="stat-label">{key.replaceAll('_', ' ')}</span>
              <div className="stat-value">
                {typeof value === 'object'
                  ? Object.entries(value).map(([label, item]) => `${label}: ${formatCell(item)}`).join(' | ')
                  : formatCell(value)}
              </div>
            </div>
          ))}
        </div>
      )}

      {error && <p role="alert" style={{ color: '#f87171', marginBottom: '1rem' }}>{error}</p>}

      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">{report.label}</h3>
            <p className="card-subtitle">{rows.length} records returned</p>
          </div>
        </div>
        {reportType === 'audit' && pageCount > 1 && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem' }}>
            <span>Page {page} of {pageCount}</span>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                type="button"
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                disabled={page === 1 || loading}
                className="btn btn-secondary btn-sm"
              >
                Previous
              </button>
              <button
                type="button"
                onClick={() => setPage((current) => Math.min(pageCount, current + 1))}
                disabled={page === pageCount || loading}
                className="btn btn-secondary btn-sm"
              >
                Next
              </button>
            </div>
          </div>
        )}
        <div className="table-container">
          <table>
            <thead>
              <tr>{report.columns.map(([, label]) => <th key={label}>{label}</th>)}</tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={report.columns.length} style={{ textAlign: 'center' }}>Loading report…</td></tr>
              ) : rows.length === 0 ? (
                <tr><td colSpan={report.columns.length} style={{ textAlign: 'center', color: '#94a3b8' }}>No records in this report.</td></tr>
              ) : rows.map((row, index) => (
                <tr key={row.id || row.invoice_id || index}>
                  {report.columns.map(([key]) => <td key={key}>{formatCell(row[key])}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Reports;
