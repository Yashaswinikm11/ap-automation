import React from 'react';

const STATUS_CONFIG = {
  uploaded: {
    label: 'Uploaded',
    className: 'badge-uploaded',
  },
  extracted: {
    label: 'OCR Extracted',
    className: 'badge-extracted',
  },
  validated: {
    label: 'Validated',
    className: 'badge-validated',
  },
  pending_approval: {
    label: 'Pending Approval',
    className: 'badge-pending_approval',
  },
  approved: {
    label: 'Approved',
    className: 'badge-approved',
  },
  rejected: {
    label: 'Rejected',
    className: 'badge-rejected',
  },
  paid: {
    label: 'Paid',
    className: 'badge-paid',
  },
  // PO / Matching statuses
  matched: {
    label: '2-Way Matched',
    className: 'badge-matched',
  },
  exception: {
    label: 'Exception',
    className: 'badge-exception',
  },
  unmatched: {
    label: 'Unmatched',
    className: 'badge-unmatched',
  },
  // Payment / Request statuses
  pending: {
    label: 'Pending',
    className: 'badge-pending_approval',
  },
  processing: {
    label: 'Processing',
    className: 'badge-extracted',
  },
  failed: {
    label: 'Failed',
    className: 'badge-rejected',
  },
  verified: {
    label: 'Verified',
    className: 'badge-approved',
  },
};

const StatusBadge = ({ status, label: customLabel }) => {
  const normalized = (status || '').toLowerCase().replace(/\s+/g, '_');
  const config = STATUS_CONFIG[normalized] || {
    label: customLabel || status || 'Unknown',
    className: 'badge-unmatched',
  };

  return (
    <span className={`badge ${config.className}`}>
      <span className="badge-dot" />
      {customLabel || config.label}
    </span>
  );
};

export default StatusBadge;
