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
      // Refresh the list after action
      fetchInvoices();
    } catch (error) {
      console.error(`Error during ${action}:`, error);
      alert(`Failed to ${action}. Check console.`);
    }
  };

  if (loading) return <p>Loading invoices...</p>;

  return (
    <div>
      <h2>Invoice List</h2>
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
                <td>
                  {inv.status === 'extracted' && (
                    <button onClick={() => handleAction(inv.id, 'validate')} style={btnStyle}>Validate</button>
                  )}
                  {inv.status === 'validated' && (
                    <button onClick={() => handleAction(inv.id, 'approve')} style={{...btnStyle, backgroundColor: '#22c55e'}}>Approve</button>
                  )}
                  {inv.status === 'approved' && (
                    <span style={{ color: 'green', fontWeight: 'bold' }}>✅ Approved</span>
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

const btnStyle = {
  padding: '6px 12px',
  backgroundColor: '#3b82f6',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer'
};