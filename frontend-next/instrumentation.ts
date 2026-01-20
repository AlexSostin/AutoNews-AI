export async function register() {
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    await import('./sentry.server.config');
  }

  if (process.env.NEXT_RUNTIME === 'edge') {
    await import('./sentry.edge.config');
  }
}

export const onRequestError = async (err: unknown, request: {
  path: string;
  method: string;
  headers: { [key: string]: string | string[] | undefined };
}) => {
  await import('@sentry/nextjs').then(({ captureException }) => {
    captureException(err, {
      extra: {
        path: request.path,
        method: request.method,
      },
    });
  });
};
