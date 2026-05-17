import json
import logging
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.permissions import role_required
from company.models import Company
from .models import Voucher, VoucherType, EntryType, VoucherStatus
from .forms import VoucherHeaderForm, VoucherEntryFormSet
from inventory.models import StockItem, StockTransaction, TransactionType

logger = logging.getLogger(__name__)



@login_required
@role_required(['Admin', 'Accountant', 'Manager', 'Billing Clerk'])
def voucher_list_view(request, voucher_type):
    """
    Categorized list view for Vouchers (Sales, Payments, Receipts, etc.).
    """
    user_role = getattr(getattr(request.user, 'profile', None), 'role', None)
    user_role_name = user_role.name.strip() if user_role else None
    
    if user_role_name == 'Billing Clerk' and voucher_type.lower() != 'sales':
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Billing Clerks are only allowed to view Sales Vouchers.")

    company = getattr(request, 'active_company', None)
    
    type_map = {
        'sales': VoucherType.SALES,
        'payments': VoucherType.PAYMENT,
        'receipts': VoucherType.RECEIPT,
        'contra': VoucherType.CONTRA,
        'journal': VoucherType.JOURNAL,
        'purchase': VoucherType.PURCHASE,
        'purchases': VoucherType.PURCHASE
    }
    
    target_type = type_map.get(voucher_type.lower())
    if not target_type:
        from django.http import Http404
        raise Http404("Invalid voucher type.")

    vouchers_qs = Voucher.objects.filter(
        company=company,
        voucher_type=target_type
    ).select_related('company').order_by('-date', '-number')

    for v in vouchers_qs:
        v.total_amount = v.entries.filter(entry_type=EntryType.DEBIT).aggregate(total=Sum('amount'))['total'] or 0

    paginator = Paginator(vouchers_qs, 20)
    page_number = request.GET.get('page')
    vouchers = paginator.get_page(page_number)

    context = {
        'active_page': voucher_type.lower(),
        'voucher_type_label': target_type.label,
        'vouchers': vouchers,
        'company': company,
    }
    return render(request, 'voucher_list.html', context)


from ledger.models import Ledger

@login_required
@role_required(['Admin', 'Accountant', 'Manager', 'Billing Clerk'])
def voucher_create_view(request, voucher_type):
    """
    Handles creation of a new Voucher with inline entries.
    """
    user_role = getattr(getattr(request.user, 'profile', None), 'role', None)
    user_role_name = user_role.name.strip() if user_role else None
    
    if user_role_name == 'Billing Clerk' and voucher_type.lower() != 'sales':
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Billing Clerks are only allowed to create Sales Vouchers.")

    company = getattr(request, 'active_company', None)
    ledger_count = Ledger.objects.filter(company=company).count()
    
    type_map = {
        'sales': VoucherType.SALES,
        'payments': VoucherType.PAYMENT,
        'receipts': VoucherType.RECEIPT,
        'purchase': VoucherType.PURCHASE,
        'purchases': VoucherType.PURCHASE,
        'journal': VoucherType.JOURNAL
    }
    
    target_type = type_map.get(voucher_type.lower())
    if not target_type:
        return redirect('dashboard')

    if request.method == 'POST':
        # Bind the form to a new Voucher instance with the company pre-populated
        # so that model validation (like clean) has access to the company.
        voucher_instance = Voucher(company=company)
        header_form = VoucherHeaderForm(request.POST, instance=voucher_instance)
        formset = VoucherEntryFormSet(request.POST, form_kwargs={'company': company})
        
        if header_form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():  # type: ignore
                    voucher = header_form.save(commit=False)
                    voucher.company = company
                    voucher.voucher_type = target_type
                    voucher.created_by = request.user
                    voucher.updated_by = request.user
                    
                    # Workflow Logic
                    if user_role_name in ['Admin', 'Accountant', 'Manager']:
                        voucher.status = VoucherStatus.APPROVED
                        voucher.is_posted = True
                    else:
                        voucher.status = VoucherStatus.PENDING
                        voucher.is_posted = False

                    voucher.save()
                    
                    formset.instance = voucher
                    entries = formset.save(commit=False)
                    for entry in entries:
                        entry.company = company
                        entry.created_by = request.user
                        entry.updated_by = request.user
                        entry.save()
                        
                        # Handle Inventory Sync
                        if hasattr(entry, 'stock_item') and entry.stock_item:
                            tx_type = TransactionType.OUT if target_type == VoucherType.SALES else TransactionType.IN
                            StockTransaction.objects.create(
                                company=company,
                                stock_item=entry.stock_item,
                                voucher_entry=entry,
                                quantity=entry.quantity,
                                rate=entry.rate,
                                transaction_type=tx_type
                            )
                    
                    formset.save_m2m()
                    
                    # Determine and save party_name from entries
                    party_entry = None
                    if target_type == VoucherType.SALES:
                        party_entry = voucher.entries.filter(entry_type=EntryType.DEBIT).first()
                    elif target_type == VoucherType.RECEIPT:
                        party_entry = voucher.entries.filter(entry_type=EntryType.CREDIT).first()
                    elif target_type == VoucherType.PAYMENT:
                        party_entry = voucher.entries.filter(entry_type=EntryType.DEBIT).first()
                    elif target_type == VoucherType.PURCHASE:
                        party_entry = voucher.entries.filter(entry_type=EntryType.CREDIT).first()
                    
                    if party_entry:
                        voucher.party_name = party_entry.ledger.name
                        voucher.save(update_fields=['party_name'])
                        
                messages.success(request, f"{target_type.label} {voucher.number} created successfully.")
                return redirect(f"{voucher_type.lower()}_list")
            except Exception as e:
                messages.error(request, f"Error creating voucher: {str(e)}")
    else:
        header_form = VoucherHeaderForm()
        formset = VoucherEntryFormSet(form_kwargs={'company': company})

    context = {
        'active_page': voucher_type.lower(),
        'voucher_type_label': target_type.label,
        'header_form': header_form,
        'formset': formset,
        'company': company,
        'ledger_count': ledger_count,
    }

    if target_type == VoucherType.SALES:
        # Pass specialized ledgers for Tally-style Sales Form
        context['debtors'] = Ledger.objects.filter(company=company, group__name__icontains='Debtors')
        context['sales_ledgers'] = Ledger.objects.filter(company=company, group__name__icontains='Sales')
        context['tax_ledgers'] = Ledger.objects.filter(company=company, group__name__icontains='Duties')
        context['stock_items'] = StockItem.objects.filter(company=company)
        return render(request, 'sales_voucher_form.html', context)

    if target_type == VoucherType.PURCHASE:
        # Pass specialized ledgers for Tally-style Purchase Form
        context['creditors'] = Ledger.objects.filter(company=company, group__name__icontains='Creditors')
        context['purchase_ledgers'] = Ledger.objects.filter(company=company, group__name__icontains='Purchase')
        context['tax_ledgers'] = Ledger.objects.filter(company=company, group__name__icontains='Duties')
        context['stock_items'] = StockItem.objects.filter(company=company)
        return render(request, 'purchase_voucher_form.html', context)

    if target_type == VoucherType.PAYMENT:
        # Pass specialized ledgers for Tally-style Payment Form
        context['cash_bank'] = Ledger.objects.filter(company=company, group__name__icontains='Bank') | Ledger.objects.filter(company=company, group__name__icontains='Cash')
        context['all_ledgers'] = Ledger.objects.filter(company=company)
        return render(request, 'payment_voucher_form.html', context)

    if target_type == VoucherType.RECEIPT:
        # Pass specialized ledgers for Tally-style Receipt Form
        context['cash_bank'] = Ledger.objects.filter(company=company, group__name__icontains='Bank') | Ledger.objects.filter(company=company, group__name__icontains='Cash')
        context['all_ledgers'] = Ledger.objects.filter(company=company)
        return render(request, 'receipt_voucher_form.html', context)

    if target_type == VoucherType.JOURNAL:
        # Pass all ledgers for Journal Form
        context['all_ledgers'] = Ledger.objects.filter(company=company)
        return render(request, 'journal_voucher_form.html', context)

    return render(request, 'voucher_form.html', context)
from .services.approval_service import approve_voucher
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from accounts.decorators import role_required

@login_required
@role_required(['Admin', 'Manager'])
@require_POST
def approve_voucher_view(request, voucher_id):
    """
    AJAX endpoint to approve a voucher from the dashboard.
    Restricted to Admins and Managers.
    """
    active_company = getattr(request, 'active_company', None)
    voucher = get_object_or_404(Voucher, pk=voucher_id, company=active_company)
    
    try:
        approve_voucher(voucher, request.user)
        return JsonResponse({
            'status': 'success',
            'message': f'Voucher {voucher.number} approved successfully.'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
@login_required
@role_required(['Admin', 'Accountant', 'Manager'])
def voucher_detail_view(request, voucher_id):
    """
    Read-only detailed view of a specific voucher.
    """
    active_company = getattr(request, 'active_company', None)
    voucher = get_object_or_404(Voucher, pk=voucher_id, company=active_company)
    
    entries = voucher.entries.all().select_related('ledger', 'stock_item')
    
    # Calculate totals
    total_debit = entries.filter(entry_type=EntryType.DEBIT).aggregate(total=Sum('amount'))['total'] or 0
    total_credit = entries.filter(entry_type=EntryType.CREDIT).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'voucher': voucher,
        'entries': entries,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'company': active_company,
    }
    return render(request, 'voucher_detail.html', context)


import os
import difflib
from django.utils.dateparse import parse_date
from ai.services.ocr_service import extract_text_from_file
from ai.services.ai_parser import parse_ocr_text_to_json
from ledger.models import Ledger
from inventory.models import StockItem, StockTransaction, TransactionType
from taxation.models import HSNCode
from .models import VoucherEntry

@login_required
@role_required(['Admin', 'Accountant', 'Manager'])
def voucher_scan_view(request):
    """Renders the AI Invoice Scanner page."""
    company = getattr(request, 'active_company', None)
    context = {
        'active_page': 'scan',
        'company': company,
    }
    return render(request, 'voucher_scan.html', context)


@login_required
@role_required(['Admin', 'Accountant', 'Manager'])
@require_POST
def voucher_scan_api(request):
    """Processes uploaded invoice, extracts metadata via Groq AI, and performs fuzzy db mapping."""
    company = getattr(request, 'active_company', None)
    if not company:
        return JsonResponse({'error': 'Active company context required.'}, status=400)

    uploaded_file = request.FILES.get('invoice_file')
    if not uploaded_file:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)

    if uploaded_file.size > 5 * 1024 * 1024:
        return JsonResponse({'error': 'File size exceeds 5MB limit.'}, status=400)

    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in ['.pdf', '.png', '.jpg', '.jpeg', '.webp']:
        return JsonResponse({'error': 'Unsupported file format.'}, status=400)

    try:
        raw_text = extract_text_from_file(uploaded_file, uploaded_file.name)
        parsed_data = parse_ocr_text_to_json(raw_text)

        # Fuzzy Match Vendor/Party
        creditors = Ledger.objects.filter(company=company, group__name__icontains='Creditors')
        creditor_choices = [{'id': str(c.id), 'name': c.name} for c in creditors]
        
        matched_vendor_id = ""
        matched_vendor_name = ""
        if parsed_data.get('vendor_name') and creditor_choices:
            ledger_names = [c['name'] for c in creditor_choices]
            matches = difflib.get_close_matches(parsed_data['vendor_name'], ledger_names, n=1, cutoff=0.3)
            if matches:
                matched_vendor_name = matches[0]
                matched_vendor_id = next(c['id'] for c in creditor_choices if c['name'] == matched_vendor_name)

        # Match Stock Items
        stock_items = StockItem.objects.filter(company=company)
        item_choices = [{'id': str(s.id), 'name': s.name} for s in stock_items]

        parsed_items = parsed_data.get('items', [])
        for item in parsed_items:
            item['matched_id'] = ""
            item['matched_name'] = ""
            if item.get('item_name') and item_choices:
                names = [s['name'] for s in item_choices]
                matches = difflib.get_close_matches(item['item_name'], names, n=1, cutoff=0.3)
                if matches:
                    item['matched_name'] = matches[0]
                    item['matched_id'] = next(s['id'] for s in item_choices if s['name'] == matches[0])

        # Fetch Purchase and Tax Ledgers
        purchase_ledgers = Ledger.objects.filter(company=company, group__name__icontains='Purchase')
        purchase_choices = [{'id': str(p.id), 'name': p.name} for p in purchase_ledgers]

        tax_ledgers = Ledger.objects.filter(company=company, group__name__icontains='Duties')
        tax_choices = [{'id': str(t.id), 'name': t.name} for t in tax_ledgers]

        response_payload = {
            'extracted': parsed_data,
            'matched_vendor_id': matched_vendor_id,
            'matched_vendor_name': matched_vendor_name,
            'creditors': creditor_choices,
            'purchase_ledgers': purchase_choices,
            'tax_ledgers': tax_choices,
            'stock_items': item_choices,
        }
        return JsonResponse(response_payload)

    except Exception as e:
        logger.error(f"Error processing invoice: {e}", exc_info=True)
        return JsonResponse({'error': f"Failed to parse invoice: {str(e)}"}, status=500)


@login_required
@role_required(['Admin', 'Accountant', 'Manager'])
@require_POST
def voucher_scan_save_api(request):
    """Validates reviewed invoice data and commits a balanced double-entry Purchase Voucher with inventory sync."""
    company = getattr(request, 'active_company', None)
    if not company:
        return JsonResponse({'error': 'Active company context required.'}, status=400)

    try:
        data = json.loads(request.body)
        vendor_id = data.get('vendor_id')
        purchase_ledger_id = data.get('purchase_ledger_id')
        invoice_number = data.get('invoice_number', '')
        invoice_date_str = data.get('invoice_date', '')
        narration = data.get('narration', '')
        subtotal = Decimal(str(data.get('subtotal', 0)))
        cgst = Decimal(str(data.get('cgst', 0)))
        sgst = Decimal(str(data.get('sgst', 0)))
        igst = Decimal(str(data.get('igst', 0)))
        total_amount = Decimal(str(data.get('total_amount', 0)))
        items = data.get('items', [])

        if not vendor_id or not purchase_ledger_id:
            return JsonResponse({'error': 'Supplier and Purchase Ledger are required.'}, status=400)

        invoice_date = parse_date(invoice_date_str) if invoice_date_str else timezone.now().date()

        vendor_ledger = get_object_or_404(Ledger, pk=vendor_id, company=company)
        purchase_ledger = get_object_or_404(Ledger, pk=purchase_ledger_id, company=company)

        # Start atomic transaction block
        with transaction.atomic():  # type: ignore
            # 1. Create Voucher Header
            voucher = Voucher.objects.create(
                company=company,
                date=invoice_date,
                voucher_type=VoucherType.PURCHASE,
                narration=f"AI Scanned Invoice: No. {invoice_number}. {narration}".strip(),
                party_name=vendor_ledger.name,
                is_posted=True,
                status=VoucherStatus.APPROVED,
                created_by=request.user,
                updated_by=request.user
            )

            # 2. Credit Party Ledger (CR)
            VoucherEntry.objects.create(
                company=company,
                voucher=voucher,
                ledger=vendor_ledger,
                amount=total_amount,
                entry_type=EntryType.CREDIT,
                created_by=request.user,
                updated_by=request.user
            )

            # 3. Debit Stock Item Line Entries (DR)
            for item in items:
                stock_item_id = item.get('stock_item_id')
                qty = Decimal(str(item.get('quantity', 0)))
                rate = Decimal(str(item.get('rate', 0)))
                line_amount = Decimal(str(item.get('amount', 0)))
                hsn_code = item.get('hsn_code', '')

                if not stock_item_id or qty <= 0:
                    continue

                stock_item = get_object_or_404(StockItem, pk=stock_item_id, company=company)
                
                hsn_obj = None
                if hsn_code:
                    hsn_obj, _ = HSNCode.objects.get_or_create(
                        company=company,
                        code=hsn_code,
                        defaults={'description': f'OCR HSN {hsn_code}', 'tax_rate': Decimal('18.00')}
                    )

                entry = VoucherEntry.objects.create(
                    company=company,
                    voucher=voucher,
                    ledger=purchase_ledger,
                    amount=line_amount,
                    entry_type=EntryType.DEBIT,
                    stock_item=stock_item,
                    quantity=qty,
                    rate=rate,
                    hsn_code=hsn_obj,
                    created_by=request.user,
                    updated_by=request.user
                )

                # Stock Transaction Sync (IN for Purchase)
                StockTransaction.objects.create(
                    company=company,
                    stock_item=stock_item,
                    voucher_entry=entry,
                    quantity=qty,
                    rate=rate,
                    transaction_type=TransactionType.IN
                )

            # 4. Debit CGST/SGST/IGST Entries (DR)
            duties_ledgers = Ledger.objects.filter(company=company, group__name__icontains='Duties')
            
            def create_tax_entry(tax_amount, keyword):
                if tax_amount <= 0:
                    return
                tax_ledger = duties_ledgers.filter(name__icontains=keyword).first()
                if not tax_ledger and duties_ledgers.exists():
                    tax_ledger = duties_ledgers.first()
                if tax_ledger:
                    VoucherEntry.objects.create(
                        company=company,
                        voucher=voucher,
                        ledger=tax_ledger,
                        amount=tax_amount,
                        entry_type=EntryType.DEBIT,
                        created_by=request.user,
                        updated_by=request.user
                    )

            create_tax_entry(cgst, 'CGST')
            create_tax_entry(sgst, 'SGST')
            create_tax_entry(igst, 'IGST')

        return JsonResponse({'status': 'success', 'message': f'Purchase Invoice {voucher.number} generated successfully!'})

    except Exception as e:
        logger.error(f"Error saving scanned invoice voucher: {e}", exc_info=True)
        return JsonResponse({'error': f"Failed to record invoice: {str(e)}"}, status=500)


from ai.services.insights_service import generate_company_insights_summary

@login_required
@role_required(['Admin', 'Accountant', 'Manager'])
def voucher_analytics_view(request):
    """
    Renders the beautiful AI Financial Analytics & Insights Dashboard.
    """
    return render(request, 'voucher_analytics.html', {
        'active_page': 'analytics',
        'company': request.active_company
    })

@login_required
@role_required(['Admin', 'Accountant', 'Manager'])
def voucher_analytics_api(request):
    """
    Computes analytical ratios and returns the cached Groq AI financial commentary.
    """
    company = getattr(request, 'active_company', None)
    if not company:
        return JsonResponse({'error': 'No active company context.'}, status=400)
        
    refresh = request.GET.get('refresh', 'false').lower() == 'true'
    payload = generate_company_insights_summary(company, force_refresh=refresh)
    return JsonResponse(payload)

