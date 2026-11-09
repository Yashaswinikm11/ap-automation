import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  GitCompare,
  Package,
  Layers,
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import api from '../services/api';
import StatusBadge from '../components/StatusBadge';

const POMatching = () => {
  const [searchParams] = useSearchParams();
  const preselectedInvoiceId = searchParams.get('invoiceId');

  const [activeTab, setActiveTab] = useState('match'); // 'match', 'pos', 'grns'
  const [invoices, setInvoices] = useState([]);
  const [purchaseOrders, setPurchaseOrders] = useState([]);
  const [grns, setGrns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedInvoiceId, setSelectedInvoiceId] = useState(preselectedInvoiceId || '');
  const [matchType, setMatchType] = useState('2way'); // '2way' or '3way'
  const [isMatching, setIsMatching] = useState(false);
  const [matchResult, setMatchResult] = useState(null);

  useEffect(() => {
    const fetchMatchingData = async () => {
      setLoading(true);
      try {
        const [invoiceResponse, poResponse, grnResponse] = await Promise.all([
          api.get('/invoices/'),
          api.get('/invoices/purchase-orders/'),
          api.get('/invoices/grns/'),
        ]);
        const invoiceData = invoiceResponse.data.results || invoiceResponse.data;
        const poData = poResponse.data.results || poResponse.data;
        const grnData = grnResponse.data.results || grnResponse.data;
        const liveInvoices = invoiceData.map((invoice) => ({
          ...invoice,
          vendor: invoice.effective_vendor_name || invoice.vendor_details?.name || 'Unknown vendor',
          amount: Number(invoice.total_amount || 0),
        }));
        const livePurchaseOrders = poData.map((po) => ({
          ...po,
          vendor: po.vendor_details?.name || 'Unknown vendor',
          total_amount: Number(po.total_amount || 0),
        }));
        setInvoices(liveInvoices);
        setPurchaseOrders(livePurchaseOrders);
        setGrns(grnData);
        setSelectedInvoiceId((current) =>
          liveInvoices.some((invoice) => String(invoice.id) === String(current))
            ? String(current)
            : liveInvoices.some((invoice) => String(invoice.id) === preselectedInvoiceId)
              ? preselectedInvoiceId
              : String(liveInvoices[0]?.id || '')
        );
      } catch (error) {
        toast.error(error.response?.data?.detail || 'Could not load invoices and matching records.');
      } finally {
        setLoading(false);
      }
    };

    fetchMatchingData();
  }, [preselectedInvoiceId]);

  const handleRunMatch = async () => {
    if (!selectedInvoiceId) {
      toast.error('Select an invoice before running a match.');
      return;
    }

    setIsMatching(true);
    try {
      const response = await api.post(`/invoices/${selectedInvoiceId}/match_po/`, {
        match_type: matchType,
      });
      setMatchResult(response.data);
      toast.success(`${matchType.toUpperCase()} matching completed: ${response.data.status}.`);
    } catch (error) {
      toast.error(
        error.response?.data?.error ||
        error.response?.data?.detail ||
        'Could not match this invoice.'
      );
    } finally {
      setIsMatching(false);
    }
  };

  const selectedInvoice = invoices.find((invoice) => String(invoice.id) === String(selectedInvoiceId));
  const matchDifferences = matchResult?.differences || {};
  const matchedVendor = Boolean(matchDifferences.vendor_matched);
  const matchedAmount = Boolean(matchDifferences.amount_matched ?? matchDifferences.po_amount_matched);
  const matchedGRN = Boolean(matchDifferences.grn_amount_matched);
  const formatCurrency = (value) => value == null ? '—' : `₹${Number(value).toLocaleString('en-IN')}`;
  const matchRows = matchResult ? [
    {
      field: 'Vendor Identity',
      po: selectedInvoice?.purchase_order_details?.vendor_details?.name || 'No linked purchase order',
      inv: selectedInvoice?.vendor || 'Unknown vendor',
      grn: selectedInvoice?.purchase_order_details?.vendor_details?.name || '—',
      diff: !selectedInvoice?.purchase_order
        ? 'No purchase order linked'
        : matchedVendor ? 'Matches' : 'Does not match',
      status: matchedVendor ? 'ok' : 'error',
    },
    {
      field: 'Invoice Amount',
      po: formatCurrency(matchResult.po_amount),
      inv: formatCurrency(matchResult.invoice_amount),
      grn: formatCurrency(matchResult.grn_amount),
      diff: matchDifferences.error || matchDifferences.issues?.join(' ') || `${matchDifferences.percentage_difference ?? matchDifferences.po_percentage_difference ?? 0}% variance`,
      status: matchedAmount && (matchType !== '3way' || matchedGRN) ? 'ok' : 'error',
    },
  ] : [];

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div>
          <h1>Purchase Order & Goods Receipt Matching</h1>
          <p className="subtitle">
            Perform automated 2-Way and 3-Way tolerance matching between invoices, POs, and receiving notes
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="tabs-nav">
        <button
          onClick={() => setActiveTab('match')}
          className={`tab-btn ${activeTab === 'match' ? 'active' : ''}`}
        >
          <GitCompare size={16} style={{ display: 'inline', marginRight: '6px' }} />
          Match Workbench
        </button>
        <button
          onClick={() => setActiveTab('pos')}
          className={`tab-btn ${activeTab === 'pos' ? 'active' : ''}`}
        >
          <Package size={16} style={{ display: 'inline', marginRight: '6px' }} />
          Purchase Orders ({purchaseOrders.length})
        </button>
        <button
          onClick={() => setActiveTab('grns')}
          className={`tab-btn ${activeTab === 'grns' ? 'active' : ''}`}
        >
          <Layers size={16} style={{ display: 'inline', marginRight: '6px' }} />
          Goods Receipt Notes ({grns.length})
        </button>
      </div>

      {/* Tab 1: Match Workbench */}
      {activeTab === 'match' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
          {/* Match Configuration Card */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Match Configuration</h3>
              {/* 2-Way vs 3-Way Selector */}
              <div style={{ display: 'flex', gap: '0.5rem', background: '#0f172a', padding: '0.25rem', borderRadius: '8px' }}>
                <button
                  type="button"
                  onClick={() => {
                    setMatchType('2way');
                    setMatchResult(null);
                  }}
                  style={{
                    padding: '0.4rem 0.85rem',
                    borderRadius: '6px',
                    border: 'none',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    background: matchType === '2way' ? 'var(--primary)' : 'transparent',
                    color: matchType === '2way' ? '#ffffff' : 'var(--muted)',
                  }}
                >
                  2-Way Match (Inv + PO)
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMatchType('3way');
                    setMatchResult(null);
                  }}
                  style={{
                    padding: '0.4rem 0.85rem',
                    borderRadius: '6px',
                    border: 'none',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    background: matchType === '3way' ? 'var(--primary)' : 'transparent',
                    color: matchType === '3way' ? '#ffffff' : 'var(--muted)',
                  }}
                >
                  3-Way Match (Inv + PO + GRN)
                </button>
              </div>
            </div>

            {/* Selectors Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: matchType === '3way' ? '1fr 1fr 1fr' : '1fr 1fr', gap: '1.25rem' }}>
              {/* Select Invoice */}
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label>Select Invoice to Match</label>
                <select
                  value={selectedInvoiceId}
                  onChange={(e) => {
                    setSelectedInvoiceId(e.target.value);
                    setMatchResult(null);
                  }}
                  disabled={loading || invoices.length === 0}
                >
                  {invoices.length === 0 && <option value="">No invoices available</option>}
                  {invoices.map((inv) => (
                    <option key={inv.id} value={inv.id}>
                      {inv.invoice_number || `Invoice #${inv.id}`} — {inv.vendor} ({formatCurrency(inv.amount)})
                    </option>
                  ))}
                </select>
              </div>

              {/* Purchase orders are matched using the PO linked to the invoice in the backend. */}
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label>Invoice-linked Purchase Order</label>
                <p style={{ color: '#cbd5e1', padding: '0.65rem 0' }}>
                  {selectedInvoice?.purchase_order_details?.po_number || 'No purchase order linked'}
                </p>
              </div>

              {matchType === '3way' && (
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label>Goods Receipt Notes for Linked PO</label>
                  <p style={{ color: '#cbd5e1', padding: '0.65rem 0' }}>
                    {grns
                      .filter((grn) => String(grn.purchase_order) === String(selectedInvoice?.purchase_order))
                      .map((grn) => grn.grn_number)
                      .join(', ') || 'No receipt notes linked'}
                  </p>
                </div>
              )}
            </div>

            <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                onClick={handleRunMatch}
                disabled={isMatching || loading || !selectedInvoiceId}
                className="btn btn-primary"
              >
                <GitCompare size={16} />
                {isMatching ? 'Running Comparison...' : 'Run Automated Match'}
              </button>
            </div>
          </div>

          {/* Results Panel */}
          {matchResult && (
            <div className="card">
              <div className="card-header">
                <div>
                  <h3 className="card-title">Matching Comparison Matrix</h3>
                  <p className="card-subtitle">Tolerance Policy: {matchResult.tolerance_percentage}%</p>
                </div>
                <StatusBadge status={matchResult.status} />
              </div>

              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Comparison Field</th>
                      <th>Purchase Order (PO)</th>
                      <th>Supplier Invoice</th>
                      {matchType === '3way' && <th>Goods Receipt (GRN)</th>}
                      <th>Difference / Variance</th>
                      <th>Parity Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {matchRows.map((f, idx) => (
                      <tr key={idx}>
                        <td style={{ fontWeight: 600 }}>{f.field}</td>
                        <td style={{ color: '#cbd5e1' }}>{f.po}</td>
                        <td style={{ color: '#f8fafc', fontWeight: 600 }}>{f.inv}</td>
                        {matchType === '3way' && <td style={{ color: '#cbd5e1' }}>{f.grn}</td>}
                        <td
                          style={{
                            fontWeight: 700,
                            color: f.status === 'error' ? '#f87171' : '#4ade80',
                          }}
                        >
                          {f.diff}
                        </td>
                        <td>
                          {f.status === 'ok' ? (
                            <span className="badge badge-validated">Matched</span>
                          ) : (
                            <span className="badge badge-rejected">Exception</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Purchase Orders List */}
      {activeTab === 'pos' && (
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Active Purchase Orders</h3>
              <p className="card-subtitle">Open purchase contracts for matching</p>
            </div>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>PO Number</th>
                  <th>Vendor</th>
                  <th>Committed Amount</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {purchaseOrders.length === 0 ? (
                  <tr><td colSpan={4} style={{ textAlign: 'center', padding: '2rem' }}>No purchase orders found.</td></tr>
                ) : purchaseOrders.map((po) => (
                  <tr key={po.id}>
                    <td style={{ fontWeight: 600, color: '#f8fafc' }}>{po.po_number}</td>
                    <td>{po.vendor}</td>
                    <td style={{ fontWeight: 700 }}>₹{po.total_amount.toLocaleString()}</td>
                    <td>
                      <StatusBadge status={po.status} label="Open" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Goods Receipt Notes (GRNs) */}
      {activeTab === 'grns' && (
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Warehouse Goods Receipt Notes</h3>
              <p className="card-subtitle">Receiving dock physical intake verification</p>
            </div>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>GRN Number</th>
                  <th>Linked PO</th>
                  <th>Receipt Date</th>
                  <th>Received Value</th>
                </tr>
              </thead>
              <tbody>
                {grns.length === 0 ? (
                  <tr><td colSpan={4} style={{ textAlign: 'center', padding: '2rem' }}>No goods receipt notes found.</td></tr>
                ) : grns.map((grn) => (
                  <tr key={grn.id}>
                    <td style={{ fontWeight: 600, color: '#f8fafc' }}>{grn.grn_number}</td>
                    <td>{grn.po_number}</td>
                    <td style={{ color: '#94a3b8' }}>{grn.received_date}</td>
                    <td style={{ fontWeight: 700 }}>₹{grn.total_amount.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default POMatching;
