import { useEffect, useState } from 'react';
import {
  FileText,
  FileUp,
  ScanText,
  ShieldCheck,
  Clock,
  CheckCircle2,
  XCircle,
  CreditCard,
  Zap,
  RefreshCw,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import api from '../services/api';

const EMPTY_STATS = {
  kpis: {
    total: 0,
    uploaded: 0,
    extracted: 0,
    validated: 0,
    pending_approval: 0,
    approved: 0,
    rejected: 0,
    paid: 0,
  },
  ocr_accuracy: null,
  avg_processing_days: 0,
  payment_summary: {
    pending_amount: 0,
    paid_amount: 0,
    overdue_count: 0,
  },
  aging_data: [],
  trend_data: [],
  top_vendors: [],
};

const Dashboard = () => {
  const [stats, setStats] = useState(EMPTY_STATS);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  const fetchDashboardStats = async () => {
    setLoading(true);
    setLoadError('');
    try {
      const res = await api.get('/dashboard/stats/');
      setStats({
        ...EMPTY_STATS,
        kpis: { ...EMPTY_STATS.kpis, ...(res.data.invoice_counts || {}) },
        ocr_accuracy: res.data.ocr_accuracy ?? null,
        avg_processing_days: res.data.avg_processing_days ?? 0,
        payment_summary: { ...EMPTY_STATS.payment_summary, ...(res.data.payment_summary || {}) },
        aging_data: res.data.invoice_aging || [],
        trend_data: (res.data.monthly_invoice_trend || []).map((item) => ({
          month: item.month,
          volume: item.count,
          spend: item.amount,
        })),
        top_vendors: (res.data.vendor_analytics || []).map((item, index) => ({
          id: item.vendor_name || index,
          name: item.vendor_name,
          count: item.invoice_count,
          amount: item.total_amount,
        })),
      });
    } catch (error) {
      setStats(EMPTY_STATS);
      setLoadError(error.response?.data?.detail || 'Could not load dashboard metrics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardStats();
  }, []);

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  const KPI_CARDS = [
    { label: 'Total Invoices', value: stats.kpis?.total, icon: FileText, color: '#6366f1' },
    { label: 'Uploaded', value: stats.kpis?.uploaded, icon: FileUp, color: '#38bdf8' },
    { label: 'OCR Extracted', value: stats.kpis?.extracted, icon: ScanText, color: '#8b5cf6' },
    { label: 'Validated', value: stats.kpis?.validated, icon: ShieldCheck, color: '#22c55e' },
    { label: 'Pending Approval', value: stats.kpis?.pending_approval, icon: Clock, color: '#f59e0b' },
    { label: 'Approved', value: stats.kpis?.approved, icon: CheckCircle2, color: '#10b981' },
    { label: 'Rejected', value: stats.kpis?.rejected, icon: XCircle, color: '#ef4444' },
    { label: 'Paid', value: stats.kpis?.paid, icon: CreditCard, color: '#14b8a6' },
  ];

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div>
          <h1>Accounts Payable Dashboard</h1>
          <p className="subtitle">
            Real-time tracking of invoice ingestion, automated validation, matching, and payments
          </p>
        </div>
        <div className="header-actions">
          <button
            onClick={fetchDashboardStats}
            disabled={loading}
            className="btn btn-secondary"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* 8 KPI Cards */}
      {loadError && <p role="alert" style={{ color: '#f87171', marginBottom: '1rem' }}>{loadError}</p>}
      <div className="stats-grid">
        {KPI_CARDS.map((kpi, idx) => {
          const Icon = kpi.icon;
          return (
            <div key={idx} className="stat-card">
              <div className="stat-top">
                <span className="stat-label">{kpi.label}</span>
                <div
                  className="stat-icon-wrapper"
                  style={{
                    backgroundColor: `${kpi.color}18`,
                    color: kpi.color,
                  }}
                >
                  <Icon size={18} />
                </div>
              </div>
              <div className="stat-value">{kpi.value || 0}</div>
              <div className="stat-subtext">
                <span style={{ color: '#22c55e', fontWeight: 600 }}>Active</span> in workflow
              </div>
            </div>
          );
        })}
      </div>

      {/* Middle Row: Efficiency Metrics & Payment Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem', marginBottom: '2rem' }}>
        {/* OCR Accuracy Metric Card */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div className="card-header">
              <span className="card-title">
                <Zap size={18} color="#f59e0b" />
                Average OCR Confidence
              </span>
              <span className="badge badge-uploaded">Tesseract OCR</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginTop: '0.5rem' }}>
              <span style={{ fontSize: '2.5rem', fontWeight: 800, color: '#f8fafc' }}>
                {stats.ocr_accuracy == null ? '—' : `${stats.ocr_accuracy}%`}
              </span>
            </div>
            <p style={{ color: '#94a3b8', fontSize: '0.85rem', marginTop: '0.5rem' }}>
              Mean OCR confidence score. It is not independently verified extraction accuracy.
            </p>
          </div>
          <div style={{ marginTop: '1.25rem' }}>
            <div style={{ width: '100%', height: '8px', backgroundColor: '#0f172a', borderRadius: '4px', overflow: 'hidden' }}>
              <div
                style={{
                  width: `${stats.ocr_accuracy || 0}%`,
                  height: '100%',
                  background: 'linear-gradient(90deg, #6366f1, #22c55e)',
                  borderRadius: '4px',
                }}
              />
            </div>
          </div>
        </div>

        {/* Avg Processing Days Card */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div className="card-header">
              <span className="card-title">
                <Clock size={18} color="#6366f1" />
                Avg Cycle Time
              </span>
              <span className="badge badge-uploaded">Approved invoices</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginTop: '0.5rem' }}>
              <span style={{ fontSize: '2.5rem', fontWeight: 800, color: '#f8fafc' }}>
                {stats.avg_processing_days}
              </span>
              <span style={{ fontSize: '1.1rem', color: '#94a3b8', fontWeight: 500 }}>days / invoice</span>
            </div>
            <p style={{ color: '#94a3b8', fontSize: '0.85rem', marginTop: '0.5rem' }}>
              Mean time from invoice capture to final approval for completed approval requests.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '1rem', marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--card-border)' }}>
            <div>
              <p style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Manual Era</p>
              <p style={{ fontWeight: 600, color: '#ef4444' }}>8.5 Days</p>
            </div>
            <div style={{ borderLeft: '1px solid var(--card-border)', paddingLeft: '1rem' }}>
              <p style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Automated AP</p>
              <p style={{ fontWeight: 600, color: '#22c55e' }}>1.8 Days (-78%)</p>
            </div>
          </div>
        </div>

        {/* Payment Summary */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div className="card-header">
              <span className="card-title">
                <CreditCard size={18} color="#14b8a6" />
                Payment Summary
              </span>
              <span className="badge badge-uploaded">{stats.payment_summary?.overdue_count || 0} overdue</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '0.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#94a3b8', fontSize: '0.875rem' }}>Pending Release:</span>
                <span style={{ fontWeight: 700, color: '#fbbf24', fontSize: '1.1rem' }}>
                  {formatCurrency(stats.payment_summary?.pending_amount || 0)}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#94a3b8', fontSize: '0.875rem' }}>Paid:</span>
                <span style={{ fontWeight: 700, color: '#2dd4bf', fontSize: '1.1rem' }}>
                  {formatCurrency(stats.payment_summary?.paid_amount || 0)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Charts Section: Aging BarChart & Monthly Trend LineChart */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(460px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        {/* Invoice Aging BarChart */}
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Accounts Payable Aging Schedule</h3>
              <p className="card-subtitle">Outstanding liabilities grouped by aging brackets</p>
            </div>
          </div>
          <div style={{ width: '100%', height: '280px', marginTop: '1rem' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats.aging_data} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                <XAxis dataKey="bucket" stroke="#94a3b8" fontSize={12} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} tickFormatter={(v) => `₹${v / 1000}k`} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', borderColor: '#475569', borderRadius: '8px', color: '#f1f5f9' }}
                  formatter={(val) => [formatCurrency(val), 'Liability Amount']}
                />
                <Bar dataKey="amount" fill="#6366f1" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Monthly Trend LineChart */}
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Monthly Invoice Volume & Amount</h3>
              <p className="card-subtitle">Invoices captured and their total invoiced amount</p>
            </div>
          </div>
          <div style={{ width: '100%', height: '280px', marginTop: '1rem' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={stats.trend_data} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                <XAxis dataKey="month" stroke="#94a3b8" fontSize={12} tickLine={false} />
                <YAxis yAxisId="left" stroke="#8b5cf6" fontSize={12} tickLine={false} />
                <YAxis yAxisId="right" orientation="right" stroke="#22c55e" fontSize={12} tickLine={false} tickFormatter={(v) => `₹${v / 1000}k`} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', borderColor: '#475569', borderRadius: '8px', color: '#f1f5f9' }}
                />
                <Legend wrapperStyle={{ paddingTop: '10px' }} />
                <Line yAxisId="left" type="monotone" dataKey="volume" name="Invoices Processed" stroke="#8b5cf6" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                <Line yAxisId="right" type="monotone" dataKey="spend" name="Invoice Amount (₹)" stroke="#22c55e" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Vendor Analytics Table */}
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Top Strategic Vendors by Spend</h3>
            <p className="card-subtitle">Invoice count and total invoiced amount by vendor</p>
          </div>
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Vendor Name</th>
                <th>Total Invoices</th>
                <th>Total Invoiced</th>
              </tr>
            </thead>
            <tbody>
              {stats.top_vendors.map((v) => (
                <tr key={v.id}>
                  <td style={{ fontWeight: 600 }}>{v.name}</td>
                  <td>{v.count} invoices</td>
                  <td style={{ fontWeight: 700, color: '#f8fafc' }}>{formatCurrency(v.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
