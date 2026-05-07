"""
Tally Integration Services.

Orchestrates the data flow between Django and Tally, ensuring 
transactional safety and detailed auditing via SyncLog.
"""

import time
import datetime
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.core.exceptions import ValidationError
from .client import TallyClient, TallyClientError
from .xml_utilities import TallyXMLGenerator, TallyXMLParser
from .models import SyncLog, SyncOperation, SyncStatus
from ledger.models import Ledger, LedgerGroup
from inventory.models import StockItem, StockTransaction, TransactionType, StockGroup
from voucher.models import Voucher, VoucherEntry, VoucherType, EntryType
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

    @classmethod
    def fetch_all_tally_companies(cls, user):
        """
        Fetches all open companies from Tally and syncs them to the local database.
        Returns a list of Company objects.
        """
        client = TallyClient()
        generator = TallyXMLGenerator()
        parser = TallyXMLParser()
        
        try:
            xml_request = generator.get_fetch_companies_xml()
            xml_response = client.post_with_retry(xml_request)
            tally_companies = parser.parse_companies(xml_response)
            
            from company.models import Company
            synced_companies = []
            
            for comp_data in tally_companies:
                company, created = Company.objects.update_or_create(
                    name=comp_data['name'],
                    defaults={
                        'financial_year_start': timezone.now().date().replace(month=4, day=1),
                        'financial_year_end': timezone.now().date().replace(year=timezone.now().year+1, month=3, day=31),
                    }
                )
                if created:
                    company.created_by = user
                    company.save(update_fields=['created_by'])
                synced_companies.append(company)
                
            return synced_companies
        except Exception as e:
            logger.error(f"Failed to fetch companies from Tally: {str(e)}")
            raise

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
            xml_request = self.generator.get_fetch_ledger_xml(company_name=self.company.name)
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
            xml_request = self.generator.get_fetch_stock_item_xml(company_name=self.company.name)
            xml_response = self.client.post_with_retry(xml_request)
            tally_items = self.parser.parse_stock_items(xml_response)

            if not tally_items:
                log.message = "No stock items found in Tally response."
                log.save()
                return 0

            default_group, _ = StockGroup.objects.get_or_create(
                company=self.company,
                name='Primary',
                defaults={'created_by': self.user}
            )

            success_count = 0
            synced_record_ids = []
            for item in tally_items:
                # 1. Handle Group recursively map
                group, _ = StockGroup.objects.get_or_create(
                    company=self.company,
                    name=item['parent'],
                    defaults={'created_by': self.user, 'parent': default_group}
                )

                # 2. Handle Stock Item
                si, _ = StockItem.objects.update_or_create(
                    company=self.company,
                    name=item['name'],
                    defaults={
                        'group': group,
                        'unit_of_measure': item['unit_of_measure'],
                        'opening_stock_qty': item['opening_balance'],
                        'closing_stock_qty': item.get('closing_balance', 0),
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

            parent_group = ledger.group.name if ledger.group else 'Suspense A/c'
            if parent_group.lower() == 'primary':
                parent_group = 'Suspense A/c'
                
            xml_request = self.generator.get_create_ledger_xml(
                name=ledger.name,
                parent=parent_group,
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
    def push_purchase_voucher_to_tally(self, voucher):
        """
        Pushes a Purchase Voucher to Tally.

        Accounting: Purchase Account (Dr) / Vendor (Cr)
        """
        return self._push_voucher_to_tally(
            voucher=voucher,
            expected_type=VoucherType.PURCHASE,
            xml_generator=self.generator.get_purchase_voucher_xml,
            label='Purchase',
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

            # ─── AUTO-CREATE LEDGERS IN TALLY ───
            logger.info(f"Auto-ensuring ledgers exist in Tally for '{voucher.number}'")
            for entry in entries:
                ledger = entry.ledger
                parent_group = ledger.group.name if ledger.group else 'Sundry Debtors'
                if parent_group.lower() == 'primary':
                    parent_group = 'Suspense A/c'
                ledger_xml = self.generator.get_create_ledger_xml(
                    name=ledger.name,
                    parent=parent_group,
                    opening_balance=0
                )
                try:
                    self.client.post_with_retry(ledger_xml)
                    logger.info(f"  Ensured ledger '{ledger.name}' under '{parent_group}' in Tally")
                except Exception as le:
                    logger.warning(f"  Ledger '{ledger.name}' push note: {le}")

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
                unit=stock_item.unit_of_measure
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
            elif voucher.voucher_type == VoucherType.PURCHASE:
                result = self.push_purchase_voucher_to_tally(voucher)
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
        Fetches vouchers from Tally and creates them locally.
        Ensures Ledgers and StockItems exist.
        """
        log = SyncLog.objects.create(
            company=self.company,
            created_by=self.user,
            model_name='Voucher',
            operation=SyncOperation.FETCH,
            status=SyncStatus.FAILED
        )
        try:
            # Map UI label to VoucherType
            type_map = {
                'sales': VoucherType.SALES,
                'payments': VoucherType.PAYMENT,
                'payment': VoucherType.PAYMENT,
                'receipts': VoucherType.RECEIPT,
                'receipt': VoucherType.RECEIPT,
                'contra': VoucherType.CONTRA,
                'journal': VoucherType.JOURNAL,
                'purchase': VoucherType.PURCHASE
            }
            target_type = type_map.get(voucher_type_label.lower())
            if not target_type:
                raise ValueError(f"Unknown voucher type: {voucher_type_label}")

            # Format dates to YYYYMMDD
            fd = from_date.replace('-', '').replace('/', '')
            td = to_date.replace('-', '').replace('/', '')
            
            xml_request = self.generator.get_fetch_vouchers_xml(
                voucher_type=voucher_type_label,
                from_date=fd,
                to_date=td,
                company_name=self.company.name
            )
            xml_response = self.client.post_with_retry(xml_request)
            tally_vouchers = self.parser.parse_vouchers_fetch(xml_response)

            if not tally_vouchers:
                log.message = f"No {voucher_type_label} vouchers found for period {from_date} to {to_date}."
                log.save()
                return 0

            primary_group, _ = LedgerGroup.objects.get_or_create(
                company=self.company,
                name='Primary',
                defaults={'created_by': self.user}
            )

            success_count = 0
            synced_record_ids = []

            # ─── Cache for performance ───
            ledger_cache = {}
            stock_cache = {}

            for v_data in tally_vouchers:
                # 1. Parse Date
                v_date_str = v_data.get('date', '')
                v_date = timezone.now().date()
                if v_date_str and len(v_date_str) == 8:
                    try:
                        v_date = datetime.datetime.strptime(v_date_str, '%Y%m%d').date()
                    except ValueError:
                        pass

                vid = v_data.get('number')
                if not vid:
                    continue

                # 2. Create or Update Voucher
                voucher, created = Voucher.objects.update_or_create(
                    company=self.company,
                    tally_id=vid,
                    voucher_type=target_type,
                    defaults={
                        'number': vid,
                        'date': v_date,
                        'narration': v_data.get('narration') or '',
                        'party_name': v_data.get('party_name') or '',
                        'is_posted': True,
                        'sync_status': ModelSyncStatus.SYNCED,
                        'last_synced_at': timezone.now(),
                        'updated_by': self.user,
                    }
                )
                
                if created:
                    voucher.created_by = self.user
                    voucher.save(update_fields=['created_by'])

                synced_record_ids.append(str(voucher.id))
                voucher.entries.all().delete()

                # 3. Create Entries (Batch processing could be better, but we need IDs for StockTransactions)
                for e_data in v_data.get('entries', []):
                    # Resolve Ledger with Cache
                    ledger_name = e_data.get('ledger') or 'Suspense A/C'
                    if ledger_name not in ledger_cache:
                        ledger, _ = Ledger.objects.get_or_create(
                            company=self.company,
                            name=ledger_name,
                            defaults={'group': primary_group, 'sync_status': ModelSyncStatus.PENDING, 'created_by': self.user}
                        )
                        ledger_cache[ledger_name] = ledger
                    ledger = ledger_cache[ledger_name]

                    # Resolve Stock Item with Cache
                    stock_item_name = e_data.get('stock_item')
                    stock_item = None
                    if stock_item_name:
                        if stock_item_name not in stock_cache:
                            si, _ = StockItem.objects.get_or_create(
                                company=self.company,
                                name=stock_item_name,
                                defaults={'sync_status': ModelSyncStatus.PENDING, 'created_by': self.user}
                            )
                            stock_cache[stock_item_name] = si
                        stock_item = stock_cache[stock_item_name]

                    entry_type = EntryType.DEBIT if e_data.get('is_debit') else EntryType.CREDIT
                    qty = e_data.get('quantity')
                    amt = e_data.get('amount') or Decimal('0.00')
                    
                    rate = None
                    if qty and qty > 0:
                        rate = amt / qty

                    # Create VoucherEntry
                    entry = VoucherEntry.objects.create(
                        company=self.company,
                        voucher=voucher,
                        ledger=ledger,
                        amount=amt,
                        entry_type=entry_type,
                        stock_item=stock_item,
                        quantity=qty,
                        rate=rate,
                        created_by=self.user,
                        updated_by=self.user
                    )

                    # 4. Create StockTransaction
                    if stock_item:
                        tx_type = TransactionType.OUT if target_type == VoucherType.SALES else TransactionType.IN
                        StockTransaction.objects.create(
                            company=self.company,
                            stock_item=stock_item,
                            voucher_entry=entry,
                            quantity=qty or Decimal('0.00'),
                            rate=rate or Decimal('0.00'),
                            transaction_type=tx_type,
                            created_by=self.user,
                            updated_by=self.user
                        )

                # Compute party_name if missing
                if not voucher.party_name:
                    party_entry = None
                    if target_type == VoucherType.SALES:
                        party_entry = voucher.entries.filter(entry_type=EntryType.DEBIT).first()
                    elif target_type == VoucherType.RECEIPT:
                        party_entry = voucher.entries.filter(entry_type=EntryType.CREDIT).first()
                    elif target_type == VoucherType.PAYMENT:
                        party_entry = voucher.entries.filter(entry_type=EntryType.DEBIT).first()
                    
                    if party_entry:
                        voucher.party_name = party_entry.ledger.name
                        voucher.save(update_fields=['party_name'])

                success_count += 1

            log.status = SyncStatus.SUCCESS
            log.message = f"Successfully synchronized {success_count} {voucher_type_label} vouchers from Tally."
            log.records_affected = success_count
            log.synced_ids = synced_record_ids
            log.save()
            
            return success_count
        except Exception as e:
            log.message = f"Voucher Fetch Error: {str(e)}"
            log.save()
            logger.exception("Voucher sync failed")
            raise
