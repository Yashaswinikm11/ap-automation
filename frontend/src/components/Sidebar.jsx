import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  Upload,
  GitCompare,
  CheckCircle,
  Building2,
  CreditCard,
  BarChart3,
  LogOut,
  Sparkles,
  User,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/invoices', label: 'Invoices', icon: FileText },
  { to: '/upload', label: 'Upload Invoice', icon: Upload },
  { to: '/po-matching', label: 'PO Matching', icon: GitCompare },
  { to: '/approvals', label: 'Approvals', icon: CheckCircle },
  { to: '/vendors', label: 'Vendors', icon: Building2 },
  { to: '/payments', label: 'Payments', icon: CreditCard },
  { to: '/reports', label: 'Reports', icon: BarChart3 },
];

const Sidebar = () => {
  const { user, logout } = useAuth();

  return (
    <aside className="sidebar">
      <div>
        {/* Brand Header */}
        <div
          style={{
            padding: '1.5rem 1.25rem 1.25rem 1.25rem',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
          }}
        >
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
              boxShadow: '0 4px 12px rgba(99, 102, 241, 0.4)',
            }}
          >
            <Sparkles size={20} />
          </div>
          <div>
            <h2
              style={{
                fontSize: '1.05rem',
                fontWeight: 700,
                color: '#f8fafc',
                letterSpacing: '-0.02em',
                lineHeight: 1.2,
              }}
            >
              AP Automation
            </h2>
            <span
              style={{
                fontSize: '0.72rem',
                color: '#94a3b8',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                fontWeight: 600,
              }}
            >
              Enterprise Suite
            </span>
          </div>
        </div>

        {/* Navigation Items */}
        <nav style={{ padding: '1rem 0' }}>
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `sidebar-link ${isActive ? 'active' : ''}`
                }
              >
                <Icon size={19} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* User Footer Profile & Logout */}
      <div
        style={{
          padding: '1rem 1.25rem',
          borderTop: '1px solid rgba(255, 255, 255, 0.08)',
          backgroundColor: 'rgba(15, 23, 42, 0.45)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', overflow: 'hidden' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              backgroundColor: '#312e81',
              border: '1.5px solid #6366f1',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#c7d2fe',
              fontWeight: 600,
              fontSize: '0.85rem',
              flexShrink: 0,
            }}
          >
            {user?.username ? user.username.charAt(0).toUpperCase() : <User size={16} />}
          </div>
          <div style={{ minWidth: 0, overflow: 'hidden' }}>
            <p
              style={{
                fontSize: '0.875rem',
                fontWeight: 600,
                color: '#f1f5f9',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              {user?.username || 'Finance User'}
            </p>
            <p
              style={{
                fontSize: '0.725rem',
                color: '#94a3b8',
                textTransform: 'capitalize',
              }}
            >
              {user?.role || 'AP Specialist'}
            </p>
          </div>
        </div>

        <button
          onClick={logout}
          title="Sign Out"
          style={{
            background: 'transparent',
            border: 'none',
            color: '#94a3b8',
            cursor: 'pointer',
            padding: '0.4rem',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.15s',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = '#ef4444';
            e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.1)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = '#94a3b8';
            e.currentTarget.style.backgroundColor = 'transparent';
          }}
        >
          <LogOut size={18} />
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
