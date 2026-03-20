'use client';

import { useGenerationStore, GenerationStep } from '@/lib/useGenerationStore';
import Link from 'next/link';

// ── Step definitions ──────────────────────────────────────────────────────────
const STEPS: { key: GenerationStep; label: string; icon: string; pct: number }[] = [
  { key: 'starting',   label: 'Starting',           icon: '🚀', pct: 5  },
  { key: 'transcript', label: 'Transcript fetched',  icon: '📝', pct: 20 },
  { key: 'facts',      label: 'Facts extracted',     icon: '🎬', pct: 35 },
  { key: 'writing',    label: 'Writing article',     icon: '✍️', pct: 60 },
  { key: 'factcheck',  label: 'Fact-check',          icon: '🕵️', pct: 75 },
  { key: 'review',     label: 'Self-review',         icon: '🔍', pct: 85 },
  { key: 'quality',    label: 'Quality gate',        icon: '🚦', pct: 93 },
  { key: 'saving',     label: 'Saving',              icon: '💾', pct: 98 },
  { key: 'done',       label: 'Done!',               icon: '✅', pct: 100 },
];

const STEP_ORDER = STEPS.map(s => s.key);

function stepIndex(step: GenerationStep): number {
  return STEP_ORDER.indexOf(step);
}

export default function GenerationDrawer() {
  const {
    isRunning, label, progress, step,
    articleSlug, errorMessage, backendMessage,
    minimized, dismiss, toggleMinimize,
  } = useGenerationStore();

  // Only show when active (running, done, error, timeout)
  const visible = isRunning || step === 'done' || step === 'error' || step === 'timeout';
  if (!visible) return null;

  const isError = step === 'error' || step === 'timeout';
  const isDone = step === 'done';

  // ── Pill (minimized) ──────────────────────────────────────────────────────
  if (minimized) {
    return (
      <button
        onClick={toggleMinimize}
        title="Click to expand generation progress"
        style={{
          position: 'fixed', bottom: '24px', right: '24px', zIndex: 9999,
          display: 'flex', alignItems: 'center', gap: '10px',
          background: isError ? '#ef4444' : isDone ? '#10b981' : '#4f46e5',
          color: '#fff',
          border: 'none', borderRadius: '999px',
          padding: '10px 18px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
          cursor: 'pointer',
          fontSize: '14px', fontWeight: 600,
          transition: 'all 0.2s',
          maxWidth: '280px',
        }}
      >
        <span style={{ animation: isRunning ? 'spin 1.2s linear infinite' : 'none' }}>
          {isError ? '❌' : isDone ? '✅' : '⚙️'}
        </span>
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '160px' }}>
          {isError ? 'Generation failed'
            : isDone ? 'Done! Click to view'
            : `${progress}% — ${label || 'Generating...'}`}
        </span>
        <span style={{ opacity: 0.8, fontSize: '12px' }}>▲</span>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </button>
    );
  }

  // ── Full drawer ───────────────────────────────────────────────────────────
  const currentIdx = stepIndex(step);

  return (
    <div
      id="generation-drawer"
      style={{
        position: 'fixed', bottom: '24px', right: '24px', zIndex: 9999,
        width: '340px',
        background: '#1e1b4b',
        border: '1px solid rgba(255,255,255,0.12)',
        borderRadius: '16px',
        boxShadow: '0 8px 40px rgba(0,0,0,0.5)',
        color: '#f1f5f9',
        fontFamily: 'system-ui, sans-serif',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 16px',
        background: isError ? 'rgba(239,68,68,0.2)'
          : isDone ? 'rgba(16,185,129,0.2)'
          : 'rgba(99,102,241,0.25)',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{
            display: 'inline-block',
            animation: isRunning ? 'spin 1.4s linear infinite' : 'none',
            fontSize: '16px',
          }}>
            {isError ? '❌' : isDone ? '✅' : '⚙️'}
          </span>
          <span style={{ fontSize: '14px', fontWeight: 700, letterSpacing: '-0.01em' }}>
            {isError ? 'Generation Failed'
              : isDone ? 'Generation Complete'
              : 'Generating Article...'}
          </span>
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            onClick={toggleMinimize}
            title="Minimize"
            style={{
              background: 'rgba(255,255,255,0.1)', border: 'none',
              borderRadius: '6px', color: '#94a3b8',
              cursor: 'pointer', padding: '2px 8px', fontSize: '14px',
            }}
          >▼</button>
          <button
            onClick={dismiss}
            title="Dismiss"
            style={{
              background: 'rgba(255,255,255,0.1)', border: 'none',
              borderRadius: '6px', color: '#94a3b8',
              cursor: 'pointer', padding: '2px 8px', fontSize: '14px',
            }}
          >✕</button>
        </div>
      </div>

      {/* Label */}
      {label && (
        <div style={{
          padding: '8px 16px 4px',
          fontSize: '12px', color: '#94a3b8',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {label}
        </div>
      )}

      {/* Error message */}
      {isError && errorMessage && (
        <div style={{
          margin: '8px 16px', padding: '10px 12px',
          background: 'rgba(239,68,68,0.15)',
          border: '1px solid rgba(239,68,68,0.3)',
          borderRadius: '8px',
          fontSize: '13px', color: '#fca5a5', lineHeight: 1.5,
        }}>
          {errorMessage}
        </div>
      )}

      {/* Steps list */}
      {!isError && (
        <div style={{ padding: '10px 16px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {STEPS.slice(0, -1).map(({ key, label: stepLabel, icon }, i) => {
            const done = i < currentIdx;
            const active = i === currentIdx;
            return (
              <div key={key} style={{
                display: 'flex', alignItems: 'center', gap: '10px',
                opacity: (done || active) ? 1 : 0.35,
                fontSize: '13px',
                transition: 'opacity 0.3s',
              }}>
                <span style={{ width: '20px', textAlign: 'center', fontSize: '14px' }}>
                  {done ? '✅' : active ? icon : '○'}
                </span>
                <span style={{
                  color: active ? '#c7d2fe' : done ? '#86efac' : '#64748b',
                  fontWeight: active ? 600 : 400,
                }}>
                  {stepLabel}
                </span>
                {active && (
                  <span style={{ marginLeft: 'auto', fontSize: '11px', color: '#818cf8', maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {backendMessage || 'running…'}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Progress bar */}
      {!isError && (
        <div style={{ padding: '0 16px 4px' }}>
          <div style={{
            height: '4px', borderRadius: '4px',
            background: 'rgba(255,255,255,0.1)',
            overflow: 'hidden',
          }}>
            <div style={{
              height: '100%',
              width: `${progress}%`,
              borderRadius: '4px',
              background: isDone
                ? 'linear-gradient(90deg, #10b981, #34d399)'
                : 'linear-gradient(90deg, #6366f1, #818cf8)',
              transition: 'width 0.6s ease',
            }} />
          </div>
          <div style={{ textAlign: 'right', fontSize: '11px', color: '#64748b', marginTop: '3px' }}>
            {progress}%
          </div>
        </div>
      )}

      {/* Footer */}
      <div style={{
        padding: '10px 16px 14px',
        display: 'flex', gap: '8px',
        borderTop: '1px solid rgba(255,255,255,0.06)',
      }}>
        {isDone && articleSlug && (
          <Link
            href={`/admin/articles/${articleSlug}/edit`}
            onClick={dismiss}
            style={{
              display: 'inline-block',
              padding: '7px 14px',
              background: 'linear-gradient(135deg, #10b981, #059669)',
              color: '#fff',
              textDecoration: 'none',
              borderRadius: '8px',
              fontSize: '13px', fontWeight: 600,
              flex: 1, textAlign: 'center',
            }}
          >
            ✏️ Edit Article
          </Link>
        )}
        {(isDone || isError) && (
          <button
            onClick={dismiss}
            style={{
              padding: '7px 14px',
              background: 'rgba(255,255,255,0.08)',
              border: '1px solid rgba(255,255,255,0.12)',
              color: '#94a3b8',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '13px',
              flex: isDone && articleSlug ? 0 : 1,
            }}
          >
            Dismiss
          </button>
        )}
        {isRunning && (
          <div style={{
            flex: 1, display: 'flex', alignItems: 'center', gap: '6px',
            fontSize: '12px', color: '#6366f1',
          }}>
            <span style={{ animation: 'pulse 1.5s ease-in-out infinite' }}>●</span>
            You can navigate away — this will continue in the background
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  );
}
