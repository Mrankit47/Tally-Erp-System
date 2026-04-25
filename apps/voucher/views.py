from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum

from core.permissions import role_required
from company.models import Company
from .models import Voucher, VoucherType, EntryType
from .forms import VoucherHeaderForm, VoucherEntryFormSet
from inventory.models import StockItem, StockTransaction, TransactionType


@login_required
@role_required(['Admin', 'Accountant'])
def voucher_list_view(request, voucher_type):
    """
    Categorized list view for Vouchers (Sales, Payments, Receipts, etc.).
    """
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
@role_required(['Admin', 'Accountant'])
def voucher_create_view(request, voucher_type):
    """
    Handles creation of a new Voucher with inline entries.
    """
    company = getattr(request, 'active_company', None)
    ledger_count = Ledger.objects.filter(company=company).count()
    
    type_map = {
        'sales': VoucherType.SALES,
        'payments': VoucherType.PAYMENT,
        'receipts': VoucherType.RECEIPT,
        'purchase': VoucherType.PURCHASE,
        'purchases': VoucherType.PURCHASE
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
                with transaction.atomic():
                    voucher = header_form.save(commit=False)
                    voucher.company = company
                    voucher.voucher_type = target_type
                    voucher.created_by = request.user
                    voucher.updated_by = request.user
                    voucher.is_posted = True # Automatically post for simple UX
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
