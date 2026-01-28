import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN || "https://87d896ae25bc56da5e80115c2c1364da@o4510742370648064.ingest.de.sentry.io/4510742712746064",
  
  // Browser tracing integration
  integrations: [
    Sentry.browserTracingIntegration(),
    Sentry.replayIntegration({
      maskAllText: true,
      blockAllMedia: true,
    }),
  ],
  
  // Trace propagation targets
  tracePropagationTargets: ["localhost", /^https:\/\/yourserver\.io\/api/],
  
  // Настройка отслеживания производительности
  tracesSampleRate: 1.0, // 100% для development, 0.1 для production
  
  // Session replay
  replaysOnErrorSampleRate: 1.0,
  replaysSessionSampleRate: 0.1,
  
  // Отладка в dev режиме
  debug: false,
  
  // Среда выполнения
  environment: process.env.NODE_ENV || 'development',
});
