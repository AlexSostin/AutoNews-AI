# AutoNews Next.js - Техническое Задание

## 📋 Обзор проекта

Современный автомобильный новостной портал с интегрированной админ-панелью на Next.js 15 с TypeScript и App Router.

**Цель:** Создать единое приложение, где публичный сайт и админ-панель находятся в одном Next.js проекте с чистой структурой роутинга.

---

## 🏗️ Структура проекта

```
frontend-next/
├── src/
│   ├── app/
│   │   ├── layout.tsx                    # Корневой layout
│   │   ├── page.tsx                      # Главная страница (/)
│   │   ├── globals.css                   # Глобальные стили
│   │   │
│   │   ├── articles/
│   │   │   ├── page.tsx                  # Список статей
│   │   │   └── [slug]/
│   │   │       └── page.tsx              # Детальная страница статьи
│   │   │
│   │   ├── categories/
│   │   │   └── [slug]/
│   │   │       └── page.tsx              # Статьи по категории
│   │   │
│   │   ├── search/
│   │   │   └── page.tsx                  # Поиск статей
│   │   │
│   │   ├── login/
│   │   │   └── page.tsx                  # Страница входа
│   │   │
│   │   └── admin/
│   │       ├── layout.tsx                # Layout админки
│   │       ├── page.tsx                  # Dashboard
│   │       ├── articles/
│   │       │   ├── page.tsx              # Список статей (управление)
│   │       │   ├── new/
│   │       │   │   └── page.tsx          # Создание статьи
│   │       │   └── [id]/
│   │       │       └── edit/
│   │       │           └── page.tsx      # Редактирование статьи
│   │       ├── categories/
│   │       │   └── page.tsx              # Управление категориями
│   │       ├── tags/
│   │       │   └── page.tsx              # Управление тегами
│   │       └── comments/
│   │           └── page.tsx              # Модерация комментариев
│   │
│   ├── components/
│   │   ├── public/                       # Компоненты публичного сайта
│   │   │   ├── Header.tsx                # Хедер с навигацией
│   │   │   ├── Footer.tsx                # Футер
│   │   │   ├── ArticleCard.tsx           # Карточка статьи
│   │   │   ├── CategoryNav.tsx           # Навигация по категориям
│   │   │   ├── SearchBar.tsx             # Поиск
│   │   │   ├── CommentSection.tsx        # Секция комментариев
│   │   │   └── RatingStars.tsx           # Рейтинг статьи
│   │   │
│   │   └── admin/                        # Компоненты админки
│   │       ├── Sidebar.tsx               # Боковое меню
│   │       ├── AdminHeader.tsx           # Хедер админки
│   │       ├── StatsCard.tsx             # Карточка статистики
│   │       ├── ArticleForm.tsx           # Форма статьи
│   │       ├── RichTextEditor.tsx        # Редактор контента
│   │       ├── ImageUpload.tsx           # Загрузка изображений
│   │       └── DataTable.tsx             # Таблица данных
│   │
│   ├── lib/
│   │   ├── api.ts                        # Axios instance с перехватчиками
│   │   ├── auth.ts                       # Функции авторизации
│   │   ├── hooks.ts                      # React Query hooks
│   │   └── utils.ts                      # Вспомогательные функции
│   │
│   ├── types/
│   │   └── index.ts                      # TypeScript типы
│   │
│   └── middleware.ts                     # Защита admin роутов
│
├── public/
│   └── images/
│
├── .env.local                            # Переменные окружения
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

---

## 🔌 Backend API (Django REST)

**Base URL:** `http://127.0.0.1:8001/api/v1/`

### Endpoints для публичного сайта:

#### Статьи
```typescript
GET /articles/
Response: {
  count: number,
  next: string | null,
  previous: string | null,
  results: Article[]
}

GET /articles/{slug}/
Response: Article

Article {
  id: number,
  title: string,
  slug: string,
  summary: string,
  content: string,
  image: string | null,
  thumbnail_url: string | null,
  youtube_url: string,
  category: number,
  category_name: string,
  tags: number[],
  tag_names: string[],
  average_rating: number,
  rating_count: number,
  created_at: string,
  updated_at: string,
  is_published: boolean,
  seo_title: string,
  seo_description: string,
  specs: CarSpecification | null,
  gallery: ArticleImage[],
  comments: Comment[]
}

CarSpecification {
  id: number,
  model_name: string,
  engine: string,
  horsepower: string,
  torque: string,
  zero_to_sixty: string,
  top_speed: string,
  price: string,
  release_date: string
}

ArticleImage {
  id: number,
  image: string,
  image_url: string,
  caption: string,
  order: number
}
```

#### Категории
```typescript
GET /categories/
Response: Category[]

Category {
  id: number,
  name: string,
  slug: string,
  article_count: number
}
```

#### Теги
```typescript
GET /tags/
Response: Tag[]

Tag {
  id: number,
  name: string,
  slug: string,
  article_count: number
}
```

#### Комментарии
```typescript
GET /comments/?article={article_id}
Response: Comment[]

POST /comments/
Body: {
  article: number,
  author_name: string,
  author_email: string,
  content: string
}

Comment {
  id: number,
  article: number,
  author_name: string,
  author_email: string,
  content: string,
  created_at: string,
  is_approved: boolean
}
```

#### Рейтинг
```typescript
POST /ratings/
Body: {
  article: number,
  rating: number (1-5),
  user_ip: string
}
```

#### Поиск
```typescript
GET /articles/?search={query}
GET /articles/?category={category_id}
GET /articles/?tags={tag_id}
GET /articles/?ordering=-created_at
```

### Endpoints для админки:

#### Авторизация
```typescript
POST /auth/login/
Body: { username: string, password: string }
Response: { access: string, refresh: string }

POST /auth/token/refresh/
Body: { refresh: string }
Response: { access: string }
```

#### CRUD статей (требуют JWT)
```typescript
POST /articles/
PUT /articles/{id}/
PATCH /articles/{id}/
DELETE /articles/{id}/

Headers: {
  Authorization: 'Bearer {access_token}'
}
```

#### CRUD категорий/тегов
```typescript
POST /categories/
PUT /categories/{id}/
DELETE /categories/{id}/

POST /tags/
PUT /tags/{id}/
DELETE /tags/{id}/
```

#### Модерация комментариев
```typescript
PATCH /comments/{id}/
Body: { is_approved: boolean }

DELETE /comments/{id}/
```

---

## 🛠️ Технологический стек

### Обязательные пакеты:

```json
{
  "dependencies": {
    "next": "^15.1.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "typescript": "^5.7.0",
    "@tanstack/react-query": "^5.62.0",
    "axios": "^1.7.0",
    "react-hook-form": "^7.54.0",
    "zod": "^3.24.0",
    "@hookform/resolvers": "^3.9.0",
    "lucide-react": "^0.469.0",
    "date-fns": "^4.1.0",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.5.0"
  },
  "devDependencies": {
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "@types/node": "^22.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0"
  }
}
```

### Опциональные (для улучшения UX):
- `react-hot-toast` - уведомления
- `framer-motion` - анимации
- `@tiptap/react` - rich text editor
- `react-dropzone` - drag&drop для изображений

---

## ⚙️ Конфигурация

### `next.config.js`
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: '127.0.0.1',
        port: '8001',
        pathname: '/media/**',
      },
    ],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8001/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
```

### `.env.local`
```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8001/api/v1
NEXT_PUBLIC_MEDIA_URL=http://127.0.0.1:8001/media
```

### `tailwind.config.ts`
```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f5f7ff',
          500: '#667eea',
          600: '#5a67d8',
          700: '#4c51bf',
        },
        secondary: {
          500: '#764ba2',
        }
      },
    },
  },
  plugins: [],
};
export default config;
```

---

## 🔐 Авторизация и защита роутов

### `src/middleware.ts`
```typescript
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('access_token')?.value;
  const isAdminRoute = request.nextUrl.pathname.startsWith('/admin');
  const isLoginRoute = request.nextUrl.pathname === '/login';

  // Если админский роут и нет токена - редирект на login
  if (isAdminRoute && !token) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  // Если есть токен и пытается зайти на login - редирект в админку
  if (isLoginRoute && token) {
    return NextResponse.redirect(new URL('/admin', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/admin/:path*', '/login'],
};
```

### `src/lib/api.ts`
```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Добавляем токен к каждому запросу
api.interceptors.request.use(
  (config) => {
    if (typeof window !== 'undefined') {
      const token = document.cookie
        .split('; ')
        .find(row => row.startsWith('access_token='))
        ?.split('=')[1];
      
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Обработка ошибок и рефреш токена
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = document.cookie
          .split('; ')
          .find(row => row.startsWith('refresh_token='))
          ?.split('=')[1];

        if (refreshToken) {
          const response = await axios.post(
            `${process.env.NEXT_PUBLIC_API_URL}/auth/token/refresh/`,
            { refresh: refreshToken }
          );

          const { access } = response.data;
          document.cookie = `access_token=${access}; path=/; max-age=3600; SameSite=Strict`;

          originalRequest.headers.Authorization = `Bearer ${access}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        // Токен устарел - редирект на login
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
```

---

## 📱 Основные компоненты

### Публичный сайт - Header
```typescript
// src/components/public/Header.tsx
'use client';

import Link from 'next/link';
import { Search, Menu } from 'lucide-react';
import SearchBar from './SearchBar';
import CategoryNav from './CategoryNav';

export default function Header() {
  return (
    <header className="bg-gradient-to-r from-primary-500 to-secondary-500 text-white shadow-lg">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between py-4">
          <Link href="/" className="text-2xl font-bold">
            🚗 AutoNews
          </Link>
          
          <nav className="hidden md:flex space-x-6">
            <Link href="/" className="hover:text-primary-200">Home</Link>
            <Link href="/articles" className="hover:text-primary-200">Articles</Link>
            <Link href="/admin" className="hover:text-primary-200">Admin</Link>
          </nav>

          <SearchBar />
        </div>
        
        <CategoryNav />
      </div>
    </header>
  );
}
```

### Админка - Sidebar
```typescript
// src/components/admin/Sidebar.tsx
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  FileText, 
  Folder, 
  Tag, 
  MessageSquare,
  LogOut 
} from 'lucide-react';

const menuItems = [
  { href: '/admin', icon: LayoutDashboard, label: 'Dashboard' },
  { href: '/admin/articles', icon: FileText, label: 'Articles' },
  { href: '/admin/categories', icon: Folder, label: 'Categories' },
  { href: '/admin/tags', icon: Tag, label: 'Tags' },
  { href: '/admin/comments', icon: MessageSquare, label: 'Comments' },
];

export default function Sidebar() {
  const pathname = usePathname();

  const handleLogout = () => {
    document.cookie = 'access_token=; path=/; max-age=0';
    document.cookie = 'refresh_token=; path=/; max-age=0';
    window.location.href = '/login';
  };

  return (
    <aside className="w-64 bg-gray-900 text-white min-h-screen">
      <div className="p-6">
        <h2 className="text-2xl font-bold">AutoNews Admin</h2>
      </div>
      
      <nav className="mt-6">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-6 py-3 transition-colors ${
                isActive ? 'bg-primary-600 text-white' : 'hover:bg-gray-800'
              }`}
            >
              <Icon size={20} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <button
        onClick={handleLogout}
        className="flex items-center gap-3 px-6 py-3 mt-auto hover:bg-gray-800 w-full"
      >
        <LogOut size={20} />
        Logout
      </button>
    </aside>
  );
}
```

---

## 🎨 Дизайн требования

### Публичный сайт:
- Современный адаптивный дизайн
- Градиентные хедеры (фиолетовый #667eea → #764ba2)
- Карточки статей с hover эффектами
- Красивые типографские стили для контента статей
- Мобильная навигация с бургер-меню
- Lazy loading изображений

### Админка:
- Темная боковая панель
- Светлая рабочая область
- Карточки статистики на дашборде
- Таблицы с пагинацией и сортировкой
- Формы с валидацией
- Toast уведомления для действий

---

## 🚀 Этапы реализации

### Phase 1: Базовая структура (День 1)
1. Инициализация Next.js проекта
2. Настройка Tailwind CSS
3. Создание структуры папок
4. Настройка API клиента и авторизации
5. Middleware для защиты роутов

### Phase 2: Публичный сайт (День 1-2)
1. Главная страница со списком статей
2. Страница детальной статьи
3. Страницы категорий
4. Поиск
5. Комментарии и рейтинг
6. Header, Footer, навигация

### Phase 3: Админ панель (День 2-3)
1. Layout админки (Sidebar + Header)
2. Dashboard с статистикой
3. Список статей с CRUD
4. Форма создания/редактирования статьи
5. Rich text editor
6. Загрузка изображений
7. Управление категориями/тегами
8. Модерация комментариев

### Phase 4: Полировка (День 3)
1. SEO оптимизация (metadata, Open Graph)
2. Loading states и skeleton screens
3. Error boundaries
4. Toast notifications
5. Анимации
6. Тестирование всех функций

---

## 📝 Важные замечания

1. **SSR vs CSR:** 
   - Публичные страницы используют SSR для SEO
   - Админка использует CSR для интерактивности

2. **Кэширование:**
   - React Query с staleTime: 5 минут
   - Revalidate страниц: 60 секунд

3. **Безопасность:**
   - httpOnly cookies для токенов
   - CSRF защита через SameSite
   - Валидация на клиенте и сервере

4. **Производительность:**
   - Image optimization через Next.js Image
   - Dynamic imports для тяжелых компонентов
   - Debounce для поиска

5. **UX:**
   - Оптимистичные обновления в админке
   - Loading indicators везде
   - Понятные сообщения об ошибках

---

## 🎯 Критерии успеха

✅ Единый Next.js проект с публичным сайтом и админкой  
✅ Красивый современный дизайн  
✅ Полная интеграция с Django REST API  
✅ JWT авторизация работает корректно  
✅ Все CRUD операции функционируют  
✅ SEO оптимизация (metadata, sitemap)  
✅ Адаптивный дизайн (mobile, tablet, desktop)  
✅ Быстрая загрузка страниц  
✅ Отсутствие ошибок в консоли  
✅ TypeScript без any типов  

---

## 📞 Для запуска

```bash
# Установка зависимостей
npm install

# Разработка
npm run dev

# Production build
npm run build
npm start
```

**Порты:**
- Frontend: `http://localhost:3000`
- Backend API: `http://127.0.0.1:8001`

---

**ВАЖНО:** Весь функционал должен работать без переключения между вкладками. Это единое SPA с роутингом Next.js.
