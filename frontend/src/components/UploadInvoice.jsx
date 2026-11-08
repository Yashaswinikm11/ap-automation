import { useState } from 'react';
import api from '../api';

export default function UploadInvoice() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setMessage('');
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setMessage('');

    const formData = new FormData();
    formData.append('original_file', file);

    try {
      const response = await api.post('/invoices/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setMessage(`✅ Success! Invoice ${response.data.invoice_number || 'uploaded'} is now ${response.data.status}.`);
      setFile(null);
    } catch (error) {
      console.error(error);
      setMessage(`❌ Upload failed. Check console for details.`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <h2>Upload Invoice (PDF or Image)</h2>
      <div style={{ padding: '20px', border: '2px dashed #ccc', borderRadius: '8px', textAlign: 'center', background: '#fff' }}>
        <input type="file" onChange={handleFileChange} accept=".pdf, .jpg, .jpeg, .png" />
        <br /><br />
        <button onClick={handleUpload} disabled={!file || uploading} style={{ padding: '10px 20px', cursor: 'pointer', background: '#1e293b', color: 'white', border: 'none', borderRadius: '4px' }}>
          {uploading ? 'Processing OCR...' : 'Upload & Extract'}
        </button>
      </div>
      
      {message && <p style={{ marginTop: '20px', fontWeight: 'bold' }}>{message}</p>}
    </div>
  );
}