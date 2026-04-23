"""
Core views for the ERP dashboard UI.

Provides the main dashboard and sync log pages using Django templates.
"""

import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.forms import modelform_factory
from .permissions import role_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Sum, Q
from django.db.models.functions import TruncMonth
from django.http import JsonResponse, Http404
from django.contrib import messages
from voucher.models import Voucher, VoucherType, VoucherEntry, EntryType, CustomVoucherType
from tally_integration.models import SyncLog
from tally_integration.services import TallySyncService
from company.models import Company
from ledger.models import LedgerGroup, Ledger, Currency, Budget, Scenario
from inventory.models import StockGroup, StockCategory, StockItem, Unit, Location


@login_required
def dashboard_view(request):
    """
    Main ERP dashboard displaying financial overview, charts, and recent sync activity.
    """
    company = getattr(request, 'active_company', None)
    all_companies = Company.objects.all()

    # Scope queries to active company, or show nothing if none selected
    if company:
        company_filter = Q(company=company)
    else:
        company_filter = Q(pk=None)  # Returns empty queryset

    # ─── Voucher Counts ───
    sales_count = Voucher.objects.filter(company_filter, voucher_type=VoucherType.SALES).count()
    purchases_count = Voucher.objects.filter(company_filter, voucher_type=VoucherType.PURCHASE).count()
    payments_count = Voucher.objects.filter(company_filter, voucher_type=VoucherType.PAYMENT).count()
    receipts_count = Voucher.objects.filter(company_filter, voucher_type=VoucherType.RECEIPT).count()

    # ─── Voucher Totals (sum of Debit entries per type) ───
    sales_total = VoucherEntry.objects.filter(
        company_filter,
        voucher__voucher_type=VoucherType.SALES,
        entry_type=EntryType.DEBIT
    ).aggregate(total=Sum('amount'))['total'] or 0

    purchases_total = VoucherEntry.objects.filter(
        company_filter,
        voucher__voucher_type=VoucherType.PURCHASE,
        entry_type=EntryType.DEBIT
    ).aggregate(total=Sum('amount'))['total'] or 0

    payments_total = VoucherEntry.objects.filter(
        company_filter,
        voucher__voucher_type=VoucherType.PAYMENT,
        entry_type=EntryType.DEBIT
    ).aggregate(total=Sum('amount'))['total'] or 0

    receipts_total = VoucherEntry.objects.filter(
        company_filter,
        voucher__voucher_type=VoucherType.RECEIPT,
        entry_type=EntryType.DEBIT
    ).aggregate(total=Sum('amount'))['total'] or 0

    # ─── Sync Status ───
    sync_success = SyncLog.objects.filter(company_filter, status='SUCCESS').count()
    sync_failed = SyncLog.objects.filter(company_filter, status='FAILED').count()
    last_sync = SyncLog.objects.filter(company_filter).order_by('-created_at').first()

    # ─── Recent Logs ───
    recent_logs = SyncLog.objects.filter(company_filter).order_by('-created_at')[:5]

    # ─── Chart Aggregations ───
    # Helper to format month aggregations
    def get_monthly_sums(voucher_type):
        qs = VoucherEntry.objects.filter(
            company_filter,
            voucher__voucher_type=voucher_type,
            entry_type=EntryType.DEBIT
        ).annotate(
            month=TruncMonth('voucher__date')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')
        
        return {item['month'].strftime('%b %Y'): float(item['total']) for item in qs if item['month']}

    sales_trend = get_monthly_sums(VoucherType.SALES)
    payments_trend = get_monthly_sums(VoucherType.PAYMENT)
    receipts_trend = get_monthly_sums(VoucherType.RECEIPT)

    # Ensure all months present in any list exist in the others for chart alignment
    all_months = sorted(list(set(list(sales_trend.keys()) + list(payments_trend.keys()) + list(receipts_trend.keys()))))
    
    chart_data = {
        'labels': all_months,
        'sales': [sales_trend.get(m, 0) for m in all_months],
        'payments': [payments_trend.get(m, 0) for m in all_months],
        'receipts': [receipts_trend.get(m, 0) for m in all_months],
    }

    context = {
        'active_page': 'dashboard',
        'sales_count': sales_count,
        'purchases_count': purchases_count,
        'payments_count': payments_count,
        'receipts_count': receipts_count,
        'sales_total': f"{sales_total:,.2f}",
        'purchases_total': f"{purchases_total:,.2f}",
        'payments_total': f"{payments_total:,.2f}",
        'receipts_total': f"{receipts_total:,.2f}",
        'sync_success': sync_success,
        'sync_failed': sync_failed,
        'last_sync_time': last_sync.created_at if last_sync else None,
        'recent_logs': recent_logs,
        'chart_data_json': json.dumps(chart_data),
        'all_companies': all_companies,
        'active_company': company,
    }
    return render(request, 'dashboard.html', context)


@login_required
def sync_logs_view(request):
    """
    Paginated sync log page with status filtering.
    """
    company = getattr(request, 'active_company', None)
    if company:
        company_filter = Q(company=company)
    else:
        company_filter = Q(pk=None)
    filter_status = request.GET.get('status', '')

    logs_qs = SyncLog.objects.filter(company_filter).order_by('-created_at')

    if filter_status in ('SUCCESS', 'FAILED'):
        logs_qs = logs_qs.filter(status=filter_status)

    # ─── Summary Stats ───
    all_logs = SyncLog.objects.filter(company_filter)
    total_logs = all_logs.count()
    success_count = all_logs.filter(status='SUCCESS').count()
    failed_count = all_logs.filter(status='FAILED').count()
    total_records = all_logs.aggregate(total=Sum('records_affected'))['total'] or 0

    # ─── Pagination ───
    paginator = Paginator(logs_qs, 20)
    page_number = request.GET.get('page', 1)
    logs = paginator.get_page(page_number)

    context = {
        'active_page': 'sync_logs',
        'logs': logs,
        'filter_status': filter_status,
        'total_logs': total_logs,
        'success_count': success_count,
        'failed_count': failed_count,
        'total_records': total_records,
        'active_company': company,
        'all_companies': Company.objects.all(),
    }
    return render(request, 'sync_logs.html', context)


@login_required
@role_required(['Admin', 'Accountant'])
@require_POST
def trigger_sync_view(request):
    """
    AJAX endpoint to manually trigger Ledgers or Vouchers sync.
    """
    try:
        data = json.loads(request.body)
        sync_type = data.get('type')
        
        company = getattr(request, 'active_company', None)
        if not company:
            return JsonResponse({'status': 'error', 'message': 'No company selected. Please select a company first.'}, status=400)
        service = TallySyncService(company, request.user)

        if sync_type == 'ledgers':
            count = service.sync_ledgers_from_tally()
            return JsonResponse({'status': 'success', 'message': f'Successfully imported {count} ledgers from Tally.'})
        
        elif sync_type == 'ledgers_push':
            result = service.push_all_ledgers_to_tally()
            msg = f"Upload to Tally complete. Success: {result['success']}, Failed: {result['failed']}."
            return JsonResponse({'status': 'success', 'message': msg})
        
        elif sync_type == 'stock_items':
            count = service.sync_stock_items_from_tally()
            return JsonResponse({'status': 'success', 'message': f'Successfully imported {count} stock items.'})

        elif sync_type == 'stock_items_push':
            # Batch push for stock items
            items = StockItem.objects.filter(company=service.company)
            success = 0
            for item in items:
                if service.push_stock_item_to_tally(item):
                    success += 1
            return JsonResponse({'status': 'success', 'message': f'Successfully uploaded {success} items to Tally.'})

        elif sync_type == 'vouchers_fetch':
             from_date = data.get('from_date')
             to_date = data.get('to_date')
             v_type_label = data.get('voucher_type_label', 'Sales') # Default to Sales
             
             if not from_date or not to_date:
                 return JsonResponse({'status': 'error', 'message': 'Date range is required for voucher import.'})
             
             count = service.sync_vouchers_from_tally(v_type_label, from_date, to_date)
             return JsonResponse({'status': 'success', 'message': f'Successfully fetched {count} {v_type_label} vouchers.'})

        elif sync_type == 'vouchers':
            result = service.push_all_unsynced_vouchers()
            msg = f"Synced {result['success']} vouchers. Failed: {result['failed']}."
            return JsonResponse({'status': 'success', 'message': msg})
            
        return JsonResponse({'status': 'error', 'message': 'Invalid sync type.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@role_required(['Admin', 'Accountant'])
@require_POST
def retry_sync_log_view(request, log_id):
    """
    AJAX endpoint to retry a failed sync log operation.
    """
    log = get_object_or_404(SyncLog, id=log_id)
    company = getattr(request, 'active_company', None)
    if not company:
        return JsonResponse({'status': 'error', 'message': 'No company selected. Please select a company first.'}, status=400)
    service = TallySyncService(company, request.user)

    try:
        if log.model_name == 'Ledger' and log.operation == 'FETCH':
            count = service.sync_ledgers_from_tally()
            return JsonResponse({'status': 'success', 'message': f'Retry complete. Synced {count} ledgers.'})
        
        elif log.model_name == 'Voucher' and log.operation == 'PUSH':
            result = service.push_all_unsynced_vouchers()
            msg = f"Retry complete. Synced {result['success']} unsynced vouchers."
            return JsonResponse({'status': 'success', 'message': msg})
            
        return JsonResponse({'status': 'error', 'message': 'Unsupported retry operation.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def about_project_view(request):
    """
    Static page explaining the ERP architecture and data flows.
    """
    context = {'active_page': 'about_project'}
    return render(request, 'about.html', context)


@login_required
@role_required(['Admin', 'Accountant'])
def masters_hub_view(request):
    """
    Tally-style 'Create Masters' hub page.
    """
    company = getattr(request, 'active_company', None)
    
    accounting_masters = [
        {'slug': 'group', 'label': 'Group'},
        {'slug': 'ledger', 'label': 'Ledger'},
        {'slug': 'currency', 'label': 'Currency'},
        {'slug': 'budget', 'label': 'Budget'},
        {'slug': 'scenario', 'label': 'Scenario'},
        {'slug': 'vouchertype', 'label': 'Voucher Type'},
    ]
    
    inventory_masters = [
        {'slug': 'stockgroup', 'label': 'Stock Group'},
        {'slug': 'stockcategory', 'label': 'Stock Category'},
        {'slug': 'stockitem', 'label': 'Stock Item'},
        {'slug': 'unit', 'label': 'Unit'},
        {'slug': 'location', 'label': 'Location (Godown)'},
    ]
    
    return render(request, 'masters_hub.html', {
        'active_page': 'masters',
        'company': company,
        'accounting_masters': accounting_masters,
        'inventory_masters': inventory_masters,
    })


@login_required
@role_required(['Admin', 'Accountant'])
def generic_master_view(request, slug):
    """
    A dynamic view to handle listing and creation of various simple Tally masters.
    """
    company = getattr(request, 'active_company', None)
    
    # Map slugs to Models
    master_map = {
        'group': (LedgerGroup, 'Accounting Group'),
        'ledger': (Ledger, 'Ledger'),
        'currency': (Currency, 'Currency'),
        'budget': (Budget, 'Budget'),
        'scenario': (Scenario, 'Scenario'),
        'vouchertype': (CustomVoucherType, 'Custom Voucher Type'),
        'stockgroup': (StockGroup, 'Stock Group'),
        'stockcategory': (StockCategory, 'Stock Category'),
        'stockitem': (StockItem, 'Stock Item'),
        'unit': (Unit, 'Unit of Measure'),
        'location': (Location, 'Location (Godown)'),
    }
    
    if slug not in master_map:
        raise Http404("Master type not found.")
    
    model_class, label = master_map[slug]
    
    # Handle redirects for complex masters that have their own dedicated views
    if slug == 'ledger':
        return redirect('ledger_create')
    if slug == 'stockitem':
        return redirect('inventory_create')

    # Create dynamic form
    excluded_fields = [
        'company', 'sync_status', 'tally_id', 'last_synced_at',
        'created_by', 'updated_by', 'is_active', 'created_at', 'updated_at'
    ]
    MasterForm = modelform_factory(
        model_class, 
        exclude=excluded_fields,
        help_texts={'parent': 'Under'}  # Tally uses 'Under' instead of 'Parent'
    )
    
    # Customizing labels and classes for better UI
    class StylizedMasterForm(MasterForm):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if 'parent' in self.fields:
                self.fields['parent'].label = "Under"
    
    if request.method == 'POST':
        form = StylizedMasterForm(request.POST)
        if form.is_valid():
            master_instance = form.save(commit=False)
            master_instance.company = company
            if hasattr(master_instance, 'created_by'):
                master_instance.created_by = request.user
            master_instance.save()
            messages.success(request, f"{label} '{master_instance}' created successfully.")
            return redirect('masters_hub')
    else:
        form = StylizedMasterForm()

    # Get existing records for this company and prepare them for the generic template
    raw_items = model_class.objects.filter(company=company).order_by('name' if hasattr(model_class, 'name') else 'pk')
    
    processed_items = []
    for item in raw_items:
        processed_items.append({
            'id': item.id,
            'display_name': getattr(item, 'name', getattr(item, 'symbol', str(item))),
            'display_details': getattr(item, 'formal_name', str(getattr(item, 'parent', '—'))),
            'raw_object': item
        })

    return render(request, 'master_generic_form.html', {
        'active_page': 'masters',
        'label': label,
        'slug': slug,
        'form': form,
        'existing_items': processed_items,
        'company': company,
    })
