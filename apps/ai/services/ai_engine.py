import logging
from ai.services.erp_service import get_total_sales, get_total_expenses, get_profit, get_recent_invoices
from ai.services.ai_service import ask_ai

logger = logging.getLogger('apps.ai')

def detect_intent(message: str) -> str:
    """
    Simple keyword-based intent detection.
    Returns: 'sales', 'expense', 'profit', 'invoice', or 'general'
    """
    msg_lower = message.lower()
    
    if any(kw in msg_lower for kw in ['sale', 'revenue', 'income']):
        return 'sales'
    elif any(kw in msg_lower for kw in ['expense', 'cost', 'spend']):
        return 'expense'
    elif any(kw in msg_lower for kw in ['profit', 'loss', 'margin']):
        return 'profit'
    elif any(kw in msg_lower for kw in ['invoice', 'bill', 'receipt']):
        return 'invoice'
    
    return 'general'

def process_query(message: str, request=None) -> str:
    """
    Orchestrates the AI request by detecting intent, fetching relevant ERP data,
    and passing it to the AI service.
    """
    if not request or not getattr(request, 'active_company', None):
        return "I need an active company context to provide financial insights."
        
    company = request.active_company
    logger.info(f"Processing query for company {company.id}: {message}")
    
    intent = detect_intent(message)
    logger.debug(f"Detected intent: {intent}")
    
    context_data = ""
    
    # Fetch specific data based on intent to enrich the prompt
    if intent == 'sales':
        context_data = get_total_sales(company)
    elif intent == 'expense':
        context_data = get_total_expenses(company)
    elif intent == 'profit':
        context_data = get_profit(company)
    elif intent == 'invoice':
        context_data = get_recent_invoices(company)
    
    # Send the combined message to the AI
    final_response = ask_ai(message, company, context_data)
    return final_response
