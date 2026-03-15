from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

class ArticleCopilotMixin:
    """
    Mixin for ArticleViewSet providing AI Copilot capabilities.
    Allows editing specific chunks of text using AI prompts.
    """
    
    @action(detail=True, methods=['post'])
    def ai_edit_chunk(self, request, slug=None):
        """
        POST /api/v1/articles/<slug>/ai_edit_chunk/
        Body:
        {
            "text": "<p>The piece of text to edit</p>",
            "instruction": "Make this sound more professional"
        }
        """
        article = self.get_object()
        
        selected_text = request.data.get('text', '').strip()
        instruction = request.data.get('instruction', '').strip()
        article_context = request.data.get('context', {})
        
        if not selected_text:
            return Response({'error': 'No text provided for editing.'}, status=status.HTTP_400_BAD_REQUEST)
            
        if not instruction:
            return Response({'error': 'No instruction provided.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # We use Gemini explicitly as agreed in our architecture
            try:
                from ai_engine.modules.ai_provider import get_generate_provider
            except ImportError:
                import sys
                import os
                sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
                from ai_engine.modules.ai_provider import get_generate_provider
                
            ai = get_generate_provider()
            
            system_prompt = (
                "You are an expert automotive editor and copywriter. "
                "Your task is to modify the provided text exactly according to the user's instructions. "
                "CRITICAL RULES: "
                "1. Return ONLY the final edited text. "
                "2. NO conversational filler (e.g., 'Here is the edited text:', 'Sure!'). "
                "3. Preserve the original HTML formatting tags (like <p>, <strong>, <h2>) unless instructed otherwise. "
                "4. If the input has no HTML tags, return plain text."
            )
            
            if article_context:
                system_prompt += (
                    "\n\n--- FULL ARTICLE CONTEXT FOR REFERENCE ---\n"
                    f"Title: {article_context.get('title', 'N/A')}\n"
                    f"Tags: {', '.join(article_context.get('tags', []))}\n"
                    f"Summary: {article_context.get('summary', 'N/A')}\n"
                    "You MUST NOT rewrite the full article. You MUST ONLY rewrite the specific 'ORIGINAL TEXT' you are given below, "
                    "using the knowledge from the full article context if it helps."
                )
            
            prompt = f"INSTRUCTION: {instruction}\n\nORIGINAL TEXT:\n{selected_text}"
            
            result = ai.generate_completion(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=800
            )
            
            if not result:
                return Response({'error': 'AI failed to generate a response.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
            # Clean up potential markdown formatting that Gemini might wrap around HTML
            result = result.strip()
            if result.startswith("```html"):
                result = result[7:]
            if result.startswith("```"):
                result = result[3:]
            if result.endswith("```"):
                result = result[:-3]
                
            result = result.strip()
            
            return Response({
                'success': True,
                'edited_text': result,
                'original_text': selected_text
            })
            
        except Exception as e:
            logger.error(f"[AI Copilot] Error editing chunk: {str(e)}", exc_info=True)
            return Response({'error': f"AI Edit failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
