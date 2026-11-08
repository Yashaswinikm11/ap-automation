import { useEffect, useState } from 'react';
import api from '../api';

export default function Dashboard() {
  const [stats, setStats] = useState({
    total: 0,
    extracted: 0,
    approved: 0
  });

  useEffect(() => {
    // Fetch all invoices to calculate stats
    api.get('/invoices/').then(res => {
      const invoices = res.data.results || res.data;
      setStats({
        total: invoices.length,
        extracted: invoices.filter(i => i.status === 'extracted').length,
        approved: invoices.filter(i => i.status === 'approved').length,
      });
    }).catch(err => console.error(err));
  }, []);

  return (
    <div>
      <h1>Dashboard</h1>
      <p>Welcome to the AP Automation System.</p>
      
      <div style={{ display: 'flex', gap: '20px', marginTop: '30px' }}>
        <div style={cardStyle}>
          <h3>Total Invoices</h3>
          <h1 style={{ color: '#1e293b' }}>{stats.total}</h1>
        </div>
        <div style={cardStyle}>
          <h3>OCR Extracted</h3>
          <h1 style={{ color: '#3b82f6' }}>{stats.extracted}</h1>
        </div>
        <div style={cardStyle}>
          <h3>Approved</h3>
          <h1 style={{ color: '#22c55e' }}>{stats.approved}</h1>
        </div>
      </div>
    </div>
  );
}

const cardStyle = {
  background: 'white',
  padding: '20px',
  borderRadius: '8px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  flex: 1,
  textAlign: 'center'
};