import { useEffect, useState } from 'react';
import api from '../api';

export default function Dashboard() {
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    api.get('/dashboard/metrics/').then(res => setMetrics(res.data)).catch(console.error);
  }, []);

  if (!metrics) return <p>Loading Analytics...</p>;

  return (
    <div>
      <h1>Dashboard & Analytics</h1>
      <p>Welcome to the AP Automation System.</p>
      
      <div style={{ display: 'flex', gap: '20px', marginTop: '30px', flexWrap: 'wrap' }}>
        
        <div style={cardStyle}>
          <h3>Total Invoices</h3>
          <h1 style={{ color: '#1e293b' }}>{metrics.total_processed}</h1>
        </div>

        <div style={cardStyle}>
          <h3>OCR Accuracy</h3>
          <h1 style={{ color: '#3b82f6' }}>{metrics.ocr_accuracy_percentage}%</h1>
        </div>

        <div style={cardStyle}>
          <h3>Pending Approval</h3>
          <h1 style={{ color: '#eab308' }}>{metrics.status_breakdown['pending_approval'] || 0}</h1>
        </div>

        <div style={cardStyle}>
          <h3>Aging (&gt; 30 Days)</h3>
          <h1 style={{ color: '#ef4444' }}>{metrics.aging_invoices_over_30_days}</h1>
        </div>

      </div>

      <h2 style={{ marginTop: '40px' }}>Workflow Status Breakdown</h2>
      <table>
        <thead>
          <tr><th>Status</th><th>Count</th></tr>
        </thead>
        <tbody>
          {Object.entries(metrics.status_breakdown).map(([status, count]) => (
            <tr key={status}>
              <td style={{ textTransform: 'capitalize' }}>{status.replace('_', ' ')}</td>
              <td>{count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const cardStyle = {
  background: 'white',
  padding: '20px',
  borderRadius: '8px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  flex: '1 1 200px',
  textAlign: 'center'
};