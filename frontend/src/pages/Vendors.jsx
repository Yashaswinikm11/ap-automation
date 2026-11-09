import { useState, useEffect } from 'react';
import {
  Building2,
  Plus,
  Search,
  Filter,
  CheckCircle2,
  Edit,
  ShieldCheck,
  X,
  Save,
  Check,
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import api from '../services/api';
import StatusBadge from '../components/StatusBadge';
import { useAuth } from '../context/AuthContext';

const INITIAL_FORM = {
  name: '',
  gstin: '',
  pan_number: '',
  tin_number: '',
  email: '',
  phone: '',
  address: '',
  bank_account: '',
  bank_ifsc: '',
  bank_name: '',
  bank_branch: '',
  payment_terms: 30,
  onboarding_status: 'pending',
};

const Vendors = () => {
  const { user } = useAuth();
  const showBankDetails = user?.role === 'admin' || user?.role === 'clerk';
  const [vendors, setVendors] = useState([]);
  const [loadError, setLoadError] = useState('');
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');

  // Drawer state
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingVendor, setEditingVendor] = useState(null);
  const [formData, setFormData] = useState(INITIAL_FORM);
  const [gstinValidation, setGstinValidation] = useState(null); // null, 'validating', 'valid', 'invalid'

  const fetchVendors = async () => {
    setLoading(true);
    setLoadError('');
    try {
      const res = await api.get('/vendors/');
      const data = res.data.results || res.data;
      setVendors(Array.isArray(data) ? data : []);
    } catch (error) {
      setVendors([]);
      setLoadError(error.response?.data?.detail || 'Could not load vendors.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVendors();
  }, []);

  const openAddDrawer = () => {
    setEditingVendor(null);
    setFormData(INITIAL_FORM);
    setGstinValidation(null);
    setDrawerOpen(true);
  };

  const openEditDrawer = (vendor) => {
    setEditingVendor(vendor);
    setFormData({ ...vendor });
    setGstinValidation(null);
    setDrawerOpen(true);
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
    setEditingVendor(null);
    setGstinValidation(null);
  };

  const handleValidateGSTIN = async () => {
    if (!formData.gstin || formData.gstin.length !== 15) {
      toast.error('Please enter a valid 15-character GSTIN.');
      return;
    }

    if (!editingVendor?.id) {
      toast.error('Save the vendor first to run server-side GSTIN format validation.');
      return;
    }

    setGstinValidation('validating');
    try {
      const response = await api.post(`/vendors/${editingVendor.id}/validate_gstin/`, { gstin: formData.gstin });
      if (!response.data.valid) {
        setGstinValidation({ status: 'invalid', message: response.data.message });
        toast.error(response.data.message || 'GSTIN format is invalid.');
        return;
      }
      setGstinValidation({ status: 'valid', message: response.data.message });
      toast.success(response.data.message || 'GSTIN format is valid.');
    } catch (error) {
      setGstinValidation({ status: 'invalid', message: error.response?.data?.message || 'GSTIN validation request failed.' });
      toast.error(error.response?.data?.message || 'GSTIN validation request failed.');
    } finally {
      if (gstinValidation === 'validating') {
        setGstinValidation((current) => current === 'validating' ? null : current);
      }
    }
  };

  const handleSaveVendor = async (e) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      toast.error('Vendor name is required.');
      return;
    }

    try {
      if (editingVendor) {
        const response = await api.patch(`/vendors/${editingVendor.id}/`, formData);
        setVendors((prev) => prev.map((v) => (v.id === editingVendor.id ? response.data : v)));
        toast.success('Vendor profile updated.');
      } else {
        const res = await api.post('/vendors/', formData);
        setVendors((prev) => [res.data, ...prev]);
        toast.success('New vendor onboarding record created.');
      }
      closeDrawer();
    } catch (error) {
      const detail = error.response?.data;
      toast.error(typeof detail === 'string' ? detail : JSON.stringify(detail || 'Could not save vendor.'));
    }
  };

  const handleUpdateStatus = async (id, newStatus) => {
    try {
      const action = newStatus === 'approved' ? 'approve_onboarding' : 'reject_onboarding';
      const response = await api.post(`/vendors/${id}/${action}/`);
      setVendors((prev) => prev.map((v) => (v.id === id ? response.data.vendor : v)));
      toast.success(response.data.message);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Could not update vendor onboarding status.');
    }
  };

  const filtered = vendors.filter((v) => {
    const matchesSearch =
      (v.name || '').toLowerCase().includes(search.toLowerCase()) ||
      (v.gstin || '').toLowerCase().includes(search.toLowerCase()) ||
      (v.email || '').toLowerCase().includes(search.toLowerCase());

    const matchesStatus =
      filterStatus === 'all' || (v.onboarding_status || '').toLowerCase() === filterStatus.toLowerCase();

    return matchesSearch && matchesStatus;
  });

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div>
          <h1>Vendor Master Directory</h1>
          <p className="subtitle">
            Manage vendor profiles and onboarding. GSTIN checks validate format only, not government registry status.
          </p>
        </div>
        {(user?.role === 'admin' || user?.role === 'clerk') && (
          <div className="header-actions">
            <button onClick={openAddDrawer} className="btn btn-primary">
              <Plus size={16} /> Add Vendor
            </button>
          </div>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div
        className="card"
        style={{
          padding: '1rem 1.25rem',
          marginBottom: '1.5rem',
          display: 'flex',
          gap: '1rem',
          alignItems: 'center',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ position: 'relative', flex: '1 1 240px' }}>
          <input
            type="text"
            placeholder="Search vendor name, GSTIN, or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ paddingLeft: '2.4rem' }}
          />
          <Search
            size={18}
            style={{
              position: 'absolute',
              left: '0.85rem',
              top: '50%',
              transform: 'translateY(-50%)',
              color: '#64748b',
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Filter size={16} color="#94a3b8" />
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            style={{ minWidth: '180px' }}
          >
            <option value="all">All Onboarding States</option>
            <option value="approved">Approved & Verified</option>
            <option value="pending">Pending KYC Review</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </div>

      {/* Vendors Table */}
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Vendor Entity</th>
              <th>GSTIN</th>
              <th>Contact Details</th>
              {showBankDetails && <th>Bank Account & IFSC</th>}
              <th>Status</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loadError && <tr><td colSpan={showBankDetails ? 6 : 5} role="alert" style={{ textAlign: 'center', color: '#f87171' }}>{loadError}</td></tr>}
            {loading && <tr><td colSpan={showBankDetails ? 6 : 5} style={{ textAlign: 'center' }}>Loading vendors…</td></tr>}
            {!loading && !loadError && filtered.length === 0 && <tr><td colSpan={showBankDetails ? 6 : 5} style={{ textAlign: 'center', color: '#94a3b8' }}>No vendors found.</td></tr>}
            {filtered.map((v) => (
              <tr key={v.id}>
                <td>
                  <div>
                    <span style={{ fontWeight: 600, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <Building2 size={16} color="#6366f1" />
                      {v.name}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                      Terms: {v.payment_terms === 0 ? 'Immediate' : `Net ${v.payment_terms ?? 30}`}
                    </span>
                  </div>
                </td>
                <td>
                  <span style={{ fontFamily: 'monospace', color: '#cbd5e1' }}>
                    {v.gstin || 'Unassigned'}
                  </span>
                </td>
                {showBankDetails && <td>
                  <div style={{ fontSize: '0.85rem' }}>
                    <p style={{ color: '#f1f5f9' }}>{v.email || '—'}</p>
                    <p style={{ color: '#94a3b8', fontSize: '0.75rem' }}>{v.phone || '—'}</p>
                  </div>
                </td>}
                <td>
                  <div style={{ fontSize: '0.85rem' }}>
                    <span style={{ fontFamily: 'monospace', color: '#f1f5f9' }}>
                      {v.bank_account || '—'}
                    </span>
                    <p style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                      IFSC: {v.bank_ifsc || '—'}
                    </p>
                  </div>
                </td>
                <td>
                  <StatusBadge
                    status={v.onboarding_status}
                    label=                    {v.onboarding_status === 'approved' ? 'Approved' : undefined}
                  />
                </td>
                <td style={{ textAlign: 'right' }}>
                  <div style={{ display: 'inline-flex', gap: '0.5rem', alignItems: 'center' }}>
                    {user?.role === 'admin' && v.onboarding_status === 'pending' && (
                      <>
                        <button
                          onClick={() => handleUpdateStatus(v.id, 'approved')}
                          className="btn btn-success btn-sm"
                          title="Approve Onboarding"
                        >
                          <Check size={14} />
                        </button>
                        <button
                          onClick={() => handleUpdateStatus(v.id, 'rejected')}
                          className="btn btn-danger btn-sm"
                          title="Reject Onboarding"
                        >
                          <X size={14} />
                        </button>
                      </>
                    )}
                    {showBankDetails && <button
                      onClick={() => openEditDrawer(v)}
                      className="btn btn-secondary btn-sm"
                      title="Edit Vendor"
                    >
                      <Edit size={14} /> Edit
                    </button>}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Slide-over Drawer for Add / Edit Vendor */}
      {drawerOpen && (
        <>
          <div className="drawer-backdrop" onClick={closeDrawer} />
          <div className="drawer">
            <div className="drawer-header">
              <h3 style={{ fontSize: '1.2rem', fontWeight: 600, color: '#f8fafc' }}>
                {editingVendor ? 'Edit Vendor Profile' : 'Onboard New Vendor'}
              </h3>
              <button onClick={closeDrawer} className="btn btn-ghost btn-sm btn-icon">
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSaveVendor} style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
              <div className="drawer-body">
                {/* Name */}
                <div className="form-group">
                  <label>Legal Business Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Acme Global Logistics Pvt Ltd"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                </div>

                {/* GSTIN with inline validate */}
                <div className="form-group">
                  <label>GSTIN (Goods & Services Tax ID)</label>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <input
                      type="text"
                      maxLength={15}
                      placeholder="e.g. 29ABCDE1234F1Z5"
                      value={formData.gstin}
                      onChange={(e) => {
                        setFormData({ ...formData, gstin: e.target.value.toUpperCase() });
                        setGstinValidation(null);
                      }}
                      style={{ textTransform: 'uppercase', fontFamily: 'monospace' }}
                    />
                    <button
                      type="button"
                      onClick={handleValidateGSTIN}
                      className="btn btn-secondary btn-sm"
                      style={{ whiteSpace: 'nowrap' }}
                    >
                      <ShieldCheck size={15} /> Validate
                    </button>
                  </div>

                  {/* GSTIN validation response inline */}
                  {gstinValidation && gstinValidation.status === 'valid' && (
                    <div
                      style={{
                        marginTop: '0.5rem',
                        padding: '0.5rem 0.75rem',
                        backgroundColor: 'rgba(34, 197, 94, 0.1)',
                        border: '1px solid rgba(34, 197, 94, 0.25)',
                        borderRadius: '6px',
                        fontSize: '0.8rem',
                        color: '#4ade80',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.4rem',
                      }}
                    >
                      <CheckCircle2 size={16} />
                      <span>{gstinValidation.message || 'GSTIN format is valid. Registry status was not checked.'}</span>
                    </div>
                  )}
                  {gstinValidation && gstinValidation.status === 'invalid' && (
                    <p role="alert" style={{ color: '#f87171', marginTop: '0.5rem' }}>{gstinValidation.message}</p>
                  )}
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div className="form-group">
                    <label>PAN Number</label>
                    <input
                      type="text"
                      maxLength={10}
                      placeholder="ABCDE1234F"
                      value={formData.pan_number || ''}
                      onChange={(e) => setFormData({ ...formData, pan_number: e.target.value.toUpperCase() })}
                      style={{ textTransform: 'uppercase', fontFamily: 'monospace' }}
                    />
                  </div>
                  <div className="form-group">
                    <label>TIN Number</label>
                    <input
                      type="text"
                      placeholder="TIN-000000"
                      value={formData.tin_number || ''}
                      onChange={(e) => setFormData({ ...formData, tin_number: e.target.value })}
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div className="form-group">
                    <label>Billing Email</label>
                    <input
                      type="email"
                      placeholder="accounts@vendor.com"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>Contact Phone</label>
                    <input
                      type="text"
                      placeholder="+91 98000 00000"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label>Registered Address</label>
                  <textarea
                    rows={2}
                    placeholder="Enter full corporate address..."
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  />
                </div>

                {/* Bank Details */}
                <div style={{ borderTop: '1px solid var(--card-border)', paddingTop: '1rem', marginTop: '0.5rem' }}>
                  <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.75rem' }}>
                    Banking & Payment Terms
                  </h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                    <div className="form-group">
                      <label>Bank Account Number</label>
                      <input
                        type="text"
                        placeholder="e.g. 992817264518"
                        value={formData.bank_account}
                        onChange={(e) => setFormData({ ...formData, bank_account: e.target.value })}
                      />
                    </div>
                    <div className="form-group">
                      <label>Bank IFSC Code</label>
                      <input
                        type="text"
                        maxLength={11}
                        placeholder="HDFC0001234"
                        value={formData.bank_ifsc}
                        onChange={(e) => setFormData({ ...formData, bank_ifsc: e.target.value.toUpperCase() })}
                        style={{ textTransform: 'uppercase' }}
                      />
                    </div>
                    <div className="form-group">
                      <label>Bank Name</label>
                      <input
                        type="text"
                        value={formData.bank_name || ''}
                        onChange={(e) => setFormData({ ...formData, bank_name: e.target.value })}
                      />
                    </div>
                    <div className="form-group">
                      <label>Bank Branch</label>
                      <input
                        type="text"
                        value={formData.bank_branch || ''}
                        onChange={(e) => setFormData({ ...formData, bank_branch: e.target.value })}
                      />
                    </div>
                  </div>

                  <div className="form-group">
                    <label>Payment Terms</label>
                    <select
                      value={formData.payment_terms}
                      onChange={(e) => setFormData({ ...formData, payment_terms: e.target.value })}
                    >
                      <option value={0}>Immediate / Due on Receipt</option>
                      <option value={15}>Net 15 Days</option>
                      <option value={30}>Net 30 Days (Standard)</option>
                      <option value={45}>Net 45 Days</option>
                      <option value={60}>Net 60 Days</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="drawer-footer">
                <button type="button" onClick={closeDrawer} className="btn btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  <Save size={16} />
                  {editingVendor ? 'Save Changes' : 'Create Vendor'}
                </button>
              </div>
            </form>
          </div>
        </>
      )}
    </div>
  );
};

export default Vendors;
