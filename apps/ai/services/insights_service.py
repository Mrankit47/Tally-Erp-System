import os
import logging
from django.core.cache import cache
from django.utils import timezone
from .router import ai_router
from .analytics_service import (
    calculate_revenue_metrics,
    calculate_expense_metrics,
    calculate_cashflow_metrics,
    calculate_gst_metrics,
    calculate_approval_metrics,
    calculate_inventory_metrics,
    calculate_forecasting_metrics,
    calculate_financial_health_score
)
from .risk_engine import audit_company_vouchers_for_risks

logger = logging.getLogger('apps.ai')

def generate_company_insights_summary(company, force_refresh=False, language='English') -> dict:
    """
    Compiles calculated metrics and programmatically flagged risks,
    caches findings for 15 mins, and retrieves Groq AI auditor commentary.
    """
    cache_key = f"ai_financial_insights_{company.id}_{language.lower()}"
    cached_insights = cache.get(cache_key)
    
    if cached_insights and not force_refresh:
        logger.info(f"Retrieved cached insights report for company {company.id} in {language}.")
        return cached_insights

    try:
        # 1. Compile programmatic metrics (No database calls by AI)
        revenue = calculate_revenue_metrics(company)
        expenses = calculate_expense_metrics(company)
        cashflow = calculate_cashflow_metrics(company)
        gst = calculate_gst_metrics(company)
        approvals = calculate_approval_metrics(company)
        inventory = calculate_inventory_metrics(company)
        forecast = calculate_forecasting_metrics(company)
        
        health_metrics = {
            'sales': revenue,
            'expenses': expenses,
            'cashflow': cashflow,
            'approvals': approvals
        }
        health = calculate_financial_health_score(company, health_metrics)
        risks = audit_company_vouchers_for_risks(company)

        # 2. Format localized variables for Groq AI
        agg_data = f"""
[COMPANY]
Name: {company.name}

[REVENUE]
Lifetime Sales: ₹{revenue['total_sales']:.2f}
Current Month Sales: ₹{revenue['current_month_sales']:.2f}
Previous Month Sales: ₹{revenue['prev_month_sales']:.2f}
Growth Rate: {revenue['growth_percentage']}%

[EXPENSES]
Total Expenses: ₹{expenses['total_expenses']:.2f}
Current Month Expenses: ₹{expenses['current_month_expenses']:.2f}
Expense Ratio: {expenses['expense_ratio']}%
Top Categories: {', '.join([f"{c['category']} (₹{c['amount']:.2f})" for c in expenses['top_categories']])}

[CASHFLOW]
Total Inflows: ₹{cashflow['inflow']:.2f}
Total Outflows: ₹{cashflow['outflow']:.2f}
Net Cashflow: ₹{cashflow['net_cashflow']:.2f}
Sundry Receivables: ₹{cashflow['receivables']:.2f}
Sundry Payables: ₹{cashflow['payables']:.2f}

[TAXES]
Total CGST Liability: ₹{gst['cgst_liability']:.2f}
Total SGST Liability: ₹{gst['sgst_liability']:.2f}
Total IGST Liability: ₹{gst['igst_liability']:.2f}
Net GST Payable: ₹{gst['net_gst_liability']:.2f}

[APPROVALS]
Pending Vouchers: {approvals['pending_approvals']}
Rejected Vouchers: {approvals['rejected_vouchers']}
Total Registered Vouchers: {approvals['total_vouchers']}

[INVENTORY INSIGHTS]
Low Stock Items Count: {len(inventory['low_stock'])}
Fast Moving items: {', '.join([f"{i['item_name']}" for i in inventory['fast_moving']])}

[FORECAST PROJECTIONS]
Expected Next Month Sales: ₹{forecast['projected_sales']:.2f}
Expected Next Month Expenses: ₹{forecast['projected_expenses']:.2f}

[FINANCIAL HEALTH SUMMARY]
Financial Health Score: {health['score']}/100
Status: {health['status']}
Primary Health Score Deductions:
{chr(10).join([f"- {d}" for d in health['deductions']]) if health['deductions'] else 'None.'}

[AUDITING ALERTS]
Total programmatically flagged warnings: {len(risks)}
High-severity warnings count: {len([r for r in risks if r['severity'] == 'HIGH'])}
Medium-severity warnings count: {len([r for r in risks if r['severity'] == 'MEDIUM'])}
Low-severity warnings count: {len([r for r in risks if r['severity'] == 'LOW'])}
"""

        # 3. Call AI Router for human-readable audit reports via DeepSeek
        logger.debug("Routing insights summary request to AI router for 'finance' task.")
        
        system_prompt = f"""You are a highly experienced Senior Chartered Accountant, Corporate Auditor, and ERP Business Intelligence consultant.
Your goal is to inspect the aggregated financial metrics and programmatic risk alerts compiled by the ERP and draft an executive financial dashboard report.

Follow these strict output guidelines:
1. Write in a formal, highly authoritative corporate auditing tone.
2. Structure your answer using these exact markdown sections:
   - **### Executive Financial Summary:** A SWOT matrix summarizing overall performance.
   - **### Liquidity & Cashflow Analysis:** Inspections of net margins, receivables collection, and bank reserves.
   - **### GST & Taxation Oversight:** Assessment of GST liability and estimated payments.
   - **### Key Risk Anomalies & Audit Review:** Critical examination of the programmatic risk triggers. Mention specific count indicators.
   - **### Strategic Growth Projections & Advisory:** Simple moving-average forecasting recommendations and cost-control actions.
3. Keep the content dense, precise, and concise. Do not add general filler or intro/outro remarks.
4. Always reference specific figures from the metrics provided. Do not invent or guess information.
5. You MUST write the entire response in the {language} language. If {language} is Hindi, translate all section headers and commentary details into clean, elegant, professional corporate Hindi, maintaining financial accuracy.
"""

        ai_commentary = ai_router.route_request(
            task="finance",
            system_prompt=system_prompt,
            user_prompt=f"ERP AGGREGATED METRICS:\n{agg_data}",
            temperature=0.2,
            max_tokens=1500
        )

        payload = {
            'metrics': {
                'revenue': revenue,
                'expenses': expenses,
                'cashflow': cashflow,
                'gst': gst,
                'approvals': approvals,
                'inventory': inventory,
                'forecast': forecast,
                'health': health,
                'risks': risks
            },
            'ai_insights': ai_commentary,
            'timestamp': timezone.now().isoformat()
        }

        # Cache the resulting analytics payload for 15 minutes (900 seconds)
        cache.set(cache_key, payload, 900)
        logger.info(f"Generated and cached new insights report for company {company.id} in {language}.")
        return payload

    except Exception as e:
        logger.error(f"Error in generate_company_insights_summary: {e}", exc_info=True)
        # Fallback payload with calculations still working if Groq fails
        try:
            fallback_metrics = {
                'revenue': calculate_revenue_metrics(company),
                'expenses': calculate_expense_metrics(company),
                'cashflow': calculate_cashflow_metrics(company),
                'gst': calculate_gst_metrics(company),
                'approvals': calculate_approval_metrics(company),
                'inventory': calculate_inventory_metrics(company),
                'forecast': calculate_forecasting_metrics(company),
                'health': {'score': 80, 'status': 'STABLE', 'deductions': []},
                'risks': audit_company_vouchers_for_risks(company)
            }
        except Exception:
            fallback_metrics = {}

        fallback_msg = "### Executive Financial Summary\nError communicating with AI Router. Real-time statistical metrics continue to function, but AI narrative insights are temporarily unavailable."
        if language.lower() == 'hindi':
            fallback_msg = "### Executive Financial Summary\nAI राउटर से संपर्क करने में त्रुटि। वास्तविक समय के सांख्यिकीय मेट्रिक्स काम करना जारी रख रहे हैं, लेकिन AI विश्लेषण वर्तमान में अस्थायी रूप से अनुपलब्ध है।"

        return {
            'metrics': fallback_metrics,
            'ai_insights': fallback_msg,
            'timestamp': timezone.now().isoformat()
        }
