import argparse
import os
import sys
import re

# Add ai_engine directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from modules.downloader import download_audio_and_thumbnail
from modules.transcriber import transcribe_from_youtube
from modules.analyzer import analyze_transcript
from modules.article_generator import generate_article
from modules.publisher import publish_article

def extract_title(html_content):
    match = re.search(r'<h2>(.*?)</h2>', html_content)
    if match:
        return match.group(1)
    return "New Car Review" 

def main(youtube_url):
    print(f"Starting pipeline for: {youtube_url}")
    
    # 1. Download
    # audio_path, thumbnail_path = download_audio_and_thumbnail(youtube_url)
    
    # 2. Transcribe
    # transcript = transcribe_audio(audio_path)
    
    # For testing without wasting API credits/Time, let's mock if needed
    # transcript = "Mock transcript..."
    
    # 3. Analyze
    # analysis = analyze_transcript(transcript)
    
    # 4. Generate Article
    # article_html = generate_article(analysis)
    
    # Mocking for demonstration since we don't have API keys set up
    article_html = "<h2>2026 Future Car Review</h2><p>This is a generated article with a mockup image.</p>"
    
    # 5. Publish
    title = extract_title(article_html)
    
    # Pass thumbnail_path if we had real download
    # publish_article(title, article_html, image_path=thumbnail_path)
    
    # Mock publish
    publish_article(title, article_html)
    
    print("Pipeline finished.")

def generate_article_from_youtube(youtube_url):
    """
    Generate article from YouTube URL and return article data
    Used by Django API
    """
    try:
        import time
        print(f"Generating article from: {youtube_url}")
        
        # Extract video ID for thumbnail
        video_id = youtube_url.split('v=')[-1].split('&')[0]
        
        # Generate unique title with timestamp
        timestamp = int(time.time())
        title = f"AI Generated Article from Video {timestamp}"
        summary = "This article was automatically generated from a YouTube video using AI technology. Full implementation with Groq AI will generate detailed automotive content when API keys are configured."
        
        article_html = f"""
        <h2>{title}</h2>
        <p class="lead">{summary}</p>
        
        <h3>Introduction</h3>
        <p>This article was automatically generated from the YouTube video. The AI analyzes the video content and creates a comprehensive article with images.</p>
        
        <img src="https://img.youtube.com/vi/{video_id}/maxresdefault.jpg" alt="Video thumbnail" style="width:100%; max-width:800px; margin:20px 0; border-radius:8px;" />
        
        <h3>Key Highlights</h3>
        <ul>
            <li>Detailed analysis of the video content</li>
            <li>Important points and takeaways</li>
            <li>Professional automotive insights</li>
        </ul>
        
        <img src="https://img.youtube.com/vi/{video_id}/hqdefault.jpg" alt="Video screenshot 1" style="width:100%; max-width:600px; margin:20px 0; border-radius:8px;" />
        
        <h3>In-Depth Review</h3>
        <p>Full AI generation with Groq will provide comprehensive automotive reviews, technical specifications, and expert analysis when API keys are configured.</p>
        
        <img src="https://img.youtube.com/vi/{video_id}/sddefault.jpg" alt="Video screenshot 2" style="width:100%; max-width:600px; margin:20px 0; border-radius:8px;" />
        
        <h3>Conclusion</h3>
        <p>Stay tuned for more AI-generated automotive content. This is just a preview of what's possible with the Groq AI integration.</p>
        """
        
        # Publish article with summary and youtube_url
        article = publish_article(title, article_html, summary=summary, youtube_url=youtube_url)
        
        return {
            'success': True,
            'article_id': article.id,
            'title': title
        }
    except Exception as e:
        print(f"Error generating article: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Auto News Generator")
    parser.add_argument("url", help="YouTube Video URL")
    args = parser.parse_args()
    
    main(args.url)
