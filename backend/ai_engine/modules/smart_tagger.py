import json
import logging
from typing import List
from django.db.models import Prefetch

logger = logging.getLogger(__name__)

def assign_tags(article_title: str, article_content: str) -> List[int]:
    """
    Intelligently assigns relevant Tag IDs to an article based on its content.
    Reads all available tags from the database and uses an LLM to select the most
    appropriate ones (up to 5-7 tags), preventing false positives.
    
    Returns:
        List of integer primary keys for the selected Tags.
    """
    try:
        from news.models import Tag
        from ai_engine.modules.ai_provider import get_light_provider
        from ai_engine.modules.utils import parse_ai_response
    except ImportError as e:
        logger.error(f"Imports failed in smart_tagger: {e}")
        return []

    # 1. Fetch and group all available tags
    tags = Tag.objects.select_related('group').all()
    if not tags.exists():
        return []

    grouped_tags = {}
    for tag in tags:
        group_name = tag.group.name if tag.group else "General"
        if group_name not in grouped_tags:
            grouped_tags[group_name] = []
        grouped_tags[group_name].append(f'"{tag.name}" (ID: {tag.id})')

    # Format tags for the prompt
    tags_context = ""
    for group, tags_list in grouped_tags.items():
        if group.lower() == "year" or group.lower() == "years":
            continue  # We do not want the AI to select year tags
        tags_context += f"\n[{group}]\n"
        tags_context += ", ".join(tags_list) + "\n"

    # 2. Build the prompts
    system_prompt = (
        "You are an expert Automotive SEO tagger. Your job is to read an article and "
        "select a CONCISE and HIGHLY RELEVANT set of tags from a strictly provided database list.\n\n"
        "RULES:\n"
        "1. DO NOT invent new tags. You must ONLY use the exact IDs provided in the list.\n"
        "2. MAXIMUM 8 TAGS. Less is more. A perfect tagging is usually 4-6 tags: Brand, Model, Body Type, Powertrain, and 1-2 major standout features.\n"
        "3. EXCLUDE COMPETITORS: Do NOT select brand or model tags for competitor vehicles mentioned in passing.\n"
        "4. EXCLUDE UMBRELLA TERMS: Do not use generic tags like 'Technology', 'Design', 'Interior', 'Performance', 'Market' unless the entire article is an analysis of that specific broad topic.\n"
        "5. EXACT POWERTRAIN: A 'PHEV' is NOT a 'BEV' or 'Electric'. If a car is fully electric, MUST include the 'BEV' tag. Do not include 'EV' and 'Electric' if 'BEV' is selected (avoid redundancy).\n"
        "6. PRICE & SEGMENT: 'Budget' and 'Affordable' mean the same thing, pick one. Do not tag a sub-$25k car as 'Premium'.\n"
        "7. You must structure your reasoning and final selection using the required JSON format."
    )

    safe_content = str(article_content)[:8000]

    user_prompt = f"""
AVAILABLE TAGS BY CATEGORY:
{tags_context}

ARTICLE TITLE: {article_title}

ARTICLE CONTENT:
{safe_content}

Analyze the article and output a JSON object with the following structure:
{{
  "analysis": {{
    "primary_vehicle": "MAIN brand and MAIN model discussed",
    "competitors_to_ignore": "Other brands/models mentioned in passing",
    "powertrain_exact": "PHEV, BEV, ICE? Will apply strict BEV tag if fully electric.",
    "redundancy_check": "Checking that we aren't selecting EV+Electric+BEV together, or Budget+Affordable together"
  }},
  "quality_control": {{
    "total_target_tags": "Must be <= 8",
    "umbrella_tags_removed": "Confirmed removal of 'Design', 'Tech', etc."
  }},
  "selected_tag_ids": [int, int, int]
}}
Ensure the output is ONLY this valid JSON object, no markdown fences or other text.
"""

    # 3. Call the AI Provider
    ai = get_light_provider()
    try:
        result = ai.generate_completion(
            prompt=user_prompt.strip(),
            system_prompt=system_prompt,
            temperature=0.1,  # Low temperature for strict analytical extraction
            max_tokens=1500,  # Accommodate CoT reasoning and large ID arrays
            caller='smart_tagger'
        )
        
        if not result:
            return []
            
        parsed_data = parse_ai_response(result.strip())
        
        tag_ids = []
        if isinstance(parsed_data, dict):
            tag_ids = parsed_data.get("selected_tag_ids", [])
            logger.info(f"Smart Tagger Analysis: {parsed_data.get('analysis')}")
            logger.info(f"Smart Tagger QC: {parsed_data.get('quality_control')}")
        elif isinstance(parsed_data, list):
            # Fallback if it returned just the list
            tag_ids = parsed_data
        
        # Validation
        if isinstance(tag_ids, list):
            valid_ids = []
            for tid in tag_ids:  # No hard cap
                try:
                    valid_ids.append(int(tid))
                except (ValueError, TypeError):
                    pass
                    
            logger.info(f"Smart Tagger selected IDs: {valid_ids}")
            return valid_ids
            
        return []

    except json.JSONDecodeError as e:
        logger.error(f"Smart Tagger failed to parse JSON: {e} | Raw output: {result}")
        return []
    except Exception as e:
        logger.error(f"Smart Tagger failed: {e}")
        return []
