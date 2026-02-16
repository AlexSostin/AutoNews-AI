
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load env variables
load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
print(f"Checking API Key: {api_key[:10]}...{api_key[-5:] if api_key else 'None'}")

if not api_key:
    print("❌ API Key not found in .env")
    exit(1)

genai.configure(api_key=api_key)

print("\nListing available models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f" - {m.name}")
except Exception as e:
    print(f"❌ Failed to list models: {e}")

print("\nAttempting generation with 'gemini-2.0-flash'...")
try:
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content("Hello, can you hear me?")
    print(f"✅ Success! Response: {response.text}")
except Exception as e:
    print(f"❌ Failed 'gemini-2.0-flash': {e}")
    
print("\nAttempting generation with 'gemini-1.5-flash'...")
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Hello, can you hear me?")
    print(f"✅ Success! Response: {response.text}")
except Exception as e:
    print(f"❌ Failed 'gemini-1.5-flash': {e}")
