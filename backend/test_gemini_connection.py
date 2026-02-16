
import os
from google import genai
from dotenv import load_dotenv

# Load env variables
load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
print(f"Checking API Key: {api_key[:10]}...{api_key[-5:] if api_key else 'None'}")

if not api_key:
    print("❌ API Key not found in .env")
    exit(1)

client = genai.Client(api_key=api_key)

print("\nListing available models...")
try:
    for m in client.models.list():
        print(f" - {m.name}")
except Exception as e:
    print(f"❌ Failed to list models: {e}")

print("\nAttempting generation with 'gemini-2.0-flash'...")
try:
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents="Hello, can you hear me?"
    )
    print(f"✅ Success! Response: {response.text}")
except Exception as e:
    print(f"❌ Failed 'gemini-2.0-flash': {e}")
    
print("\nAttempting generation with 'gemini-1.5-flash'...")
try:
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents="Hello, can you hear me?"
    )
    print(f"✅ Success! Response: {response.text}")
except Exception as e:
    print(f"❌ Failed 'gemini-1.5-flash': {e}")
