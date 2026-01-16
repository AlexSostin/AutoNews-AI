import argparse
from modules.downloader import download_audio_and_thumbnail
from modules.transcriber import transcribe_audio
from modules.analyzer import analyze_transcript
from modules.article_generator import generate_article
from modules.publisher import publish_article
import re

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Auto News Generator")
    parser.add_argument("url", help="YouTube Video URL")
    args = parser.parse_args()
    
    main(args.url)
