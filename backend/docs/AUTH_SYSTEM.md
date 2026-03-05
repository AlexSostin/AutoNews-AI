# 🔐 Authentication & User Management System

## Система ролей

### 👤 Роли пользователей

1. **Гость** (не авторизован):
   - Чтение статей
   - Комментирование (с именем/email)
   - Рейтинги

2. **Зарегистрированный пользователь**:
   - Все функции гостя +
   - Личный кабинет (/profile)
   - Favorites (в разработке)
   - История комментариев (в разработке)

3. **Администратор** (is_staff=True):
   - Все функции пользователя +
   - Доступ к Admin панели
   - Создание/редактирование статей
   - Модерация контента

---

## 🎯 Header - Умная навигация

### Для ГОСТЕЙ

```
🚗 AutoNews | Home | Articles | Categories | 🔍 | 👤 Login
```

### Для ПОЛЬЗОВАТЕЛЕЙ

```
🚗 AutoNews | Home | Articles | Categories | 🔍 | 👤 Username ▼
                                                    └─ My Profile
                                                    └─ Favorites
                                                    └─ Logout
```

### Для АДМИНОВ

```
🚗 AutoNews | Home | Articles | Categories | 🔍 | ⚙️ Admin | 👤 Username ▼
```

**Кнопка Admin показывается ТОЛЬКО если:**

- `user.is_staff === true`
- ИЛИ `user.is_superuser === true`

---

## 🔒 Безопасность

### Защита роутов

**Frontend (middleware.ts):**

- `/admin/*` - требует авторизации
- `/profile/*` - требует авторизации
- Редирект на `/login?redirect=...`

**Backend (permissions):**

- `IsAuthenticated` - только для залогиненных
- `IsAdminUser` - только для staff/superuser (16 эндпоинтов)
- JWT токены в cookies (HttpOnly-like)

### Brute-Force Protection

- **django-axes**: 5 неудачных попыток → блокировка на 30 минут
- Rate limiting: 5 попыток логина за 15 минут на IP
- Логирование всех попыток (success/fail с IP адресом)

### JWT Instant Logout

- `POST /auth/logout/` — черный список refresh токена
- Мгновенное отключение доступа (не ждать истечения access token)

### Хранение данных

```typescript
// Токены в cookies (безопасно)
document.cookie = `access_token=${token}; path=/; max-age=3600; SameSite=Strict`;

// Данные пользователя в localStorage (удобно)
localStorage.setItem('user', JSON.stringify(userData));
```

---

## 🔐 Двухфакторная аутентификация (2FA)

### Как работает

1. **Админ включает 2FA**: `POST /auth/2fa/setup/` → получает QR-код
2. **Сканирует QR**: Google Authenticator / Authy / любое TOTP-приложение
3. **Подтверждает**: `POST /auth/2fa/confirm/` с первым кодом → получает 8 backup-кодов

### Логин с 2FA (два шага)

```
Шаг 1: POST /token/ → {requires_2fa: true}  (токены НЕ выдаются)
Шаг 2: POST /auth/2fa/verify/ + {username, password, totp_code} → {access, refresh}
```

### API Endpoints

```bash
POST /api/v1/auth/2fa/setup/       # QR-код для authenticator
POST /api/v1/auth/2fa/confirm/     # Подтверждение + backup коды
POST /api/v1/auth/2fa/verify/      # Верификация при логине
POST /api/v1/auth/2fa/disable/     # Отключение (требует код)
GET  /api/v1/auth/2fa/status/      # Проверка статуса
```

### Backup коды

- 8 одноразовых кодов (hex, 8 символов)
- Хранятся в БД захешированными (SHA256)
- Каждый код можно использовать только один раз

---

## 📁 Структура файлов

### Frontend

```
frontend-next/
├── lib/
│   └── auth.ts              # Функции авторизации
├── app/
│   ├── login/page.tsx       # Страница входа
│   ├── profile/
│   │   ├── page.tsx         # Личный кабинет
│   │   └── favorites/
│   │       └── page.tsx     # Избранное
│   └── admin/               # Админ-панель
└── components/public/
    └── Header.tsx           # Умная навигация
```

### Backend

```
backend/news/
├── api_views/
│   ├── two_factor.py       # 2FA API (setup, confirm, verify, disable, status)
│   └── ...
├── api_urls.py             # Роутинг API + 2FA endpoints
├── models/system.py        # TOTPDevice модель
└── serializers.py          # User serialization
```

---

## 🚀 API Endpoints

### Авторизация

```bash
POST /api/v1/token/          # Логин (получить токены / requires_2fa)
POST /api/v1/token/refresh/  # Обновить access token
POST /api/v1/auth/logout/    # Instant logout (JWT blacklist)
```

### 2FA

```bash
POST /api/v1/auth/2fa/setup/     # Генерация QR кода
POST /api/v1/auth/2fa/confirm/   # Подтверждение 2FA
POST /api/v1/auth/2fa/verify/    # Верификация при логине
POST /api/v1/auth/2fa/disable/   # Отключение
GET  /api/v1/auth/2fa/status/    # Статус
```

### Пользователь

```bash
GET /api/v1/users/me/        # Получить данные текущего пользователя
```

**Response:**

```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_staff": true,
  "is_superuser": false,
  "date_joined": "2026-01-15T10:30:00Z"
}
```

---

## ✅ Функции авторизации (lib/auth.ts)

```typescript
// Проверка авторизации
isAuthenticated(): boolean

// Логин пользователя
login(credentials): Promise<AuthTokens>

// Выход
logout(): void

// Получить токен
getAccessToken(): string | null

// Получить текущего пользователя (API запрос)
getCurrentUser(token?): Promise<User | null>

// Получить пользователя из кеша
getUserFromStorage(): User | null

// Проверка админа
isAdmin(): boolean
```

---

## 📱 Личный кабинет (/profile)

### Текущие возможности

- ✅ Просмотр информации профиля
- ✅ Дата регистрации
- ✅ Email
- ✅ Статус администратора
- ✅ Смена пароля

### В разработке

- 🔄 Избранные статьи (Favorites)
- 🔄 История комментариев
- 🔄 Редактирование профиля
- 🔄 Email настройки

---

## ✨ Итого

**Реализовано:**

- ✅ Полноценная система авторизации
- ✅ Роли (Guest, User, Admin)
- ✅ Умная навигация в Header
- ✅ Личный кабинет
- ✅ Защита роутов
- ✅ JWT токены + instant logout
- ✅ API endpoint для пользователя
- ✅ Мобильная версия
- ✅ TOTP 2FA для админов

**Безопасность:**

- ✅ Admin кнопка только для is_staff
- ✅ Middleware защита
- ✅ Token в cookies
- ✅ Авто-редирект на login
- ✅ Brute-force protection (django-axes)
- ✅ IsAdminUser на 16 эндпоинтах
- ✅ 2FA с backup кодами
- ✅ Sensitive data scrubbing в error logs

**Готово к запуску!** 🚀
