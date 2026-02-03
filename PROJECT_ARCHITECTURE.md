# AutoNews-AI Project Architecture

This document provides a comprehensive overview of the AutoNews-AI project structure, technology stack, and core workflows. It is designed to help AI assistants and developers understand how the system works.

## 🚀 Technology Stack

### Backend
- **Framework**: Django 5.x / Django REST Framework (DRF)
- **Language**: Python 3.12+
- **Database**: PostgreSQL (Production), SQLite (Local/Development)
- **Task Queue/Cache**: Redis
- **AI Integration**: Groq (Llama 3), Google Gemini (Pro/Flash)
- **APIs**: YouTube Data API v3, Google Search Console API
- **Monitoring**: Sentry (Error tracking)

### Frontend
- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript / JavaScript
- **Styling**: Vanilla CSS (Premium custom design)
- **State Management**: React Context, Local Storage
- **Dashboard**: Custom implementation based on modern UI principles

---

## 📂 Project Structure

### Root Directory
```text
/
├── backend/            # Django Application
├── frontend/           # Next.js Application
├── .gemini/            # Antigravity brain and task history
└── docker-compose.yml  # Container orchestration
```

### Backend Structure (`/backend`)
- **`auto_news_site/`**: Main Django settings, URL routing, and WSGI/ASGI config.
- **`news/`**: Core application logic.
    - `models.py`: Database schema (Article, Category, Tag, YouTubeChannel, PendingArticle, etc.).
    - `api_views.py`: DRF ViewSets for frontend endpoints.
    - `serializers.py`: Data transformation layer between models and JSON.
    - `signals.py`: Automatic notifications and triggers.
    - `image_utils.py`: WebP optimization and resizing logic.
- **`ai_engine/`**: The "Brain" of the application.
    - `main.py`: Orchestration logic for generating articles content.
    - `modules/`: Specialized AI tools.
        - `transcriber.py`: YouTube transcript retrieval (yt-dlp + oEmbed fallback).
        - `analyzer.py`: LLM-based content extraction and car specs parsing.
        - `publisher.py`: Tools for saving generated content into models.
- **`manage.py`**: Django entry point.

### Frontend Structure (`/frontend`)
- **`app/`**: Next.js App Router folders.
    - `(public)/`: Publicly accessible news site pages.
    - `admin/`: Secured administrative dashboard.
    - `api/`: Frontend-side API routes (e.g., Auth proxies).
- **`components/`**: Reusable UI components.
- **`context/`**: React Context providers (Auth, Theme).
- **`styles/`**: Custom CSS modules and global variables.

---

## 🔧 Core Workflows

### 1. AI Article Generation
1. **Trigger**: Manual scan in dashboard or automatic schedule.
2. **Channel Monitoring**: Fetches latest videos from monitored YouTube channels.
3. **Transcription**: `transcriber.py` fetches subtitles or uses oEmbed metadata fallback if blocked.
4. **Analysis**: LLM (Groq/Gemini) analyzes the transcript to extract car specs, pros/cons, and write a summary.
5. **Pending State**: Created as a `PendingArticle` for manual review.
6. **Approval**: Admin reviews and publishes, converting it into a live `Article`.

### 2. Auto-Optimization
- **Images**: All uploaded or AI-generated images are automatically converted to WebP and resized via `optimize_image` in `models.py:Article.save`.
- **Slugs**: Automatic SEO-friendly slug generation for articles, categories, and tags.

### 3. SEO & Analytics
- **Dynamic SEO**: Meta titles and descriptions are automatically generated based on AI analysis.
- **GSC Integration**: Fetches real-time search performance data (clicks, impressions) via Google Search Console API.

---

## 🔒 Security & Environment
- **Environment Variables**: Managed via `.env` (API keys, DB credentials, SMTP).
- **Authentication**: JWT-based (Django SimpleJWT) with secure HTTP-only cookie handling on the frontend.
- **Roles**: Staff-only access for administration and AI generation triggers.

## 📋 Important Configuration
- **`YOUTUBE_COOKIES_CONTENT`**: Used by `yt-dlp` to bypass YouTube sign-in/bot blocks.
- **`GROQ_API_KEY` / `GEMINI_API_KEY`**: Required for AI content generation.
- **`GSC_KEY_JSON`**: Service account credentials for Search Console integration.
