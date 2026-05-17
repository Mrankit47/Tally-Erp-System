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
        language = data.get('language', 'English')
        
        if not user_message:
            return JsonResponse({'error': 'Message field is required.'}, status=400)
            
        # Call the AI engine with request context and language
        ai_response = process_query(user_message, request=request, language=language)
        
        return JsonResponse({'reply': ai_response})
        
    except json.JSONDecodeError:
        logger.warning("Invalid JSON received in chat endpoint")
        return JsonResponse({'error': 'Invalid JSON format.'}, status=400)
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return JsonResponse({'error': 'An internal error occurred.'}, status=500)


from django.shortcuts import get_object_or_404

@login_required
@require_POST
def resolve_audit_risk_api(request):
    """
    API endpoint for resolving / acknowledging a programmatic audit risk alert.
    """
    try:
        company = getattr(request, 'active_company', None)
        if not company:
            return JsonResponse({'error': 'No active company context.'}, status=400)
            
        data = json.loads(request.body)
        voucher_id = data.get('voucher_id')
        risk_type = data.get('risk_type')
        comments = data.get('comments', '')
        
        if not voucher_id or not risk_type:
            return JsonResponse({'error': 'Voucher ID and Risk Type are required fields.'}, status=400)
            
        from voucher.models import Voucher, AuditRiskResolution
        from django.core.cache import cache
        
        voucher = get_object_or_404(Voucher, id=voucher_id, company=company)
        
        resolution, created = AuditRiskResolution.objects.update_or_create(
            company=company,
            voucher=voucher,
            risk_type=risk_type,
            defaults={
                'resolved_by': request.user,
                'comments': comments
            }
        )
        
        # Invalidate cache for the company AI financial insights to refresh warnings
        cache_key = f"ai_financial_insights_{company.id}"
        cache.delete(cache_key)
        
        return JsonResponse({
            'status': 'success',
            'message': f'Audit risk alert resolved successfully.',
            'resolved_id': str(resolution.id)
        })
        
    except Exception as e:
        logger.error(f"Error in resolve_audit_risk_api: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
