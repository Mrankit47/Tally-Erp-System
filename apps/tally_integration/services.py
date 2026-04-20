"""
Tally Integration Services.

Orchestrates the data flow between Django and Tally, ensuring 
transactional safety and detailed auditing via SyncLog.
"""

import time
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.core.exceptions import ValidationError
from .client import TallyClient, TallyClientError
from .xml_utilities import TallyXMLGenerator, TallyXMLParser
from .models import SyncLog, SyncOperation, SyncStatus
from ledger.models import Ledger, LedgerGroup
from inventory.models import StockItem
from voucher.models import Voucher, VoucherType, EntryType
from core.models import SyncStatus as ModelSyncStatus

import logging
logger = logging.getLogger('apps.tally_integration')


class TallySyncService:
    """
    Enterprise service for bi-directional Tally synchronization.
    """

    def __init__(self, company, user):
        self.company = company
        self.user = user
        self.client = TallyClient()
        self.generator = TallyXMLGenerator()
        self.parser = TallyXMLParser()

    # =========================================================================
    # LEDGER SYNC (Inward — Tally → Django)
    # =========================================================================

    @transaction.atomic
    def sync_ledgers_from_tally(self):
        """
        Fetches all ledgers from Tally and synchronizes them with the local DB.
        Strategy: Tally is the source of truth.
        """
        log = SyncLog.objects.create(
            company=self.company,
            created_by=self.user,
            model_name='Ledger',
            operation=SyncOperation.FETCH,
            status=SyncStatus.FAILED
        )

        try:
            xml_request = self.generator.get_fetch_ledger_xml()
            xml_response = self.client.post_with_retry(xml_request)

            tally_ledgers = self.parser.parse_ledgers(xml_response)
            
            if not tally_ledgers:
                logger.warning(f"Tally Sync: No ledgers found. Raw response length: {len(xml_response)}")
                log.message = f"No ledgers found in Tally response (Length: {len(xml_response)} bytes)."
                log.save()
                return 0

            default_group, _ = LedgerGroup.objects.get_or_create(
                company=self.company,
                name='Primary',
                defaults={'created_by': self.user}
            )

            success_count = 0
            synced_record_ids = []

            for data in tally_ledgers:
                # 1. Handle Group
                group, group_created = LedgerGroup.objects.get_or_create(
                    company=self.company,
                    name=data['parent'],
                    defaults={'created_by': self.user, 'parent': default_group}
                )
                if group_created:
                    synced_record_ids.append(str(group.id))

                # 2. Handle Ledger
                ledger, _ = Ledger.objects.update_or_create(
                    company=self.company,
                    name=data['name'],
                    defaults={
                        'group': group,
                        'opening_balance': data['opening_balance'],
                        'tally_id': data['name'],
                        'sync_status': ModelSyncStatus.SYNCED,
                        'last_synced_at': timezone.now(),
                        'updated_by': self.user,
                    }
                )
                synced_record_ids.append(str(ledger.id))
                success_count += 1

            log.status = SyncStatus.SUCCESS
            log.message = f"Successfully synchronized {success_count} ledgers from Tally."
            log.records_affected = success_count
            log.synced_ids = synced_record_ids
            log.save()
            
            return success_count

        except TallyClientError as e:
            log.message = f"Network Error: {str(e)}"
            log.save()
            raise
        except Exception as e:
            log.message = f"Unexpected Error: {str(e)}"
            log.save()
            raise

    # =========================================================================
    # INVENTORY SYNC (Inward — Tally → Django)
    # =========================================================================

    @transaction.atomic
    def sync_stock_items_from_tally(self):
        """Fetches and syncs all stock items from Tally."""
        log = SyncLog.objects.create(
            company=self.company,
            created_by=self.user,
            model_name='StockItem',
            operation=SyncOperation.FETCH,
            status=SyncStatus.FAILED
        )
        try:
            xml_request = self.generator.get_fetch_stock_item_xml()
            xml_response = self.client.post_with_retry(xml_request)
            tally_items = self.parser.parse_stock_items(xml_response)

            if not tally_items:
                log.message = "No stock items found in Tally response."
                log.save()
                return 0

            success_count = 0
            synced_record_ids = []
            for item in tally_items:
                si, _ = StockItem.objects.update_or_create(
                    company=self.company,
                    name=item['name'],
                    defaults={
                        'unit_of_measure': item['unit_of_measure'],
                        'tally_id': item['name'],
                        'sync_status': ModelSyncStatus.SYNCED,
                        'last_synced_at': timezone.now(),
                        'updated_by': self.user,
                    }
                )
                synced_record_ids.append(str(si.id))
                success_count += 1

            log.status = SyncStatus.SUCCESS
            log.message = f"Successfully synchronized {success_count} stock items from Tally."
            log.records_affected = success_count
            log.synced_ids = synced_record_ids
            log.save()
            return success_count
        except Exception as e:
            log.message = f"Inward Stock Sync Error: {str(e)}"
            log.save()
            raise

    # =========================================================================
    # LEDGER PUSH (Outward — Django → Tally)
    # =========================================================================

    def push_ledger_to_tally(self, ledger):
        """
        Creates a single local Ledger master in Tally.
        """
        log = SyncLog.objects.create(
            company=self.company,
            created_by=self.user,
            model_name='Ledger',
            operation=SyncOperation.PUSH,
            status=SyncStatus.FAILED
        )

        try:
            # Guard: Already synced
            if ledger.tally_id and ledger.sync_status == ModelSyncStatus.SYNCED:
                log.message = f"Skipping push: Ledger '{ledger.name}' already synced."
                log.status = SyncStatus.SUCCESS
                log.save()
                return True

            xml_request = self.generator.get_create_ledger_xml(
                name=ledger.name,
                parent=ledger.group.name,
                opening_balance=ledger.opening_balance
            )
            xml_response = self.client.post_with_retry(xml_request)

            if self.parser.is_import_successful(xml_response):
                ledger.sync_status = ModelSyncStatus.SYNCED
                ledger.tally_id = ledger.name
                ledger.last_synced_at = timezone.now()
                ledger.save(update_fields=['sync_status', 'tally_id', 'last_synced_at'])
                
                log.status = SyncStatus.SUCCESS
                log.message = f"Ledger '{ledger.name}' successfully created in Tally."
                log.records_affected = 1
                log.synced_ids = [str(ledger.id)]
                log.save()
                return True
            else:
                error_msg = self.parser.extract_error_message(xml_response)
                ledger.sync_status = ModelSyncStatus.FAILED
                ledger.save(update_fields=['sync_status'])
                
                log.message = f"Tally Validation Error: {error_msg}"
                log.response_xml = xml_response[:2000]
                log.save()
                return False

        except TallyClientError as e:
            log.message = f"Network Error: {str(e)}"
            log.save()
            return False
        except Exception as e:
            log.message = f"Unexpected Error: {str(e)}"
            log.save()
            return False

    # =========================================================================
    # VOUCHER PUSH (Outward — Django → Tally)
    # Supports: Sales, Payment, Receipt
    # =========================================================================

    @transaction.atomic
    def push_sales_voucher_to_tally(self, voucher):
        """
        Pushes a Sales Voucher (Invoice) to Tally.

        Accounting: Customer (Dr) / Sales Revenue (Cr)
        """
        return self._push_voucher_to_tally(
            voucher=voucher,
            expected_type=VoucherType.SALES,
            xml_generator=self.generator.get_sales_voucher_xml,
            label='Sales',
        )

    @transaction.atomic
    def push_payment_voucher_to_tally(self, voucher):
        """
        Pushes a Payment Voucher to Tally.

        Accounting: Expense/Vendor (Dr) / Cash or Bank (Cr)
        """
        return self._push_voucher_to_tally(
            voucher=voucher,
            expected_type=VoucherType.PAYMENT,
            xml_generator=self.generator.get_payment_voucher_xml,
            label='Payment',
        )

    @transaction.atomic
    def push_receipt_voucher_to_tally(self, voucher):
        """
        Pushes a Receipt Voucher to Tally.

        Accounting: Cash/Bank (Dr) / Party or Income (Cr)
        """
        return self._push_voucher_to_tally(
            voucher=voucher,
            expected_type=VoucherType.RECEIPT,
            xml_generator=self.generator.get_receipt_voucher_xml,
            label='Receipt',
        )

    def _push_voucher_to_tally(self, voucher, expected_type, xml_generator, label):
        """
        Internal engine that handles the full push lifecycle for any voucher type.

        Guards:
            1. Voucher type must match `expected_type`.
            2. Voucher must not already be synced (duplicate protection via tally_id).
            3. Voucher must be balanced (Sum Debit == Sum Credit).
            4. Voucher must have at least one entry.

        Flow:
            Validate → Generate XML → Send via TallyClient → Parse response →
            Update sync state → Log in SyncLog.

        Args:
            voucher: Django Voucher model instance.
            expected_type: The VoucherType enum value to enforce.
            xml_generator: Callable that accepts a voucher and returns XML string.
            label: Human-readable label for log messages (e.g., 'Sales', 'Payment').

        Returns:
            bool: True if push succeeded, False otherwise.
        """
        log = SyncLog.objects.create(
            company=self.company,
            created_by=self.user,
            model_name='Voucher',
            operation=SyncOperation.PUSH,
            status=SyncStatus.FAILED
        )

        try:
            # ─── GUARD 1: Voucher type enforcement ───
            if voucher.voucher_type != expected_type:
                log.message = (
                    f"Rejected: Voucher '{voucher.number}' is type '{voucher.voucher_type}', "
                    f"expected '{expected_type}'. Use the correct push method."
                )
                log.save()
                return False

            # ─── GUARD 2: Duplicate protection ───
            if voucher.tally_id and voucher.sync_status == ModelSyncStatus.SYNCED:
                log.message = (
                    f"Skipping push: {label} Voucher '{voucher.number}' already synced "
                    f"with Tally ID '{voucher.tally_id}'."
                )
                log.status = SyncStatus.SUCCESS
                log.save()
                return True

            # ─── GUARD 3: Entries existence ───
            entries = voucher.entries.all()
            if not entries.exists():
                log.message = f"Rejected: {label} Voucher '{voucher.number}' has no entries."
                log.save()
                return False

            # ─── GUARD 4: Accounting balance validation ───
            dr_total = entries.filter(
                entry_type=EntryType.DEBIT
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            cr_total = entries.filter(
                entry_type=EntryType.CREDIT
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            if dr_total != cr_total:
                log.message = (
                    f"Accounting Mismatch: {label} Voucher '{voucher.number}' — "
                    f"Total Debit ({dr_total}) != Total Credit ({cr_total}). "
                    f"Push aborted."
                )
                log.save()
                return False

            # ─── GENERATE XML ───
            logger.info(f"Generating {label} Voucher XML for '{voucher.number}'")
            xml_request = xml_generator(voucher)

            # ─── SEND TO TALLY ───
            logger.info(f"Sending {label} Voucher '{voucher.number}' to Tally")
            xml_response = self.client.post_with_retry(xml_request)

            # ─── PARSE RESPONSE ───
            if self.parser.is_import_successful(xml_response):
                voucher.sync_status = ModelSyncStatus.SYNCED
                voucher.tally_id = voucher.number
                voucher.last_synced_at = timezone.now()
                voucher.save(update_fields=['sync_status', 'tally_id', 'last_synced_at'])

                stats = self.parser.extract_import_stats(xml_response)
                log.status = SyncStatus.SUCCESS
                log.message = (
                    f"{label} Voucher '{voucher.number}' successfully created in Tally. "
                    f"Stats: Created={stats['created']}, Errors={stats['errors']}"
                )
                log.records_affected = 1
                log.synced_ids = [str(voucher.id)]
                log.save()

                logger.info(f"{label} Voucher '{voucher.number}' synced to Tally successfully.")
                return True

            else:
                error_msg = self.parser.extract_error_message(xml_response)
                voucher.sync_status = ModelSyncStatus.FAILED
                voucher.save(update_fields=['sync_status'])

                log.message = (
                    f"Tally rejected {label} Voucher '{voucher.number}': {error_msg}"
                )
                log.response_xml = xml_response[:5000]
                log.save()

                logger.error(f"{label} Voucher '{voucher.number}' push FAILED: {error_msg}")
                return False

        except TallyClientError as e:
            log.message = f"Network Error pushing {label} '{voucher.number}': {str(e)}"
            log.save()
            logger.error(f"TallyClientError for {label} voucher '{voucher.number}': {str(e)}")
            return False
        except Exception as e:
            log.message = f"Unexpected Error pushing {label} '{voucher.number}': {str(e)}"
            log.response_xml = str(e)[:2000]
            log.save()
            logger.exception(f"Unexpected error pushing {label} voucher '{voucher.number}'")
            return False

    def push_stock_item_to_tally(self, stock_item):
        """Creates a single Stock Item in Tally."""
        log = SyncLog.objects.create(
            company=self.company,
            created_by=self.user,
            model_name='StockItem',
            operation=SyncOperation.PUSH,
            status=SyncStatus.FAILED
        )
        try:
            xml_request = self.generator.get_create_stock_item_xml(
                name=stock_item.name,
                unit_of_measure=stock_item.unit_of_measure
            )
            xml_response = self.client.post_with_retry(xml_request)

            if self.parser.is_import_successful(xml_response):
                stock_item.sync_status = ModelSyncStatus.SYNCED
                stock_item.tally_id = stock_item.name
                stock_item.last_synced_at = timezone.now()
                stock_item.save(update_fields=['sync_status', 'tally_id', 'last_synced_at'])

                log.status = SyncStatus.SUCCESS
                log.message = f"Stock Item '{stock_item.name}' successfully created in Tally."
                log.records_affected = 1
                log.synced_ids = [str(stock_item.id)]
                log.save()
                return True
            else:
                error_msg = self.parser.extract_error_message(xml_response)
                log.message = f"Tally Rejection: {error_msg}"
                log.save()
                return False
        except Exception as e:
            log.message = f"Push Stock Error: {str(e)}"
            log.save()
            return False

    # =========================================================================
    # BATCH OPERATIONS / RETRY LOGIC
    # =========================================================================

    def push_all_ledgers_to_tally(self):
        """
        Idempotent service to push all local Ledgers for the company to Tally.
        """
        unsynced_ledgers = Ledger.objects.filter(
            company=self.company
        )

        success_count = 0
        failed_count = 0

        for ledger in unsynced_ledgers:
            # push_ledger_to_tally handles duplicate protection
            if self.push_ledger_to_tally(ledger):
                success_count += 1
            else:
                failed_count += 1

        return {
            'success': success_count,
            'failed': failed_count,
            'total': success_count + failed_count
        }

    def push_all_unsynced_vouchers(self):
        """
        Idempotent background/batch service.
        Fetches all PENDING or FAILED vouchers for the company and attempts to push them.
        """
        from voucher.models import Voucher

        unsynced_vouchers = Voucher.objects.filter(
            company=self.company,
            sync_status__in=[ModelSyncStatus.PENDING, ModelSyncStatus.FAILED]
        ).prefetch_related('entries')

        success_count = 0
        failed_count = 0

        for voucher in unsynced_vouchers:
            result = False
            
            # Map type to the correct push method
            if voucher.voucher_type == VoucherType.SALES:
                result = self.push_sales_voucher_to_tally(voucher)
            elif voucher.voucher_type == VoucherType.PAYMENT:
                result = self.push_payment_voucher_to_tally(voucher)
            elif voucher.voucher_type == VoucherType.RECEIPT:
                result = self.push_receipt_voucher_to_tally(voucher)
            else:
                logger.warning(f"Batch Sync: Unsupported voucher type '{voucher.voucher_type}' for '{voucher.number}'")
                continue

            if result:
                success_count += 1
            else:
                failed_count += 1

            # Give Tally ERP a tiny breather to process the XML
            time.sleep(0.5)

        return {
            'success': success_count,
            'failed': failed_count,
            'total': success_count + failed_count
        }

    @transaction.atomic
    def sync_vouchers_from_tally(self, voucher_type_label, from_date, to_date):
        """
        Fetches vouchers from Tally and records them in the SyncLog.
        Dumb Import: We log the data for Audit.
        In a production environment, this would create local Voucher objects.
        """
        log = SyncLog.objects.create(
            company=self.company,
            created_by=self.user,
            model_name='Voucher',
            operation=SyncOperation.FETCH,
            status=SyncStatus.FAILED
        )
        try:
            # Format dates to YYYYMMDD
            fd = from_date.replace('-', '').replace('/', '')
            td = to_date.replace('-', '').replace('/', '')
            
            xml_request = self.generator.get_fetch_vouchers_xml(
                voucher_type=voucher_type_label,
                from_date=fd,
                to_date=td
            )
            xml_response = self.client.post_with_retry(xml_request)
            tally_vouchers = self.parser.parse_vouchers_fetch(xml_response)

            if not tally_vouchers:
                log.message = f"No {voucher_type_label} vouchers found for period {from_date} to {to_date}."
                log.save()
                return 0

            # Real import would map ledgers and stock items here.
            # For this version, we save the fetch count and raw response for audit.
            log.status = SyncStatus.SUCCESS
            log.message = f"Successfully fetched {len(tally_vouchers)} {voucher_type_label} vouchers from Tally."
            log.records_affected = len(tally_vouchers)
            log.response_xml = xml_response[:10000] 
            log.save()
            return len(tally_vouchers)
        except Exception as e:
            log.message = f"Voucher Fetch Error: {str(e)}"
            log.save()
            raise
