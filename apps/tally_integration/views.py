import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from core.permissions import role_required
from company.models import Company
from voucher.models import Voucher, VoucherType, VoucherStatus
from .services import TallySyncService


def _get_active_company(request):
    """
    Helper to get the active company from the request (set by middleware).
    Returns (company, error_response) — if error_response is not None, return it immediately.
    """
    company = getattr(request, 'active_company', None)
    if not company:
        return None, JsonResponse(
            {'status': 'error', 'message': 'No company selected. Please select a company first.'},
            status=400
        )
    return company, None


@login_required
@role_required(['Admin', 'Accountant', 'Manager'])
@require_POST
def sync_single_voucher_view(request, voucher_id):
    """AJAX endpoint to sync a specific voucher to Tally."""
    company, error = _get_active_company(request)
    if error:
        return error
    voucher = get_object_or_404(Voucher, id=voucher_id, company=company)
    
    if voucher.status != VoucherStatus.APPROVED:
        return JsonResponse({
            'status': 'error', 
            'message': 'Invoice is not approved yet. Please approve the invoice before pushing to Tally.'
        }, status=400)
        
    service = TallySyncService(company, request.user)
    
    # Map voucher type to service method
    type_method_map = {
        VoucherType.SALES: service.push_sales_voucher_to_tally,
        VoucherType.PURCHASE: service.push_purchase_voucher_to_tally,
        VoucherType.PAYMENT: service.push_payment_voucher_to_tally,
        VoucherType.RECEIPT: service.push_receipt_voucher_to_tally,
    }
    
    method = type_method_map.get(voucher.voucher_type)
    if not method:
        return JsonResponse({'status': 'error', 'message': f'Sync not supported for {voucher.voucher_type}'}, status=400)
    
    success = method(voucher)
    if success:
        return JsonResponse({'status': 'success', 'message': f'Voucher {voucher.number} synced successfully.'})
    else:
        return JsonResponse({'status': 'error', 'message': f'Failed to sync {voucher.number}. Check Sync Logs for details.'}, status=500)

from .models import SyncLog, SyncOperation
from ledger.models import Ledger, LedgerGroup
from core.models import SyncStatus as ModelSyncStatus

@login_required
@role_required(['Admin', 'Accountant', 'Manager'])
@require_POST
def delete_sync_log_view(request, log_id):
    """
    Deletes a Sync Log and rolls back the associated records.
    - FETCH: Deletes newly created ERP records.
    - PUSH: Resets ERP records to 'PENDING'.
    """
    company, error = _get_active_company(request)
    if error:
        return error
    log = get_object_or_404(SyncLog, id=log_id, company=company)
    
    synced_ids = log.synced_ids or []
    operation = log.operation
    model_name = log.model_name
    
    try:
        if operation == SyncOperation.FETCH:
            # ROLLBACK: Delete imported records
            if model_name == 'Ledger':
                # Delete Ledgers first, then groups (to honor FKs)
                # We filter by company and ID list for safety
                Ledger.objects.filter(company=company, id__in=synced_ids).delete()
                # Note: LedgerGroup might have other ledgers, so we only delete if empty? 
                # For simplicity, we just delete the specific ones tracked.
                LedgerGroup.objects.filter(company=company, id__in=synced_ids).delete()
            
            elif model_name == 'Voucher':
                Voucher.objects.filter(company=company, id__in=synced_ids).delete()
        
        elif operation == SyncOperation.PUSH:
            # ROLLBACK: Just reset the sync status in ERP
            if model_name == 'Ledger':
                Ledger.objects.filter(company=company, id__in=synced_ids).update(
                    sync_status=ModelSyncStatus.PENDING,
                    tally_id=None
                )
            elif model_name == 'Voucher':
                Voucher.objects.filter(company=company, id__in=synced_ids).update(
                    sync_status=ModelSyncStatus.PENDING,
                    tally_id=None
                )
        
        # Finally delete the log
        log.delete()
        return JsonResponse({'status': 'success', 'message': f'Log deleted and {operation} rolled back.'})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Rollback failed: {str(e)}'}, status=500)

@login_required
@role_required(['Admin', 'Accountant', 'Manager'])
@require_POST
def sync_ledgers_view(request):
    """AJAX endpoint to trigger full ledger sync from Tally."""
    company, error = _get_active_company(request)
    if error:
        return error
    service = TallySyncService(company, request.user)
    try:
        count = service.sync_ledgers_from_tally()
        return JsonResponse({'status': 'success', 'message': f'Successfully imported {count} ledgers from Tally.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
