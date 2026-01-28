import * as Sentry from '@sentry/nextjs';

/**
 * Логирование ошибок в Sentry с дополнительным контекстом
 */
export const logError = (
  error: Error | string,
  context?: {
    level?: 'fatal' | 'error' | 'warning' | 'info' | 'debug';
    tags?: Record<string, string>;
    extra?: Record<string, any>;
    user?: {
      id?: string;
      email?: string;
      username?: string;
    };
  }
) => {
  console.error('Error logged:', error, context);

  if (typeof error === 'string') {
    Sentry.captureMessage(error, {
      level: context?.level || 'error',
      tags: context?.tags,
      extra: context?.extra,
      user: context?.user,
    });
  } else {
    Sentry.captureException(error, {
      level: context?.level || 'error',
      tags: context?.tags,
      extra: context?.extra,
      user: context?.user,
    });
  }
};

/**
 * Установка пользовательского контекста для всех последующих ошибок
 */
export const setUserContext = (user: {
  id?: string;
  email?: string;
  username?: string;
  is_staff?: boolean;
}) => {
  Sentry.setUser({
    id: user.id,
    email: user.email,
    username: user.username,
    is_staff: user.is_staff,
  });
};

/**
 * Очистка пользовательского контекста (при выходе)
 */
export const clearUserContext = () => {
  Sentry.setUser(null);
};

/**
 * Добавление breadcrumb (хлебные крошки для отслеживания действий пользователя)
 */
export const addBreadcrumb = (
  message: string,
  category?: string,
  data?: Record<string, any>
) => {
  Sentry.addBreadcrumb({
    message,
    category: category || 'user-action',
    level: 'info',
    data,
  });
};

/**
 * Установка тегов для группировки ошибок
 */
export const setErrorTags = (tags: Record<string, string>) => {
  Sentry.setTags(tags);
};
