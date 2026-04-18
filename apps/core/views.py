"""
Core views for the ERP dashboard UI.

Provides the main dashboard and sync log pages using Django templates.
"""

import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Sum, Q
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from voucher.models import Voucher, VoucherType, VoucherEntry, EntryType
from tally_integration.models import SyncLog
from tally_integration.services import TallySyncService
from company.models import Company


@login_required
def dashboard_view(request):
    """
    Main ERP dashboard displaying financial overview, charts, and recent sync activity.
    """
    company_filter = Q()
    # In a real multi-tenant app, scope to user's company:
    # company_filter = Q(company=request.user.company)
    
    company = Company.objects.first() # Default for single-tenant demo
    if not company:
        pass # Handle gracefully in template

    # ─── Voucher Counts ───
    sales_count = Voucher.objects.filter(company_filter, voucher_type=VoucherType.SALES).count()
    payments_count = Voucher.objects.filter(company_filter, voucher_type=VoucherType.PAYMENT).count()
    receipts_count = Voucher.objects.filter(company_filter, voucher_type=VoucherType.RECEIPT).count()

    # ─── Voucher Totals (sum of Debit entries per type) ───
    sales_total = VoucherEntry.objects.filter(
        company_filter,
        voucher__voucher_type=VoucherType.SALES,
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
        'payments_count': payments_count,
        'receipts_count': receipts_count,
        'sales_total': f"{sales_total:,.2f}",
        'payments_total': f"{payments_total:,.2f}",
        'receipts_total': f"{receipts_total:,.2f}",
        'sync_success': sync_success,
        'sync_failed': sync_failed,
        'last_sync_time': last_sync.created_at if last_sync else None,
        'recent_logs': recent_logs,
        'chart_data_json': json.dumps(chart_data),
    }
    return render(request, 'dashboard.html', context)


@login_required
def sync_logs_view(request):
    """
    Paginated sync log page with status filtering.
    """
    company_filter = Q()
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
    }
    return render(request, 'sync_logs.html', context)


@login_required
@require_POST
def trigger_sync_view(request):
    """
    AJAX endpoint to manually trigger Ledgers or Vouchers sync.
    """
    try:
        data = json.loads(request.body)
        sync_type = data.get('type')
        
        company = Company.objects.first()
        service = TallySyncService(company, request.user)

        if sync_type == 'ledgers':
            count = service.sync_ledgers_from_tally()
            return JsonResponse({'status': 'success', 'message': f'Successfully synced {count} ledgers.'})
        
        elif sync_type == 'vouchers':
            result = service.push_all_unsynced_vouchers()
            msg = f"Synced {result['success']} vouchers. Failed: {result['failed']}."
            return JsonResponse({'status': 'success', 'message': msg})
            
        return JsonResponse({'status': 'error', 'message': 'Invalid sync type.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def retry_sync_log_view(request, log_id):
    """
    AJAX endpoint to retry a failed sync log operation.
    """
    log = get_object_or_404(SyncLog, id=log_id)
    company = Company.objects.first()
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
