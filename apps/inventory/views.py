"""
Inventory views.

Thin views that delegate to the service layer.
Architecture: Views → Services → Models
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core.permissions import role_required
from django.core.paginator import Paginator

from company.models import Company
from .models import StockItem
from .forms import StockItemForm


@login_required
@role_required(['Admin', 'Accountant', 'InventoryManager'])
def stock_item_list_view(request):
    """List view for all inventory Stock Items."""
    company = Company.objects.first()
    
    # Using generic select_related, and relying on current_quantity property. 
    # For large datasets we would annotate this in the DB, but property is fine for initial MVP.
    items_qs = StockItem.objects.filter(company=company)
    
    paginator = Paginator(items_qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'active_page': 'inventory',
        'items': page_obj,
        'company': company,
    }
    return render(request, 'inventory/stock_item_list.html', context)


@login_required
@role_required(['Admin', 'Accountant', 'InventoryManager'])
def stock_item_create_view(request):
    """View to register a new Stock Item."""
    company = Company.objects.first()
    
    if request.method == 'POST':
        form = StockItemForm(request.POST)
        if form.is_valid():
            try:
                item = form.save(commit=False)
                item.company = company
                item.created_by = request.user
                item.updated_by = request.user
                item.save()
                
                messages.success(request, f"Stock Item '{item.name}' created successfully.")
                return redirect('inventory_list')
            except Exception as e:
                messages.error(request, f"Error saving stock item: {str(e)}")
    else:
        form = StockItemForm()
        
    context = {
        'active_page': 'inventory',
        'form': form,
    }
    return render(request, 'inventory/stock_item_form.html', context)
