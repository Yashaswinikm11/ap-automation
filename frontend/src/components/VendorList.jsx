import { useEffect, useState } from 'react';
import api from '../api';

export default function VendorList() {
  const [vendors, setVendors] = useState([]);
  const [name, setName] = useState('');
  const [gstin, setGstin] = useState('');

  const fetchVendors = () => {
    api.get('/vendors/').then(res => setVendors(res.data.results || res.data));
  };

  useEffect(() => { fetchVendors(); }, []);

  const handleAddVendor = async (e) => {
    e.preventDefault();
    try {
      await api.post('/vendors/', { name, gstin });
      setName('');
      setGstin('');
      fetchVendors(); // refresh list
    } catch (err) {
      console.error(err);
      alert("Failed to add vendor.");
    }
  };

  return (
    <div>
      <h2>Vendor Management</h2>
      
      {/* Add Vendor Form */}
      <div style={{ background: 'white', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
        <h3>Add New Vendor</h3>
        <form onSubmit={handleAddVendor} style={{ display: 'flex', gap: '10px' }}>
          <input required placeholder="Vendor Name" value={name} onChange={e => setName(e.target.value)} style={inputStyle} />
          <input placeholder="GSTIN" value={gstin} onChange={e => setGstin(e.target.value)} style={inputStyle} />
          <button type="submit" style={btnStyle}>Add Vendor</button>
        </form>
      </div>

      {/* Vendor List */}
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Vendor Name</th>
            <th>GSTIN</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {vendors.map(v => (
            <tr key={v.id}>
              <td>{v.id}</td>
              <td>{v.name}</td>
              <td>{v.gstin || '-'}</td>
              <td>{v.is_active ? 'Active' : 'Inactive'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const inputStyle = { padding: '8px', border: '1px solid #ccc', borderRadius: '4px', flex: 1 };
const btnStyle = { padding: '8px 16px', backgroundColor: '#1e293b', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' };