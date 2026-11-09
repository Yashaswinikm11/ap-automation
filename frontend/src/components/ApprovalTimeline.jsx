import React from 'react';
import {
  FileUp,
  ScanText,
  ShieldCheck,
  GitCompare,
  UserCheck,
  CreditCard,
  Check,
  X,
  Clock,
} from 'lucide-react';

const DEFAULT_STEPS = [
  { id: 'uploaded', label: 'Invoice Ingestion', icon: FileUp, desc: 'Original file uploaded & stored' },
  { id: 'extracted', label: 'OCR & Parsing', icon: ScanText, desc: 'Tesseract OCR field extraction' },
  { id: 'validated', label: 'Rule Validation', icon: ShieldCheck, desc: 'Math check, GST & duplicate rules' },
  { id: 'matched', label: 'PO Matching', icon: GitCompare, desc: '2-way or 3-way line item match' },
  { id: 'approved', label: 'Manager Approval', icon: UserCheck, desc: 'Multi-level workflow approval' },
  { id: 'paid', label: 'Payment Release', icon: CreditCard, desc: 'Bank disbursement & reconciliation' },
];

const ApprovalTimeline = ({ currentStatus = 'uploaded', actions = [], customSteps }) => {
  const steps = customSteps || DEFAULT_STEPS;

  const getStepStatus = (stepId, index) => {
    const statusOrder = ['uploaded', 'extracted', 'validated', 'matched', 'approved', 'paid'];
    const currentIdx = statusOrder.indexOf(currentStatus);
    const targetIdx = statusOrder.indexOf(stepId);

    if (currentStatus === 'rejected') {
      if (stepId === 'approved') return 'rejected';
      return targetIdx < 4 ? 'completed' : 'pending';
    }

    if (currentIdx === -1) {
      return index === 0 ? 'completed' : 'pending';
    }

    if (targetIdx < currentIdx) return 'completed';
    if (targetIdx === currentIdx) return 'active';
    return 'pending';
  };

  return (
    <div className="timeline">
      {steps.map((step, index) => {
        const state = getStepStatus(step.id, index);
        const Icon = step.icon;

        return (
          <div key={step.id} className={`timeline-step ${state}`}>
            <div className="timeline-dot">
              {state === 'completed' ? (
                <Check size={13} strokeWidth={3} />
              ) : state === 'rejected' ? (
                <X size={13} strokeWidth={3} />
              ) : state === 'active' ? (
                <Clock size={13} />
              ) : (
                index + 1
              )}
            </div>

            <div style={{ marginLeft: '0.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontWeight: 600, fontSize: '0.9rem', color: state === 'pending' ? 'var(--muted)' : 'var(--text)' }}>
                  {step.label}
                </span>
                {state === 'active' && (
                  <span className="badge badge-pending" style={{ fontSize: '0.7rem', padding: '0.1rem 0.45rem' }}>
                    In Progress
                  </span>
                )}
                {state === 'completed' && (
                  <span className="badge badge-validated" style={{ fontSize: '0.7rem', padding: '0.1rem 0.45rem' }}>
                    Completed
                  </span>
                )}
                {state === 'rejected' && (
                  <span className="badge badge-rejected" style={{ fontSize: '0.7rem', padding: '0.1rem 0.45rem' }}>
                    Rejected
                  </span>
                )}
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--muted)', marginTop: '0.2rem' }}>
                {step.desc}
              </p>

              {/* Show associated actions if any */}
              {actions
                .filter((a) => a.step === step.id)
                .map((action, aIdx) => (
                  <div
                    key={aIdx}
                    style={{
                      marginTop: '0.4rem',
                      padding: '0.4rem 0.6rem',
                      background: 'rgba(15, 23, 42, 0.6)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.775rem',
                      borderLeft: '2px solid var(--primary)',
                    }}
                  >
                    <strong>{action.user || 'Approver'}</strong>: {action.comments || action.decision}
                  </div>
                ))}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default ApprovalTimeline;
