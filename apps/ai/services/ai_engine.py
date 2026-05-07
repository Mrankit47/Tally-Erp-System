import logging
from ai.services.erp_service import get_total_sales, get_total_expenses, get_profit, get_recent_invoices
from ai.services.ai_service import ask_ai
from ai.services.analytics_service import (
    calculate_revenue_metrics,
    calculate_expense_metrics,
    calculate_cashflow_metrics,
    calculate_gst_metrics,
    calculate_approval_metrics,
    calculate_forecasting_metrics,
    calculate_financial_health_score
)
from ai.services.risk_engine import audit_company_vouchers_for_risks

logger = logging.getLogger('apps.ai')

def detect_intent(message: str) -> str:
    """
    Keyword-based intent classifier.
    Categorizes the request to enrich the Groq prompt with precise aggregate metrics.
    """
    msg_lower = message.lower()
    
    if any(kw in msg_lower for kw in ['gst', 'tax', 'cgst', 'sgst', 'igst', 'duties']):
        return 'gst'
    elif any(kw in msg_lower for kw in ['approve', 'pending', 'reject', 'approvals']):
        return 'approvals'
    elif any(kw in msg_lower for kw in ['risk', 'anomaly', 'suspicious', 'duplicate', 'hour', 'audit', 'narration']):
        return 'risk'
    elif any(kw in msg_lower for kw in ['health', 'score', 'rating', 'swot', 'financial state']):
        return 'health'
    elif any(kw in msg_lower for kw in ['forecast', 'predict', 'projection', 'next month', 'sma']):
        return 'forecast'
    elif any(kw in msg_lower for kw in ['sale', 'revenue', 'income']):
        return 'sales'
    elif any(kw in msg_lower for kw in ['expense', 'cost', 'spend', 'category']):
        return 'expense'
    elif any(kw in msg_lower for kw in ['profit', 'loss', 'margin']):
        return 'profit'
    elif any(kw in msg_lower for kw in ['invoice', 'bill', 'receipt']):
        return 'invoice'
    
    return 'general'

def process_query(message: str, request=None) -> str:
    """
    Orchestrates the AI request by detecting intent, extracting precise local metrics,
    and sending a factual context bundle to Groq.
    """
    if not request or not getattr(request, 'active_company', None):
        return "I need an active company context to provide financial insights."
        
    company = request.active_company
    logger.info(f"Processing query for company {company.id}: {message}")
    
    intent = detect_intent(message)
    logger.debug(f"Detected intent: {intent}")
    
    context_data = ""
    
    # Fetch specific data based on intent to enrich the prompt
    if intent == 'gst':
        gst = calculate_gst_metrics(company)
        context_data = f"GST Obligations: CGST Liability ₹{gst['cgst_liability']:.2f}, SGST Liability ₹{gst['sgst_liability']:.2f}, IGST Liability ₹{gst['igst_liability']:.2f}, Net Payable ₹{gst['net_gst_liability']:.2f}."
    elif intent == 'approvals':
        appr = calculate_approval_metrics(company)
        context_data = f"Voucher Approvals Status: Pending Vouchers = {appr['pending_approvals']}, Rejected Vouchers = {appr['rejected_vouchers']}, Total Registered Vouchers = {appr['total_vouchers']}."
    elif intent == 'risk':
        risks = audit_company_vouchers_for_risks(company)
        context_data = f"Automated ERP Audit Alerts: Detected {len(risks)} compliance anomalies. " + \
                       ", ".join([f"[{r['severity']}] {r['title']}: {r['description']}" for r in risks[:3]])
    elif intent == 'health':
        rev = calculate_revenue_metrics(company)
        exp = calculate_expense_metrics(company)
        cash = calculate_cashflow_metrics(company)
        appr = calculate_approval_metrics(company)
        health = calculate_financial_health_score(company, {'sales': rev, 'expenses': exp, 'cashflow': cash, 'approvals': appr})
        context_data = f"Company Financial Health Score: {health['score']}/100, Rating = {health['status']}. Deductions factors: {', '.join(health['deductions']) if health['deductions'] else 'None (Fully compliant)'}."
    elif intent == 'forecast':
        f = calculate_forecasting_metrics(company)
        context_data = f"AI SMA Forecasting: Projected Sales for next month is ₹{f['projected_sales']:.2f}, Projected Expenses is ₹{f['projected_expenses']:.2f}."
    elif intent == 'sales':
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
