"""
Reports views.

Thin views that delegate to the service layer.
Architecture: Views → Services → Models
"""
import csv
import json
from dateutil.relativedelta import relativedelta
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from core.permissions import role_required
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from core.templatetags.currency_tags import indian_currency
from .services import generate_trial_balance, generate_profit_and_loss, get_top_expenses
from company.models import Company
from voucher.models import VoucherEntry, EntryType, VoucherType


@login_required
@role_required(['Admin', 'Accountant', 'Manager'])
def trial_balance_view(request):
    """Renders the HTML Trial Balance Report."""
    company = getattr(request, 'active_company', None)
    tb_report = generate_trial_balance(company)
    
    # Check if there's any data
    is_empty = all(len(ledgers) == 0 for ledgers in tb_report['data'].values())
    
    context = {
        'active_page': 'trial_balance',
        'tb': tb_report,
        'company': company,
        'is_empty': is_empty
    }
    return render(request, 'reports/trial_balance.html', context)


@login_required
@role_required(['Admin', 'Accountant', 'Manager'])
def export_trial_balance_csv(request):
    """Exports the Trial Balance to CSV."""
    company = getattr(request, 'active_company', None)
    tb_report = generate_trial_balance(company)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Trial_Balance.csv"'
    response.write('\ufeff'.encode('utf8')) # BOM for Excel
    
    writer = csv.writer(response)
    writer.writerow([f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"])
    writer.writerow([f"Company: {company.name if company else 'Unknown'}"])
    writer.writerow([]) # Empty separator
    
    writer.writerow(['Category', 'Ledger Name', 'Debit Amount', 'Credit Amount'])
    
    for category in ['Assets', 'Liabilities', 'Income', 'Expenses']:
        for ledger in tb_report['data'][category]:
            writer.writerow([
                category,
                ledger['name'],
                indian_currency(ledger['debit']) if ledger['debit'] else '',
                indian_currency(ledger['credit']) if ledger['credit'] else ''
            ])
            
    writer.writerow([])
    writer.writerow(['', 'TOTAL', indian_currency(tb_report['total_debit']), indian_currency(tb_report['total_credit'])])
    
    if not tb_report['is_balanced']:
        writer.writerow(['', 'DIFFERENCE', '', indian_currency(tb_report['difference'])])
    
    return response


@login_required
@role_required(['Admin', 'Accountant', 'Manager'])
def profit_loss_view(request):
    """Renders the HTML Profit & Loss Statement with Visual Analytics."""
    company = getattr(request, 'active_company', None)
    pl_report = generate_profit_and_loss(company)
    top_expenses = get_top_expenses(company, limit=5)
    
    is_empty = len(pl_report['incomes']) == 0 and len(pl_report['expenses']) == 0
    
    # Generate Chart Data (Last 12 months)
    today = timezone.now().date()
    start_date = (today.replace(day=1) - relativedelta(months=11))
    
    def get_monthly_sums(voucher_type):
        qs = VoucherEntry.objects.filter(
            ledger__company=company,
            voucher__voucher_type=voucher_type,
            entry_type=EntryType.DEBIT,
            voucher__date__gte=start_date
        ).annotate(
            month=TruncMonth('voucher__date')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')
        
        return {item['month'].strftime('%b %Y'): float(item['total']) for item in qs if item['month']}

    sales_trend = get_monthly_sums(VoucherType.SALES)
    expenses_trend = get_monthly_sums(VoucherType.PAYMENT) # Proxy for expenses trend
    
    # Generate continuous last 12 months labels ensures no blanks
    months = []
    for i in range(11, -1, -1):
        d = today - relativedelta(months=i)
        months.append(d.strftime('%b %Y'))
        
    chart_data = {
        'labels': months,
        'income': [sales_trend.get(m, 0) for m in months],
        'expenses': [expenses_trend.get(m, 0) for m in months],
        'profit': [(sales_trend.get(m, 0) - expenses_trend.get(m, 0)) for m in months]
    }
    
    context = {
        'active_page': 'profit_loss',
        'pl': pl_report,
        'top_expenses': top_expenses,
        'company': company,
        'is_empty': is_empty,
        'chart_data_json': json.dumps(chart_data)
    }
    return render(request, 'reports/profit_loss.html', context)


@login_required
@role_required(['Admin', 'Accountant', 'Manager'])
def export_profit_loss_csv(request):
    """Exports the Profit & Loss statement to CSV."""
    company = getattr(request, 'active_company', None)
    pl_report = generate_profit_and_loss(company)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Profit_And_Loss.csv"'
    response.write('\ufeff'.encode('utf8'))
    
    writer = csv.writer(response)
    writer.writerow([f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"])
    writer.writerow([f"Company: {company.name if company else 'Unknown'}"])
    writer.writerow([])
    
    writer.writerow(['Type', 'Ledger Name', 'Amount'])
    
    writer.writerow(['INCOME', '', ''])
    for ledger in pl_report['incomes']:
        amount = ledger['credit'] - ledger['debit']
        writer.writerow(['', ledger['name'], indian_currency(amount)])
    writer.writerow(['', 'Total Income', indian_currency(pl_report['total_income'])])
    
    writer.writerow([])
    writer.writerow(['EXPENSES', '', ''])
    for ledger in pl_report['expenses']:
        amount = ledger['debit'] - ledger['credit']
        writer.writerow(['', ledger['name'], indian_currency(amount)])
    writer.writerow(['', 'Total Expenses', indian_currency(pl_report['total_expenses'])])
    
    writer.writerow([])
    status = "Net Profit" if pl_report['is_profit'] else "Net Loss"
    writer.writerow(['SUMMARY', status, indian_currency(pl_report['net_result'])])
    
    return response


from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
import pypdf
from ai.services.router import ai_router
from ledger.models import Ledger
from voucher.models import Voucher, VoucherEntry, EntryType, VoucherStatus
import logging

logger = logging.getLogger('apps.reports')

@login_required
@role_required(['Admin', 'Accountant', 'Manager'])
def bank_reconciliation_view(request):
    """
    Renders the beautiful AI Bank Sync / Reconciliation dashboard.
    """
    company = getattr(request, 'active_company', None)
    
    # Load all local ledgers for the company
    ledgers_qs = Ledger.objects.filter(company=company).order_by('name')
    ledgers_list = [{'id': str(l.id), 'name': l.name} for l in ledgers_qs]
    
    # Load Bank ledgers specifically for statement association
    bank_ledgers_qs = Ledger.objects.filter(company=company, group__name__icontains='Bank').order_by('name')
    if not bank_ledgers_qs.exists():
        # Fallback to any Cash ledger or first available ledger
        bank_ledgers_qs = Ledger.objects.filter(company=company, name__icontains='Cash')
    if not bank_ledgers_qs.exists():
        bank_ledgers_qs = ledgers_qs
        
    bank_ledgers_list = [{'id': str(l.id), 'name': l.name} for l in bank_ledgers_qs]
    
    context = {
        'active_page': 'bank_reconciliation',
        'company': company,
        'ledgers_json': json.dumps(ledgers_list),
        'bank_ledgers': bank_ledgers_list,
    }
    return render(request, 'reports/bank_reconciliation.html', context)


@login_required
@role_required(['Admin', 'Accountant', 'Manager'])
@require_POST
def bank_reconciliation_upload_api(request):
    """
    Handles bank statement PDF upload, extracts digital text, and calls Gemini
    to parse and auto-map transaction details to local company ledgers.
    """
    try:
        company = getattr(request, 'active_company', None)
        if not company:
            return JsonResponse({'error': 'No active company context.'}, status=400)
            
        file_obj = request.FILES.get('file')
        if not file_obj:
            return JsonResponse({'error': 'No bank statement PDF file uploaded.'}, status=400)
            
        try:
            with open("c:/Users/Ankit/OneDrive/Desktop/Major Project/scratch_statement.pdf", "wb+") as f:
                for chunk in file_obj.chunks():
                    f.write(chunk)
        except Exception as e:
            logger.error(f"Failed to save scratch PDF: {e}")
            
        # 1. Extract digital text from PDF
        logger.info(f"Uploading and parsing bank statement: {file_obj.name}")
        reader = pypdf.PdfReader(file_obj)
        pages_text = []
        for page in reader.pages:
            content = page.extract_text()
            if content:
                pages_text.append(content)
                
        raw_text = "\n".join(pages_text).strip()
        if not raw_text:
            return JsonResponse({'error': 'Digital text extraction was empty. Please upload a standard digital bank PDF.'}, status=400)
            
        # 2. Send text to Gemini to parse transaction rows
        system_prompt = """You are a highly capable bank statement layout parsing assistant.
Extract all transaction row entries from the provided bank statement text.
Format your output strictly as a JSON array of objects, where each object has these exact keys:
- "date": Transaction posting date in format "YYYY-MM-DD"
- "description": Complete transaction details/narrative/description
- "debit": The withdrawal / debit amount as a decimal number (0.0 if not present or credit)
- "credit": The deposit / credit amount as a decimal number (0.0 if not present or debit)

Rules:
1. Extract EVERY single transaction row accurately without skipping.
2. Ignore summarized general bank details, headers, summary cards, and balances.
3. Ensure "debit" and "credit" are raw numbers (no commas or currency symbols).
4. Do NOT include any unescaped double quotes (replace with single quotes).
5. Do NOT include any backslashes (\) inside the "description" value (replace with forward slashes / or spaces).
6. The "description" must be a clean, single-line string with no literal newlines or carriage returns.
7. Strictly return JSON format only without surrounding markdown blocks.
"""
        
        logger.info("Calling Gemini Vision/Text API for bank statement layout parsing.")
        gemini_response = ai_router.get_gemini().generate_response(
            system_prompt=system_prompt,
            user_prompt=f"BANK STATEMENT TEXT CONTENT:\n{raw_text}",
            temperature=0.1,
            max_tokens=8000
        )
        
        # Clean any accidental Markdown blocks
        cleaned_response = gemini_response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        elif cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()
        
        # Robust JSON repair function to self-heal truncated model outputs
        def repair_truncated_json(s: str) -> str:
            s = s.strip()
            if not s:
                return "[]"
            try:
                json.loads(s)
                return s
            except json.JSONDecodeError:
                pass
                
            # Find last complete object closure
            last_brace = s.rfind('}')
            if last_brace == -1:
                return "[]"
                
            repaired = s[:last_brace + 1]
            if not repaired.startswith('['):
                first_brace = repaired.find('{')
                if first_brace != -1:
                    repaired = '[' + repaired[first_brace:]
                else:
                    return "[]"
            repaired += ']'
            
            try:
                json.loads(repaired)
                return repaired
            except json.JSONDecodeError:
                # Iteratively search backwards if the absolute last brace was within a malformed segment
                temp = repaired[:-1]
                while True:
                    last_b = temp.rfind('}')
                    if last_b == -1:
                        break
                    temp = temp[:last_b + 1]
                    candidate = temp + ']'
                    try:
                        json.loads(candidate)
                        return candidate
                    except json.JSONDecodeError:
                        temp = temp[:-1]
            return "[]"

        repaired_response = repair_truncated_json(cleaned_response)
        
        import re
        # Clean invalid backslashes that break standard JSON parsing
        repaired_response = re.sub(r'\\(?![\\"/bfnrtu])', '/', repaired_response)
        
        try:
            parsed_transactions = json.loads(repaired_response)
        except json.JSONDecodeError as je:
            logger.error(f"Failed to parse JSON response from Gemini: {repaired_response}")
            try:
                with open("c:/Users/Ankit/OneDrive/Desktop/Major Project/scratch_response.txt", "w", encoding="utf-8") as f:
                    f.write(repaired_response)
            except Exception as fe:
                logger.error(f"Failed to write debug file: {fe}")
            return JsonResponse({'error': f'Failed to parse AI bank statement output: {str(je)}'}, status=500)
            
        # 3. Perform backend keyword auto-mapping
        ledgers = list(Ledger.objects.filter(company=company))
        processed_list = []
        
        for tx in parsed_transactions:
            desc = tx.get('description', '')
            debit = float(tx.get('debit', 0.0) or 0.0)
            credit = float(tx.get('credit', 0.0) or 0.0)
            tx_date = tx.get('date', timezone.now().date().strftime('%Y-%m-%d'))
            
            # Simple keyword search inside descriptions
            desc_lower = desc.lower()
            suggested_voucher_type = "PAYMENT" if debit > 0 else "RECEIPT"
            
            best_match = None
            for ledger in ledgers:
                lname_lower = ledger.name.lower()
                # Direct match or containment of important words
                if lname_lower in desc_lower or any(len(w) > 3 and w in desc_lower for w in lname_lower.split()):
                    best_match = ledger
                    break
            
            # Smart Custom overrides
            if not best_match:
                if "electricity" in desc_lower or "power" in desc_lower:
                    best_match = next((l for l in ledgers if "electric" in l.name.lower()), None)
                elif "rent" in desc_lower:
                    best_match = next((l for l in ledgers if "rent" in l.name.lower()), None)
                elif "salary" in desc_lower or "salary" in desc_lower:
                    best_match = next((l for l in ledgers if "salary" in l.name.lower()), None)
                elif "cash" in desc_lower:
                    best_match = next((l for l in ledgers if "cash" in l.name.lower()), None)
                elif "rahul" in desc_lower:
                    best_match = next((l for l in ledgers if "rahul" in l.name.lower()), None)
                    
            if best_match:
                ledger_id = str(best_match.id)
                ledger_name = best_match.name
                confidence = "HIGH"
            else:
                # Default fallbacks
                if suggested_voucher_type == "PAYMENT":
                    fallback = next((l for l in ledgers if "expense" in l.group.name.lower() or "expense" in l.name.lower()), None)
                else:
                    fallback = next((l for l in ledgers if "sale" in l.name.lower()), None)
                    
                if not fallback:
                    fallback = next((l for l in ledgers if "cash" in l.name.lower()), None)
                if not fallback and ledgers:
                    fallback = ledgers[0]
                    
                ledger_id = str(fallback.id) if fallback else ""
                ledger_name = fallback.name if fallback else "Unmapped Ledger"
                confidence = "LOW"
                
            processed_list.append({
                'date': tx_date,
                'description': desc,
                'debit': debit,
                'credit': credit,
                'suggested_voucher_type': suggested_voucher_type,
                'suggested_ledger_id': ledger_id,
                'suggested_ledger_name': ledger_name,
                'confidence': confidence
            })
            
        return JsonResponse({
            'status': 'success',
            'filename': file_obj.name,
            'transactions': processed_list
        })
        
    except Exception as e:
        logger.error(f"Error processing bank statement upload: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@role_required(['Admin', 'Accountant', 'Manager'])
@require_POST
def bank_reconciliation_post_api(request):
    """
    Receives reviewed bank transactions, generates double-entry Vouchers, and posts them.
    """
    try:
        company = getattr(request, 'active_company', None)
        if not company:
            return JsonResponse({'error': 'No active company context.'}, status=400)
            
        data = json.loads(request.body)
        bank_ledger_id = data.get('bank_ledger_id')
        transactions = data.get('transactions', [])
        
        if not bank_ledger_id:
            return JsonResponse({'error': 'Please select the local Bank Account Ledger to sync against.'}, status=400)
            
        if not transactions:
            return JsonResponse({'error': 'No transactions provided for posting.'}, status=400)
            
        bank_ledger = get_object_or_404(Ledger, id=bank_ledger_id, company=company)
        
        created_count = 0
        from django.db import transaction as db_transaction
        from django.core.cache import cache
        
        with db_transaction.atomic():  # type: ignore
            for tx in transactions:
                tx_date = tx.get('date')
                desc = tx.get('description', '')
                debit_amt = float(tx.get('debit', 0.0) or 0.0)
                credit_amt = float(tx.get('credit', 0.0) or 0.0)
                v_type = tx.get('suggested_voucher_type')
                ledger_id = tx.get('suggested_ledger_id')
                
                amount = debit_amt if v_type == 'PAYMENT' else credit_amt
                if amount <= 0:
                    continue
                    
                target_ledger = get_object_or_404(Ledger, id=ledger_id, company=company)
                
                # Create Voucher
                voucher = Voucher.objects.create(
                    company=company,
                    date=tx_date,
                    voucher_type=v_type,
                    narration=f"Bank Sync: {desc}",
                    party_name=target_ledger.name,
                    status=VoucherStatus.APPROVED,
                    is_posted=True
                )
                
                # Double Entry Bookkeeping
                if v_type == 'PAYMENT':
                    # Debit the Expense/Vendor Account
                    VoucherEntry.objects.create(
                        company=company,
                        voucher=voucher,
                        ledger=target_ledger,
                        amount=amount,
                        entry_type=EntryType.DEBIT,
                        created_by=request.user,
                        updated_by=request.user
                    )
                    # Credit the Bank Account
                    VoucherEntry.objects.create(
                        company=company,
                        voucher=voucher,
                        ledger=bank_ledger,
                        amount=amount,
                        entry_type=EntryType.CREDIT,
                        created_by=request.user,
                        updated_by=request.user
                    )
                else: # RECEIPT
                    # Debit the Bank Account
                    VoucherEntry.objects.create(
                        company=company,
                        voucher=voucher,
                        ledger=bank_ledger,
                        amount=amount,
                        entry_type=EntryType.DEBIT,
                        created_by=request.user,
                        updated_by=request.user
                    )
                    # Credit the Income/Customer Account
                    VoucherEntry.objects.create(
                        company=company,
                        voucher=voucher,
                        ledger=target_ledger,
                        amount=amount,
                        entry_type=EntryType.CREDIT,
                        created_by=request.user,
                        updated_by=request.user
                    )
                    
                created_count += 1
                
        # Invalidate dashboard and financial analytics caches
        cache.delete(f"ai_financial_insights_{company.id}")
        
        return JsonResponse({
            'status': 'success',
            'message': f'Successfully posted {created_count} bank reconciliation vouchers.'
        })
        
    except Exception as e:
        logger.error(f"Error posting bank statement transactions: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
