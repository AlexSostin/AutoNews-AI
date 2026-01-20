import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  
  // Настройка отслеживания производительности
  tracesSampleRate: 0.1, // 10% запросов для production
  
  // Отладка в dev режиме
  debug: false,
  
  // Среда выполнения
  environment: process.env.NODE_ENV || 'development',
  
  // Повторные попытки отправки
  replaysOnErrorSampleRate: 1.0,
  replaysSessionSampleRate: 0.1,
  
  integrations: [
    Sentry.replayIntegration({
      maskAllText: true,
      blockAllMedia: true,
    }),
  ],
});
