import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Link } from 'react-router-dom';
import {
  UploadCloud,
  File,
  FileText,
  Image,
  CheckCircle2,
  AlertCircle,
  X,
  ArrowRight,
  Info,
  Loader2,
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import api from '../services/api';

const ACCEPTED_TYPES = {
  'application/pdf': ['.pdf'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
  'image/tiff': ['.tiff', '.tif'],
};

const InvoiceCapture = () => {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);

  const onDrop = useCallback((acceptedFiles) => {
    const mapped = acceptedFiles.map((file) => ({
      file,
      id: Math.random().toString(36).substring(7),
      name: file.name,
      size: (file.size / 1024 / 1024).toFixed(2), // MB
      type: file.type,
      status: 'pending', // pending, uploading, success, error
      progress: 0,
      invoiceId: null,
      errorMsg: null,
    }));
    setFiles((prev) => [...prev, ...mapped]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: 25 * 1024 * 1024, // 25MB
  });

  const removeFile = (id) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const uploadSingleFile = async (item) => {
    const formData = new FormData();
    formData.append('original_file', item.file);

    // Update status to uploading
    setFiles((prev) =>
      prev.map((f) => (f.id === item.id ? { ...f, status: 'uploading', progress: 30 } : f))
    );

    try {
      const response = await api.post('/invoices/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const percent = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1));
          setFiles((prev) =>
            prev.map((f) => (f.id === item.id ? { ...f, progress: percent } : f))
          );
        },
      });

      if (!response.data.id) {
        throw new Error('Upload response did not include the created invoice ID.');
      }
      const invoiceId = response.data.id;

      setFiles((prev) =>
        prev.map((f) =>
          f.id === item.id
            ? { ...f, status: 'success', progress: 100, invoiceId }
            : f
        )
      );
      toast.success(`Uploaded successfully: ${item.name}`);
    } catch (err) {
      const errorText = err.response?.data?.original_file?.[0] || err.message || 'Upload failed';
      setFiles((prev) =>
        prev.map((f) =>
          f.id === item.id
            ? { ...f, status: 'error', progress: 0, errorMsg: errorText }
            : f
        )
      );
      toast.error(`Error uploading ${item.name}: ${errorText}`);
    }
  };

  const handleUploadAll = async () => {
    const pendingFiles = files.filter((f) => f.status === 'pending');
    if (pendingFiles.length === 0) {
      toast('No pending files to upload.');
      return;
    }

    setUploading(true);
    for (const item of pendingFiles) {
      await uploadSingleFile(item);
    }
    setUploading(false);
  };

  const getFileIcon = (type) => {
    if (type.includes('pdf')) return <FileText size={24} color="#ef4444" />;
    if (type.includes('image')) return <Image size={24} color="#38bdf8" />;
    return <File size={24} color="#a855f7" />;
  };

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1>Invoice Document Ingestion</h1>
          <p className="subtitle">
            Upload raw supplier invoices for automated OCR extraction, math validation, and PO matching
          </p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '2rem' }}>
        {/* Left Column: Dropzone and File Queue */}
        <div>
          <div
            {...getRootProps()}
            className={`upload-zone ${isDragActive ? 'drag-active' : ''}`}
          >
            <input {...getInputProps()} />
            <div
              style={{
                width: '64px',
                height: '64px',
                borderRadius: '50%',
                backgroundColor: 'rgba(99, 102, 241, 0.12)',
                color: '#6366f1',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '1rem',
              }}
            >
              <UploadCloud size={32} />
            </div>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.5rem' }}>
              {isDragActive ? 'Drop your invoice files right here' : 'Drag & drop invoice files here'}
            </h3>
            <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginBottom: '1.25rem' }}>
              Supports PDF, JPG, PNG, and TIFF up to 25MB each
            </p>
            <button type="button" className="btn btn-secondary btn-sm">
              Browse Local Files
            </button>
          </div>

          {/* Files List / Bulk Queue */}
          {files.length > 0 && (
            <div className="card" style={{ marginTop: '1.5rem' }}>
              <div className="card-header">
                <div>
                  <h3 className="card-title">Upload Queue ({files.length})</h3>
                  <p className="card-subtitle">Ready for batch OCR ingestion</p>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    onClick={() => setFiles([])}
                    disabled={uploading}
                    className="btn btn-ghost btn-sm"
                  >
                    Clear All
                  </button>
                  <button
                    onClick={handleUploadAll}
                    disabled={uploading || files.every((f) => f.status === 'success')}
                    className="btn btn-primary btn-sm"
                  >
                    {uploading ? (
                      <>
                        <Loader2 size={15} className="animate-spin" />
                        Uploading...
                      </>
                    ) : (
                      <>
                        <UploadCloud size={15} />
                        Upload All
                      </>
                    )}
                  </button>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {files.map((item) => (
                  <div
                    key={item.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '0.85rem 1rem',
                      backgroundColor: 'rgba(15, 23, 42, 0.5)',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--card-border)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', minWidth: 0 }}>
                      {getFileIcon(item.type)}
                      <div style={{ minWidth: 0 }}>
                        <p
                          style={{
                            fontWeight: 500,
                            fontSize: '0.875rem',
                            color: '#f8fafc',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            maxWidth: '240px',
                          }}
                        >
                          {item.name}
                        </p>
                        <p style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                          {item.size} MB
                        </p>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      {item.status === 'pending' && (
                        <button
                          onClick={() => uploadSingleFile(item)}
                          disabled={uploading}
                          className="btn btn-secondary btn-sm"
                        >
                          Upload
                        </button>
                      )}

                      {item.status === 'uploading' && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <Loader2 size={16} color="#6366f1" className="animate-spin" />
                          <span style={{ fontSize: '0.8rem', color: '#a5b4fc' }}>{item.progress}%</span>
                        </div>
                      )}

                      {item.status === 'success' && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                          <span style={{ color: '#22c55e', display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.8rem', fontWeight: 600 }}>
                            <CheckCircle2 size={16} /> Processed
                          </span>
                          {item.invoiceId && (
                            <Link
                              to={`/invoices/${item.invoiceId}`}
                              className="btn btn-primary btn-sm"
                              style={{ padding: '0.25rem 0.55rem', fontSize: '0.75rem' }}
                            >
                              View <ArrowRight size={13} />
                            </Link>
                          )}
                        </div>
                      )}

                      {item.status === 'error' && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#ef4444', fontSize: '0.8rem' }}>
                          <AlertCircle size={16} /> Failed
                        </div>
                      )}

                      {item.status !== 'uploading' && (
                        <button
                          onClick={() => removeFile(item.id)}
                          className="btn btn-ghost btn-sm btn-icon"
                          title="Remove"
                        >
                          <X size={16} />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Instructions & Capabilities */}
        <div>
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <Info size={18} color="#6366f1" />
                Ingestion Specifications
              </h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontSize: '0.875rem', color: '#cbd5e1' }}>
              <div>
                <strong style={{ color: '#f8fafc', display: 'block', marginBottom: '0.25rem' }}>
                  Supported File Types
                </strong>
                <p style={{ color: '#94a3b8' }}>
                  Standard Adobe PDF, High-Resolution JPEG, PNG, and multi-page TIFF. Scanned invoices must be at least 200 DPI for optimal character extraction.
                </p>
              </div>

              <div style={{ borderTop: '1px solid var(--card-border)', paddingTop: '1rem' }}>
                <strong style={{ color: '#f8fafc', display: 'block', marginBottom: '0.25rem' }}>
                  Automated OCR Pipeline
                </strong>
                <p style={{ color: '#94a3b8' }}>
                  Once uploaded, documents trigger the asynchronous Tesseract OCR engine. Extracted fields include Invoice Number, PO Reference, GSTIN, Date, Item Details, and Tax breakdown.
                </p>
              </div>

              <div style={{ borderTop: '1px solid var(--card-border)', paddingTop: '1rem' }}>
                <strong style={{ color: '#f8fafc', display: 'block', marginBottom: '0.25rem' }}>
                  Multi-Page & Bulk Support
                </strong>
                <p style={{ color: '#94a3b8' }}>
                  You can drop up to 50 invoices simultaneously. Each document will receive its own isolated tracking pipeline and audit log.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InvoiceCapture;
