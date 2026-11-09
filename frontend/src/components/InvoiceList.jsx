import { useEffect, useState } from 'react';
import api from '../api';

export default function InvoiceList() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchInvoices = () => {
    api.get('/invoices/')
      .then(res => {
        setInvoices(res.data.results || res.data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Fetch error:", err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchInvoices();
  }, []);

  const handleAction = async (id, action) => {
    try {
      await api.post(`/invoices/${id}/${action}/`);
      fetchInvoices();
    } catch (error) {
      console.error(`Error during ${action}:`, error);
      alert(`Failed to ${action}. Check console.`);
    }
  };

  const handlePayment = async (id) => {
    try {
      await api.post('/payments/requests/generate_from_invoice/', { invoice_id: id });
      alert("✅ Payment Request Generated Successfully!");
      fetchInvoices();
    } catch (error) {
      console.error(error);
      alert(error.response?.data?.error || "Failed to generate payment.");
    }
  };

  if (loading) return <p>Loading invoices...</p>;

  return (
    <div>
      <h2>Invoice Workflow</h2>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Invoice #</th>
            <th>Amount</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {invoices.length === 0 ? (
            <tr><td colSpan="5" style={{ textAlign: 'center' }}>No invoices found.</td></tr>
          ) : (
            invoices.map(inv => (
              <tr key={inv.id}>
                <td>{inv.id}</td>
                <td>{inv.invoice_number || '-'}</td>
                <td>{inv.total_amount || '-'}</td>
                <td>
                  <span style={{ padding: '4px 8px', background: '#fef08a', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold' }}>
                    {inv.status}
                  </span>
                </td>
                <td style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
                  {inv.status === 'extracted' && (
                    <button onClick={() => handleAction(inv.id, 'validate')} style={btnStyle('#3b82f6')}>Validate</button>
                  )}
                  {inv.status === 'validated' && (
                    <button onClick={() => handleAction(inv.id, 'submit_for_approval')} style={btnStyle('#22c55e')}>Submit for Approval</button>
                  )}
                  {inv.status === 'approved' && (
                    <>
                      <button onClick={() => handleAction(inv.id, 'match_2way')} style={btnStyle('#8b5cf6')}>2-Way Match</button>
                      <button onClick={() => handlePayment(inv.id)} style={btnStyle('#eab308')}>Pay</button>
                    </>
                  )}
                  {inv.status === 'paid' && (
                    <span style={{ color: 'green', fontWeight: 'bold' }}>✅ Paid</span>
                  )}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

const btnStyle = (color) => ({
  padding: '6px 12px',
  backgroundColor: color,
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px'
});