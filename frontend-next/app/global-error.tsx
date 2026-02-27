'use client';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html>
      <body>
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#f3f4f6',
          padding: '1rem'
        }}>
          <div style={{
            maxWidth: '32rem',
            width: '100%',
            backgroundColor: 'white',
            borderRadius: '1rem',
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
            padding: '2rem',
            textAlign: 'center'
          }}>
            <h1 style={{
              fontSize: '1.5rem',
              fontWeight: 'bold',
              color: '#1f2937',
              marginBottom: '1rem'
            }}>
              Something went wrong
            </h1>
            <p style={{
              color: '#6b7280',
              marginBottom: '1.5rem'
            }}>
              A critical error occurred. Please reload the page.
            </p>
            <button
              onClick={() => reset()}
              style={{
                background: 'linear-gradient(to right, #4f46e5, #7c3aed)',
                color: 'white',
                padding: '0.75rem 1.5rem',
                borderRadius: '0.5rem',
                fontWeight: '600',
                border: 'none',
                cursor: 'pointer',
                marginRight: '0.5rem'
              }}
            >
              Try Again
            </button>
            <a
              href="/"
              style={{
                display: 'inline-block',
                background: '#e5e7eb',
                color: '#374151',
                padding: '0.75rem 1.5rem',
                borderRadius: '0.5rem',
                fontWeight: '600',
                textDecoration: 'none'
              }}
            >
              Go Home
            </a>
          </div>
        </div>
      </body>
    </html>
  );
}
