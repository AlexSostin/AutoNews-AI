import logging
import json

logger = logging.getLogger(__name__)

def run_fact_check(article_html: str, web_context: str, provider: str = 'gemini', source_title: str = None) -> str:
    """
    Runs a secondary LLM pass to extract factual claims from the generated article
    and cross-reference them against the raw web context.
    If hallucinations are found, injects a warning banner into the HTML.
    """
    if not web_context or len(web_context.strip()) < 50:
        return article_html # No context to check against
        
    try:
        from ai_engine.modules.ai_provider import get_ai_provider
    except ImportError:
        from modules.ai_provider import get_ai_provider

    ai = get_ai_provider(provider)
    
    # Build entity verification section if source_title is provided
    entity_check_section = ""
    if source_title:
        entity_check_section = f"""
    5. CRITICAL: Verify the EXACT car model name. The original source title is: "{source_title}"
       - Check if the article uses the SAME model name and number as the source title.
       - If the article says "Leopard 7" but the source says "Leopard 8", this is a CRITICAL hallucination.
       - Model name/number mismatches are the HIGHEST PRIORITY issue to flag.
"""
    
    prompt = f"""
    You are an expert fact-checker. Your job is to verify the numerical claims in the ARTICLE against the provided WEB CONTEXT.
    
    WEB CONTEXT (Ground Truth):
    {web_context}
    
    ARTICLE TEXT TO VERIFY:
    {article_html}
    
    Instructions:
    1. Extract 3-5 key numerical claims from the ARTICLE (like Price, Horsepower, Range, Battery size, 0-100 km/h).
    2. Check if these claims are supported by the WEB CONTEXT.
    3. If a claim in the ARTICLE contradicts the WEB CONTEXT, or is completely fabricated (not found in context), flag it.
    4. Return your analysis as a JSON object with the following structure:
    {{
        "hallucinations_found": true/false,
        "issues": [
            "Article claims price is $20,000, but web context states it starts at $30,000.",
            "Article claims 500 HP, but this is not mentioned in the web context."
        ]
    }}
{entity_check_section}
    Respond ONLY with valid JSON. Do not include markdown formatting like ```json or any other text.
    """
    
    system_prompt = "You are a strict fact-checking AI. You only output valid parseable JSON."
    
    try:
        response = ai.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=1000
        )
        
        # Clean response to ensure it's parseable JSON
        clean_json = response.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
            
        result = json.loads(clean_json.strip())
        
        if result.get('hallucinations_found') and result.get('issues'):
            print(f"⚠️ Fact-check detected issues: {result['issues']}")
            
            # Formulate the warning HTML
            issues_list = "".join(f"<li>{issue}</li>" for issue in result['issues'])
            warning_html = f"""
            <div class="ai-editor-note" style="background-color: #fef0f0; border-left: 4px solid #f56c6c; padding: 15px; margin-bottom: 20px;">
                <h4 style="color: #f56c6c; margin-top: 0;">⚠️ AI Fact-Check Warning</h4>
                <p>The following discrepancies were detected between the generated text and the web sources:</p>
                <ul>{issues_list}</ul>
                <p><em>Please review and correct these numbers before publishing.</em></p>
            </div>
            """
            
            # Inject at the very top of the article
            return warning_html + article_html
            
        return article_html
        
    except Exception as e:
        logger.error(f"Fact-checking failed: {e}")
        print(f"⚠️ Fact-checking failed: {e}. Skipping validation.")
        return article_html
