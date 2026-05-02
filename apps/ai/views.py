import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from ai.services.ai_engine import process_query

logger = logging.getLogger('apps.ai')

@login_required
@require_POST
def chat_endpoint(request):
    """
    API endpoint for the chatbot.
    Expects JSON: {"message": "user question"}
    Returns JSON: {"reply": "AI response"}
    """
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '')
        
        if not user_message:
            return JsonResponse({'error': 'Message field is required.'}, status=400)
            
        # Call the AI engine with request context
        ai_response = process_query(user_message, request=request)
        
        return JsonResponse({'reply': ai_response})
        
    except json.JSONDecodeError:
        logger.warning("Invalid JSON received in chat endpoint")
        return JsonResponse({'error': 'Invalid JSON format.'}, status=400)
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return JsonResponse({'error': 'An internal error occurred.'}, status=500)
