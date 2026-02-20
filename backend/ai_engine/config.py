import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Optional, not used by default
GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # Main AI provider (free, fast)

# AI Provider: 'groq' (recommended) or 'openai'
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "ai_engine", "output")

TRANSCRIPTS_DIR = os.path.join(OUTPUT_DIR, "transcripts")
ARTICLES_DIR = os.path.join(OUTPUT_DIR, "articles")
LOGS_DIR = os.path.join(OUTPUT_DIR, "logs")

# Module Settings
WHISPER_MODEL = "whisper-1"  # OpenAI Whisper (optional)
GROQ_MODEL = "llama-3.3-70b-versatile"  # Main model (Jan 2026)
LLM_MODEL = "gpt-4-turbo"  # OpenAI GPT (optional)

# Pexels API Configuration (Free image search)
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
PEXELS_ENABLED = bool(PEXELS_API_KEY)
PEXELS_IMAGE_SIZE = "large"  # large, medium, small, original

