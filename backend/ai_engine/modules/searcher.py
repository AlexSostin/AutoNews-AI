
import requests
from googlesearch import search
from bs4 import BeautifulSoup
import time
import random

def search_car_details(make, model, year=None):
    """
    Searches for car details and reviews on the web.
    Returns structured text with key info found.
    """
    # Construct query
    query = f"{year if year else ''} {make} {model} specs review price release date"
    print(f"🌐 Searching web for: {query}...")
    
    search_results = []
    
    try:
        # Search Google (gets top 5 URLs)
        urls = list(search(query, num_results=5, advanced=True))
        
        for result in urls:
            try:
                # Basic scraping of title and snippet provided by google search
                # Note: googlesearch-python advanced=True returns SearchResult objects
                # But sometimes it's flaky. Let's stick to safe iteration.
                
                title = result.title
                desc = result.description
                url = result.url
                
                # Check if it's a useful site (skip youtube, reddit sometimes)
                if 'youtube.com' in url:
                    continue
                    
                search_results.append(f"Source: {title} ({url})\nSummary: {desc}\n")
                
            except:
                continue
                
        if not search_results:
            return "No relevant web results found."
            
        return "\n".join(search_results[:4])
        
    except Exception as e:
        print(f"⚠️ Search failed: {e}")
        return f"Web search failed: {str(e)}"

def get_web_context(specs_dict):
    """
    Helper to get context string for AI based on specs
    """
    make = specs_dict.get('make')
    model = specs_dict.get('model')
    year = specs_dict.get('year')
    
    if make == 'Not specified' or model == 'Not specified':
        return ""
        
    results = search_car_details(make, model, year)
    return f"\n\n[WEB SEARCH RESULTS FOR CONTEXT]:\n{results}\n"
