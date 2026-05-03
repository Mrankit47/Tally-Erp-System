"""
Company views.

Thin views that delegate to the service layer.
Architecture: Views → Services → Models
"""

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Company
from tally_integration.services import TallySyncService

@csrf_exempt
def company_view(request):
    """
    Temporary API endpoint for Tally integration debugging.
    Handles POST requests with Tally XML/JSON payloads.
    """
    print(f"[DEBUG] Incoming Request: {request.method} {request.path}")
    
    if request.method == "POST":
        try:
            # You can parse JSON or XML here based on Tally payload
            # body = json.loads(request.body)
            print(f"[DEBUG] POST Body: {request.body}")
            return JsonResponse({'status': 'success', 'message': 'Payload received successfully at /api/company/'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    elif request.method == "GET":
        return JsonResponse({'status': 'success', 'message': 'API /api/company/ is running and ready for Tally.'})
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@login_required
@require_POST
def fetch_tally_companies_view(request):
    """Fetches companies from Tally and saves them to local DB."""
    try:
        companies = TallySyncService.fetch_all_tally_companies(request.user)
        return JsonResponse({'status': 'success', 'message': f'Fetched {len(companies)} companies from Tally.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@require_POST
def select_company_view(request):
    """Sets the active company in the user session."""
    company_id = request.POST.get('company_id')
    if company_id:
        request.session['active_company_id'] = company_id
        return JsonResponse({'status': 'success', 'message': 'Company selected successfully.'})
    return JsonResponse({'status': 'error', 'message': 'Company ID not provided.'}, status=400)
