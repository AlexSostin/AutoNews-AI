from groq import Groq
from ..config import GROQ_API_KEY, GROQ_MODEL

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

def analyze_transcript(transcript_text):
    """
    Analyzes the transcript to extract car details using Groq (super fast!).
    """
    print("Analyzing transcript with Groq...")
    
    prompt = f"""
Analyze this automotive video transcript and extract key information in STRUCTURED format.

Output format (use these EXACT labels):
Make: [Brand name]
Model: [Model name]
Year: [Year if mentioned, else estimate based on context]
Engine: [Engine type/size - e.g., "1.5L Turbo" or "Electric motor"]
Horsepower: [HP number - e.g., "300 HP"]
Torque: [Torque - e.g., "400 Nm"]
Acceleration: [0-60 or 0-100 time - e.g., "5.5 seconds"]
Top Speed: [Max speed - e.g., "155 mph"]
Battery: [Battery capacity for EVs - e.g., "75 kWh"]
Range: [Driving range - e.g., "400 km" or "250 miles"]
Price: [Starting price - e.g., "$45,000" or "€50,000"]

Key Features:
- [List main features]
- [Technology highlights]

Pros:
- [List advantages]

Cons:
- [List disadvantages]

Summary: [2-3 sentence overview]

Transcript:
{transcript_text[:15000]}

IMPORTANT: Use exact labels above. If info not available, write "Not specified".
"""
    
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert automotive analyst. Provide detailed, structured analysis."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        analysis = response.choices[0].message.content if response.choices else ""
        
        if not analysis:
            raise Exception("Groq returned empty analysis")
            
        print(f"Analysis complete. Length: {len(analysis)} characters")
        return analysis
    except Exception as e:
        print(f"Error during analysis: {e}")
        return ""
