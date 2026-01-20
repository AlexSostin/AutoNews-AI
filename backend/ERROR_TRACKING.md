# Система отслеживания ошибок (Sentry)

## Что это дает?

**Sentry** - это система мониторинга ошибок, которая позволяет:

✅ **Автоматически получать уведомления** о всех ошибках на сайте  
✅ **Видеть stack trace** - где именно произошла ошибка  
✅ **Отслеживать действия пользователя** перед ошибкой (breadcrumbs)  
✅ **Группировать похожие ошибки** для анализа  
✅ **Получать контекст** - браузер, устройство, URL, пользователь  

### Без Sentry:
- Вы узнаёте об ошибках только когда пользователи жалуются
- Нет информации о том, что привело к ошибке
- Сложно воспроизвести проблему

### С Sentry:
- Все ошибки приходят в реальном времени
- Полная информация для быстрого исправления
- Можно отслеживать, сколько пользователей затронуто

## Настройка

### 1. Создание аккаунта

1. Зайдите на [sentry.io](https://sentry.io)
2. Создайте бесплатный аккаунт (до 5000 событий/месяц бесплатно)
3. Создайте новый проект:
   - Platform: **Next.js** (для frontend)
   - Platform: **Django** (для backend)

### 2. Получение DSN

После создания проекта вы получите **DSN** (Data Source Name) - это URL для отправки ошибок.

Выглядит примерно так:
```
https://examplePublicKey@o0.ingest.sentry.io/0
```

### 3. Настройка Frontend

Добавьте в `.env.local`:
```env
NEXT_PUBLIC_SENTRY_DSN=ваш_dsn_от_sentry
```

Или в `docker-compose.yml` для frontend:
```yaml
environment:
  - NEXT_PUBLIC_SENTRY_DSN=ваш_dsn_от_sentry
```

### 4. Настройка Backend

Добавьте в `backend/.env`:
```env
SENTRY_DSN=ваш_dsn_от_sentry
```

## Использование

### Автоматическое отслеживание

Все необработанные ошибки **автоматически** попадают в Sentry:

```typescript
// Эта ошибка автоматически логируется
throw new Error('Что-то пошло не так!');
```

### Ручное логирование

Используйте утилиты из `lib/errorTracking.ts`:

```typescript
import { logError, addBreadcrumb, setUserContext } from '@/lib/errorTracking';

// Логирование ошибки с контекстом
try {
  await fetchData();
} catch (error) {
  logError(error as Error, {
    level: 'error',
    tags: { feature: 'articles', action: 'fetch' },
    extra: { articleId: '123' }
  });
}

// Добавление breadcrumb (хлебные крошки)
addBreadcrumb('User clicked favorite button', 'user-action', { 
  articleId: '456' 
});

// Установка пользователя (делается после логина)
setUserContext({
  id: user.id,
  email: user.email,
  username: user.username,
  is_staff: user.is_staff
});
```

### Интеграция с логином

Обновите `lib/auth.ts` для отслеживания пользователя:

```typescript
import { setUserContext, clearUserContext } from './errorTracking';

export const login = async (credentials: LoginCredentials) => {
  // ... код логина
  
  const userData = await getCurrentUser(access);
  if (userData) {
    localStorage.setItem('user', JSON.stringify(userData));
    
    // Добавить пользователя в Sentry
    setUserContext({
      id: userData.id.toString(),
      email: userData.email,
      username: userData.username,
      is_staff: userData.is_staff
    });
  }
  
  return { access, refresh };
};

export const logout = () => {
  // ... код выхода
  
  // Очистить пользователя из Sentry
  clearUserContext();
  
  window.location.href = '/login';
};
```

## Примеры использования

### 1. Логирование ошибок API

```typescript
const fetchArticles = async () => {
  try {
    const response = await fetch('/api/articles');
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    logError(error as Error, {
      tags: { api: 'articles' },
      extra: { endpoint: '/api/articles' }
    });
    throw error;
  }
};
```

### 2. Отслеживание действий пользователя

```typescript
const handleFavorite = async (articleId: string) => {
  addBreadcrumb('User favorited article', 'user-action', { articleId });
  
  try {
    await addToFavorites(articleId);
  } catch (error) {
    logError(error as Error, {
      tags: { feature: 'favorites', action: 'add' },
      extra: { articleId }
    });
  }
};
```

### 3. Логирование предупреждений

```typescript
if (!user.email) {
  logError('User has no email', {
    level: 'warning',
    tags: { validation: 'user-data' },
    extra: { userId: user.id }
  });
}
```

## Проверка работы

### Способ 1: Вручную вызвать ошибку

Создайте страницу `/test-error`:

```typescript
// app/test-error/page.tsx
'use client';

export default function TestError() {
  return (
    <button onClick={() => {
      throw new Error('Test Sentry error!');
    }}>
      Вызвать тестовую ошибку
    </button>
  );
}
```

### Способ 2: Проверить в консоли Sentry

1. Зайдите на [sentry.io](https://sentry.io)
2. Откройте ваш проект
3. Перейдите в **Issues** - там должны появиться ошибки

## Преимущества

| До Sentry | С Sentry |
|-----------|----------|
| ❌ Узнаете об ошибках от пользователей | ✅ Получаете уведомления в реальном времени |
| ❌ Нет stack trace | ✅ Полный stack trace с номерами строк |
| ❌ Не знаете, как воспроизвести | ✅ Видите все действия пользователя |
| ❌ Нужно логировать вручную | ✅ Автоматический сбор всех ошибок |
| ❌ Сложно понять масштаб проблемы | ✅ Статистика: сколько пользователей затронуто |

## Стоимость

- **Бесплатно**: до 5,000 событий/месяц
- **Developer ($29/мес)**: 50,000 событий
- **Team ($80/мес)**: 100,000 событий

Для небольшого проекта бесплатного плана более чем достаточно!

## Альтернативы Sentry

- **LogRocket** - записывает видео действий пользователя
- **Bugsnag** - похож на Sentry
- **Rollbar** - проще в настройке
- **New Relic** - полный мониторинг производительности

Sentry - самый популярный и удобный для большинства проектов.
