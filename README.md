# 🚗 AutoNews - AI-Powered Automotive News Platform

![Django](https://img.shields.io/badge/Django-6.0.1-green)
![Python](https://img.shields.io/badge/Python-3.13-blue)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)

**AutoNews** is an automated automotive news platform that generates high-quality articles from YouTube videos using AI. The system automatically downloads content, transcribes audio, analyzes information, and publishes beautifully formatted articles with images, specifications, and interactive features.

## ✨ Features

### 🤖 AI-Powered Content Generation
- **Automatic Article Creation** - Generate articles from YouTube URLs in ~15 seconds
- **Smart Video Analysis** - Extracts car specifications, brands, models, and features
- **3 Screenshot Extraction** - Automatically captures key moments (15%, 50%, 85% timestamps)
- **Subtitle Transcription** - Uses yt-dlp for accurate subtitle extraction
- **Groq AI Integration** - Powered by llama-3.3-70b-versatile model
- **Clean Title Processing** - Removes HTML entities and formats properly

### 📰 Content Management
- **9 Categories** - News, Reviews, EVs, Technology, Industry, Classics, Motorsport, Modifications, Comparisons
- **95 Automotive Tags** - Comprehensive tagging system (brands, types, technologies, features)
- **Car Specifications** - Automatic extraction of make, model, year, horsepower, torque, 0-60, top speed
- **Image Gallery** - Carousel with multiple screenshots per article
- **Rich Text Editor** - HTML content with proper formatting

### 🎨 Modern Design
- **Purple Gradient Theme** - Consistent design across all pages (#667eea → #764ba2)
- **Hero Section** - Eye-catching landing page with featured articles
- **Clickable Cards** - Entire article cards are clickable with hover effects
- **Responsive Layout** - Mobile-friendly Bootstrap 5 design
- **Social Icons** - Real favicons for Facebook, X, WhatsApp, Telegram, Instagram, YouTube, LinkedIn
- **Dropdown Navigation** - Organized categories in header dropdown

### 💬 Interactive Features
- **Comments System** - Users can leave feedback on articles
- **5-Star Ratings** - Rate articles and see average ratings
- **Search Functionality** - Full-text search across articles
- **Share Buttons** - Facebook, X (Twitter), WhatsApp, Telegram with real icons
- **Avatar Comments** - First letter circles for comment authors

### 💰 Monetization Ready
- **Google AdSense Integration** - Pre-configured ad placements
- **5 Ad Positions** - Top banner, in-article, in-content (auto), content bottom, sidebar
- **Automatic In-Content Ads** - JavaScript auto-inserts ads after 2nd and 4th h2 sections
- **Comprehensive Guide** - AD_SETUP_GUIDE.md with revenue estimates and setup instructions

### 📄 Legal Pages
- **Privacy Policy** - GDPR-compliant privacy page
- **Contact Form** - Beautiful contact page with social links
- **About Page** - Company information

## 🛠️ Tech Stack

### Backend
- **Django 6.0.1** - Web framework
- **Python 3.13.3** - Programming language
- **SQLite** - Database (easily upgradeable to PostgreSQL)
- **Channels 4.2.1** - WebSocket support (partial implementation)
- **Daphne 4.2.1** - ASGI server

### AI & Media Processing
- **Groq API** - AI text generation (llama-3.3-70b-versatile)
- **yt-dlp** - YouTube video/subtitle extraction
- **FFmpeg 8.0.1** - Video screenshot extraction
- **Gemini API** - Backup AI model

### Frontend
- **Bootstrap 5.3.0** - Responsive framework
- **Font Awesome** - Icons (via CDN)
- **Google Favicons API** - Social media icons
- **Custom CSS** - Gradient themes and animations

### Admin
- **Django Jazzmin** - Beautiful admin interface
- **Custom Admin Actions** - Generate articles directly from admin panel

## 📋 Requirements

- Python 3.13+
- FFmpeg (for video processing)
- Groq API Key (free tier available)
- Optional: Gemini API Key (backup)

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/Auto_News.git
cd Auto_News
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install FFmpeg
**Windows:**
- Download from https://ffmpeg.org/download.html
- Add to PATH

**Linux:**
```bash
sudo apt install ffmpeg
```

**Mac:**
```bash
brew install ffmpeg
```

### 5. Configure API Keys
Create `ai_engine/config.py`:
```python
GROQ_API_KEY = "your_groq_api_key_here"
GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_API_KEY = "your_gemini_api_key_here"  # Optional backup
```

**Get API Keys:**
- Groq: https://console.groq.com/ (Free tier: 30 requests/minute)
- Gemini: https://makersuite.google.com/app/apikey (Optional)

### 6. Run Migrations
```bash
python manage.py migrate
```

### 7. Create Superuser
```bash
python manage.py createsuperuser
```

### 8. Create Categories and Tags
```bash
python create_categories.py
python create_tags.py
```

### 9. Run Development Server
```bash
python manage.py runserver 8001
```

Visit: http://127.0.0.1:8001

## 📖 Usage

### Generate Article from Admin Panel
1. Login to admin: http://127.0.0.1:8001/admin
2. Go to **News → Articles**
3. Click **"Add Article"**
4. Paste YouTube URL in **"YouTube URL"** field
5. Click **"Save"** - article generates automatically in ~15 seconds
6. View published article on homepage

### Generate Article from Command Line
```bash
python ai_engine/main.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Features Generated Automatically:
✅ Article title (cleaned and formatted)  
✅ Full article content (HTML formatted)  
✅ 3 screenshots from video  
✅ Car specifications (make, model, year, horsepower, etc.)  
✅ Category assignment  
✅ Tag assignment  
✅ SEO-friendly slug  

## 📁 Project Structure

```
Auto_News/
├── ai_engine/              # AI article generation engine
│   ├── config.py          # API keys configuration
│   ├── main.py            # Main orchestrator
│   └── modules/
│       ├── downloader.py  # YouTube download & screenshot extraction
│       ├── transcriber.py # Subtitle extraction
│       ├── analyzer.py    # Car spec extraction
│       ├── article_generator.py  # AI article generation
│       ├── publisher.py   # Database publication
│       └── utils.py       # Helper functions
├── auto_news_site/        # Django project settings
├── news/                  # Main Django app
│   ├── models.py         # Article, Category, Tag, Comment, Rating, CarSpec
│   ├── views.py          # All page views
│   ├── admin.py          # Admin interface with AI integration
│   └── urls.py           # URL routing
├── templates/             # HTML templates
│   ├── base.html         # Base template with header/footer
│   ├── news/
│   │   ├── home.html     # Homepage with hero section
│   │   ├── article_detail.html  # Article page with all features
│   │   ├── privacy.html  # Privacy policy
│   │   └── contact.html  # Contact page
│   └── ads/              # Ad templates
├── static/               # CSS, JS, images
├── media/                # Uploaded images
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## 🎨 Customization

### Change Theme Colors
Edit `templates/base.html` and search for gradient colors:
```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```
Replace with your colors.

### Add More Categories
Edit `create_categories.py` and run:
```bash
python create_categories.py
```

### Modify AI Prompts
Edit prompts in:
- `ai_engine/modules/article_generator.py` - Article generation
- `ai_engine/modules/analyzer.py` - Specification extraction

### Configure Ad Placements
1. Get AdSense code from https://www.google.com/adsense
2. Edit templates in `templates/ads/`
3. See `AD_SETUP_GUIDE.md` for detailed instructions

## 💰 Monetization

The platform is **monetization-ready** with:
- **5 ad positions** pre-configured
- **Automatic in-content ads** (JavaScript injection)
- **AdSense guide** with revenue estimates

**Estimated Revenue** (Google AdSense):
- 10k visitors/month: $50-150
- 50k visitors/month: $300-800

See [AD_SETUP_GUIDE.md](AD_SETUP_GUIDE.md) for complete setup instructions.

## 🔒 Security Notes

**Before Production:**
1. Change `SECRET_KEY` in `settings.py`
2. Set `DEBUG = False`
3. Configure `ALLOWED_HOSTS`
4. Use PostgreSQL instead of SQLite
5. Set up HTTPS/SSL
6. Never commit `config.py` with API keys
7. Use environment variables for secrets

## 📄 License

MIT License - feel free to use for commercial projects!

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 🐛 Known Issues

- WebSocket real-time progress not fully functional (task_id passing)
- Some videos without subtitles use fallback (title + description)

## 📞 Support

- **Issues**: Open a GitHub issue
- **Documentation**: See `GEMINI_SETUP.md` and `AD_SETUP_GUIDE.md`

## 🌟 Acknowledgments

- **Groq** - Fast AI inference
- **yt-dlp** - YouTube extraction
- **FFmpeg** - Video processing
- **Django** - Web framework
- **Bootstrap** - UI framework

---

Made with ❤️ for automotive enthusiasts

**Star ⭐ this repo if you find it useful!**
