import { useEffect, useState } from 'react';
import api from '../api';

export default function InvoiceList() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/invoices/')
      .then(res => {
        setInvoices(res.data.results || res.data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Fetch error:", err);
        setLoading(false);
      });
  }, []);

  if (loading) return <p>Loading invoices...</p>;

  return (
    <div>
      <h2>Invoice List</h2>
      <table border="1" cellPadding="10" style={{ width: '100%', borderCollapse: 'collapse', background: '#fff' }}>
        <thead style={{ background: '#e2e8f0' }}>
          <tr>
            <th>ID</th>
            <th>Invoice #</th>
            <th>Total Amount</th>
            <th>Status</th>
            <th>Uploaded At</th>
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
                <td>{new Date(inv.created_at).toLocaleString()}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}