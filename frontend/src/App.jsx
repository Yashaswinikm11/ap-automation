import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import UploadInvoice from './components/UploadInvoice';
import InvoiceList from './components/InvoiceList';
import VendorList from './components/VendorList'; // 👈 Added VendorList import
import './App.css';

function App() {
  return (
    <Router>
      <div className="app-container">
        <nav className="sidebar">
          <h2>AP Automation</h2>
          <ul>
            <li><Link to="/">Dashboard</Link></li>
            <li><Link to="/upload">Upload Invoice</Link></li>
            <li><Link to="/invoices">All Invoices</Link></li>
            <li><Link to="/vendors">Vendors</Link></li> {/* 👈 Added Vendors Link */}
            <li><a href="http://localhost:8000/admin/" target="_blank" rel="noreferrer">Django Admin</a></li>
          </ul>
        </nav>
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/upload" element={<UploadInvoice />} />
            <Route path="/invoices" element={<InvoiceList />} />
            <Route path="/vendors" element={<VendorList />} /> {/* 👈 Added Vendors Route */}
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;