import { useEffect, useState } from 'react';
import api from '../api';

export default function Reports() {
  const [report, setReport] = useState(null);

  useEffect(() => {
    api.get('/reports/ap-summary/').then(res => setReport(res.data));
  }, []);

  if (!report) return <p>Loading report...</p>;

  return (
    <div>
      <h2>AP Reports & Analytics</h2>
      <div style={{ display: 'flex', gap: '20px', marginBottom: '30px' }}>
        <div style={cardStyle}>
          <h3>Total Unpaid Amount</h3>
          <h1 style={{ color: '#ef4444' }}>₹{report.total_unpaid_amount}</h1>
        </div>
        <div style={cardStyle}>
          <h3>Pending Payments</h3>
          <h1 style={{ color: '#3b82f6' }}>{report.total_payments_pending}</h1>
        </div>
      </div>

      <h3>Invoice Status Breakdown</h3>
      <table>
        <thead><tr><th>Status</th><th>Count</th></tr></thead>
        <tbody>
          {Object.entries(report.invoice_status_breakdown).map(([status, count]) => (
            <tr key={status}><td>{status}</td><td>{count}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const cardStyle = {
  background: 'white', padding: '20px', borderRadius: '8px', 
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)', flex: 1, textAlign: 'center'
};