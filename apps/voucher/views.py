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
from inventory.models import StockTransaction, TransactionType


@login_required
@role_required(['Admin', 'Accountant'])
def voucher_list_view(request, voucher_type):
    """
    Categorized list view for Vouchers (Sales, Payments, Receipts, etc.).
    """
    company = Company.objects.first()
    
    type_map = {
        'sales': VoucherType.SALES,
        'payments': VoucherType.PAYMENT,
        'receipts': VoucherType.RECEIPT,
        'contra': VoucherType.CONTRA,
        'journal': VoucherType.JOURNAL,
        'purchase': VoucherType.PURCHASE
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
    company = Company.objects.first()
    ledger_count = Ledger.objects.filter(company=company).count()
    
    type_map = {
        'sales': VoucherType.SALES,
        'payments': VoucherType.PAYMENT,
        'receipts': VoucherType.RECEIPT,
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
    return render(request, 'voucher_form.html', context)
