"""
Ledger views.

Display and manage the Chart of Accounts.
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from company.models import Company
from core.permissions import role_required
from .models import LedgerGroup, Ledger
from .forms import LedgerForm
from .services import initialize_tally_groups


@login_required
@role_required(['Admin', 'Accountant'])
def ledger_list_view(request):
    """
    Displays the Chart of Accounts (Ledgers grouped by Category).
    """
    company = getattr(request, 'active_company', None)
    
    # Auto-initialize if empty (for better first-time UX)
    if not LedgerGroup.objects.filter(company=company).exists():
        initialize_tally_groups(company)
    
    # Fetch groups and their ledgers, prefetched to avoid N+1
    groups = LedgerGroup.objects.filter(company=company).prefetch_related('ledgers').order_by('name')
    
    context = {
        'active_page': 'ledgers',
        'groups': groups,
        'company': company,
    }
    return render(request, 'ledger_list.html', context)


@login_required
@role_required(['Admin', 'Accountant'])
def ledger_create_view(request):
    """
    Handles creation of a new Ledger.
    """
    company = getattr(request, 'active_company', None)
    
    # Ensure groups exist
    if not LedgerGroup.objects.filter(company=company).exists():
        initialize_tally_groups(company)
    
    if request.method == 'POST':
        form = LedgerForm(request.POST, company=company)
        if form.is_valid():
            try:
                ledger = form.save(commit=False)
                ledger.company = company
                ledger.created_by = request.user
                ledger.updated_by = request.user
                ledger.save()
                
                messages.success(request, f"Ledger '{ledger.name}' created successfully.")
                return redirect('ledger_list')
            except IntegrityError:
                form.add_error('name', f"A ledger with this name already exists for {company.name}.")
    else:
        form = LedgerForm(company=company)

    context = {
        'active_page': 'ledgers',
        'form': form,
        'company': company,
    }
    return render(request, 'ledger_form.html', context)
