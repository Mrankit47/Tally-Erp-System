import logging
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Avg
from voucher.models import Voucher, VoucherEntry, EntryType, VoucherType, VoucherStatus
from ledger.models import Ledger
from inventory.models import StockItem

logger = logging.getLogger('apps.ai')

def calculate_revenue_metrics(company) -> dict:
    """Computes total sales, monthly growth, weekly trends, and historical monthly sales."""
    now = timezone.now()
    start_of_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Start of previous month
    first_day_prev = (start_of_current_month - timedelta(days=1)).replace(day=1)
    end_of_prev_month = start_of_current_month - timedelta(seconds=1)

    try:
        # Total Sales (lifetime)
        total_sales = VoucherEntry.objects.filter(
            voucher__company=company,
            voucher__voucher_type=VoucherType.SALES,
            entry_type=EntryType.CREDIT
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Current Month Sales
        current_month_sales = VoucherEntry.objects.filter(
            voucher__company=company,
            voucher__voucher_type=VoucherType.SALES,
            voucher__date__gte=start_of_current_month.date(),
            entry_type=EntryType.CREDIT
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Previous Month Sales
        prev_month_sales = VoucherEntry.objects.filter(
            voucher__company=company,
            voucher__voucher_type=VoucherType.SALES,
            voucher__date__range=[first_day_prev.date(), end_of_prev_month.date()],
            entry_type=EntryType.CREDIT
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Growth Rate
        growth_percentage = 0.00
        if prev_month_sales > 0:
            growth_percentage = float(((current_month_sales - prev_month_sales) / prev_month_sales) * 100)

        # Weekly sales (last 4 weeks)
        weekly_sales = []
        for i in range(4):
            end_date = now - timedelta(weeks=i)
            start_date = end_date - timedelta(days=7)
            sum_week = VoucherEntry.objects.filter(
                voucher__company=company,
                voucher__voucher_type=VoucherType.SALES,
                voucher__date__range=[start_date.date(), end_date.date()],
                entry_type=EntryType.CREDIT
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            weekly_sales.append({
                'week': f"Week {4-i}",
                'amount': float(sum_week)
            })
        weekly_sales.reverse()

        # Monthly chart data (last 6 months)
        monthly_trends = []
        for i in range(5, -1, -1):
            target_date = now - timedelta(days=i*30)
            month_start = target_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year+1, month=1) - timedelta(seconds=1)
            else:
                month_end = month_start.replace(month=month_start.month+1) - timedelta(seconds=1)
            
            sum_month = VoucherEntry.objects.filter(
                voucher__company=company,
                voucher__voucher_type=VoucherType.SALES,
                voucher__date__range=[month_start.date(), month_end.date()],
                entry_type=EntryType.CREDIT
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            monthly_trends.append({
                'month': month_start.strftime('%b'),
                'amount': float(sum_month)
            })

        return {
            'total_sales': float(total_sales),
            'current_month_sales': float(current_month_sales),
            'prev_month_sales': float(prev_month_sales),
            'growth_percentage': round(growth_percentage, 2),
            'weekly_sales': weekly_sales,
            'monthly_trends': monthly_trends
        }
    except Exception as e:
        logger.error(f"Error computing revenue metrics: {e}", exc_info=True)
        return {'total_sales': 0.00, 'growth_percentage': 0.00, 'weekly_sales': [], 'monthly_trends': []}


def calculate_expense_metrics(company) -> dict:
    """Computes total expenses, top categories, expense ratio, and monthly trends."""
    now = timezone.now()
    start_of_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    try:
        # Total indirect/direct expenses (Debit entries on expense ledgers)
        expense_ledgers = Ledger.objects.filter(company=company, group__name__icontains='Expenses')
        
        total_expenses = VoucherEntry.objects.filter(
            voucher__company=company,
            ledger__in=expense_ledgers,
            entry_type=EntryType.DEBIT
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Current Month Expenses
        current_month_expenses = VoucherEntry.objects.filter(
            voucher__company=company,
            ledger__in=expense_ledgers,
            voucher__date__gte=start_of_current_month.date(),
            entry_type=EntryType.DEBIT
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Top 5 Expense Categories/Ledgers
        top_ledgers = VoucherEntry.objects.filter(
            voucher__company=company,
            ledger__in=expense_ledgers,
            entry_type=EntryType.DEBIT
        ).values('ledger__name').annotate(total=Sum('amount')).order_by('-total')[:5]

        top_categories = []
        for tl in top_ledgers:
            top_categories.append({
                'category': tl['ledger__name'],
                'amount': float(tl['total'] or 0)
            })

        # Expense ratio (expenses / sales)
        sales_metrics = calculate_revenue_metrics(company)
        total_sales = sales_metrics.get('total_sales', 0.00)
        expense_ratio = 0.00
        if total_sales > 0:
            expense_ratio = (float(total_expenses) / total_sales) * 100

        # Monthly expense trends (last 6 months)
        monthly_expense_trends = []
        for i in range(5, -1, -1):
            target_date = now - timedelta(days=i*30)
            month_start = target_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year+1, month=1) - timedelta(seconds=1)
            else:
                month_end = month_start.replace(month=month_start.month+1) - timedelta(seconds=1)
            
            sum_month = VoucherEntry.objects.filter(
                voucher__company=company,
                ledger__in=expense_ledgers,
                voucher__date__range=[month_start.date(), month_end.date()],
                entry_type=EntryType.DEBIT
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            monthly_expense_trends.append({
                'month': month_start.strftime('%b'),
                'amount': float(sum_month)
            })

        return {
            'total_expenses': float(total_expenses),
            'current_month_expenses': float(current_month_expenses),
            'top_categories': top_categories,
            'expense_ratio': round(expense_ratio, 2),
            'monthly_expense_trends': monthly_expense_trends
        }
    except Exception as e:
        logger.error(f"Error computing expense metrics: {e}", exc_info=True)
        return {'total_expenses': 0.00, 'top_categories': [], 'expense_ratio': 0.00, 'monthly_expense_trends': []}


def calculate_cashflow_metrics(company) -> dict:
    """Computes net inflow vs outflow and outstanding client/supplier balances."""
    try:
        # Cash/Bank Ledgers
        cash_bank_ledgers = Ledger.objects.filter(company=company, group__name__icontains='Cash') | \
                            Ledger.objects.filter(company=company, group__name__icontains='Bank')
        
        # Inflows (DR entries in Cash/Bank)
        inflows = VoucherEntry.objects.filter(
            voucher__company=company,
            ledger__in=cash_bank_ledgers,
            entry_type=EntryType.DEBIT
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Outflows (CR entries in Cash/Bank)
        outflows = VoucherEntry.objects.filter(
            voucher__company=company,
            ledger__in=cash_bank_ledgers,
            entry_type=EntryType.CREDIT
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Sundry Debtors Outstandings (Pending Receivables)
        debtors = Ledger.objects.filter(company=company, group__name__icontains='Debtors')
        outstanding_receivables = VoucherEntry.objects.filter(
            voucher__company=company,
            ledger__in=debtors,
            entry_type=EntryType.DEBIT # Debtors debit increases outstanding
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        received_from_debtors = VoucherEntry.objects.filter(
            voucher__company=company,
            ledger__in=debtors,
            entry_type=EntryType.CREDIT # Debtors credit decreases outstanding
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        net_receivables = outstanding_receivables - received_from_debtors

        # Sundry Creditors Outstandings (Pending Payables)
        creditors = Ledger.objects.filter(company=company, group__name__icontains='Creditors')
        outstanding_payables = VoucherEntry.objects.filter(
            voucher__company=company,
            ledger__in=creditors,
            entry_type=EntryType.CREDIT # Creditors credit increases outstanding
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        paid_to_creditors = VoucherEntry.objects.filter(
            voucher__company=company,
            ledger__in=creditors,
            entry_type=EntryType.DEBIT # Creditors debit decreases outstanding
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        net_payables = outstanding_payables - paid_to_creditors

        return {
            'inflow': float(inflows),
            'outflow': float(outflows),
            'net_cashflow': float(inflows - outflows),
            'receivables': float(max(Decimal('0.00'), net_receivables)),
            'payables': float(max(Decimal('0.00'), net_payables))
        }
    except Exception as e:
        logger.error(f"Error computing cashflow metrics: {e}", exc_info=True)
        return {'inflow': 0.00, 'outflow': 0.00, 'net_cashflow': 0.00, 'receivables': 0.00, 'payables': 0.00}


def calculate_gst_metrics(company) -> dict:
    """Computes CGST, SGST, IGST totals and dynamic estimates."""
    try:
        # Duties & Taxes Ledgers
        tax_ledgers = Ledger.objects.filter(company=company, group__name__icontains='Duties')
        
        # CGST sum (vouchers debit is paid tax, credit is output liability)
        cgst_ledgers = tax_ledgers.filter(name__icontains='CGST')
        cgst_dr = VoucherEntry.objects.filter(voucher__company=company, ledger__in=cgst_ledgers, entry_type=EntryType.DEBIT).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
        cgst_cr = VoucherEntry.objects.filter(voucher__company=company, ledger__in=cgst_ledgers, entry_type=EntryType.CREDIT).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
        
        # SGST sum
        sgst_ledgers = tax_ledgers.filter(name__icontains='SGST')
        sgst_dr = VoucherEntry.objects.filter(voucher__company=company, ledger__in=sgst_ledgers, entry_type=EntryType.DEBIT).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
        sgst_cr = VoucherEntry.objects.filter(voucher__company=company, ledger__in=sgst_ledgers, entry_type=EntryType.CREDIT).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

        # IGST sum
        igst_ledgers = tax_ledgers.filter(name__icontains='IGST')
        igst_dr = VoucherEntry.objects.filter(voucher__company=company, ledger__in=igst_ledgers, entry_type=EntryType.DEBIT).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
        igst_cr = VoucherEntry.objects.filter(voucher__company=company, ledger__in=igst_ledgers, entry_type=EntryType.CREDIT).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

        # Output liabilities are Credits (vouchers sales output GST), Input credits are Debits
        net_cgst = cgst_cr - cgst_dr
        net_sgst = sgst_cr - sgst_dr
        net_igst = igst_cr - igst_dr
        
        net_liability = net_cgst + net_sgst + net_igst

        return {
            'cgst_paid': float(cgst_dr),
            'cgst_liability': float(cgst_cr),
            'sgst_paid': float(sgst_dr),
            'sgst_liability': float(sgst_cr),
            'igst_paid': float(igst_dr),
            'igst_liability': float(igst_cr),
            'net_gst_liability': float(net_liability)
        }
    except Exception as e:
        logger.error(f"Error computing GST metrics: {e}", exc_info=True)
        return {'cgst_paid': 0, 'sgst_paid': 0, 'igst_paid': 0, 'net_gst_liability': 0}


def calculate_approval_metrics(company) -> dict:
    """Aggregates voucher approval parameters."""
    try:
        vouchers = Voucher.objects.filter(company=company)
        
        pending_count = vouchers.filter(status=VoucherStatus.PENDING).count()
        approved_count = vouchers.filter(status=VoucherStatus.APPROVED).count()
        rejected_count = vouchers.filter(status=VoucherStatus.REJECTED).count()
        
        return {
            'pending_approvals': pending_count,
            'approved_vouchers': approved_count,
            'rejected_vouchers': rejected_count,
            'total_vouchers': vouchers.count()
        }
    except Exception as e:
        logger.error(f"Error computing approval metrics: {e}", exc_info=True)
        return {'pending_approvals': 0, 'approved_vouchers': 0, 'rejected_vouchers': 0, 'total_vouchers': 0}


def calculate_inventory_metrics(company) -> dict:
    """Determines low stock items and fast-moving products."""
    try:
        stock_items = StockItem.objects.filter(company=company)
        
        # Low Stock (threshold < 10 units)
        low_stock_items = []
        for item in stock_items:
            # Check quantity (from custom db calculation or balance)
            qty = float(getattr(item, 'opening_balance_qty', 0) or 0)
            if qty < 10:
                low_stock_items.append({
                    'item_name': item.name,
                    'stock': qty
                })

        # Fast moving stock items (most frequent in voucher entry lines)
        frequent_items = VoucherEntry.objects.filter(
            voucher__company=company,
            stock_item__isnull=False
        ).values('stock_item__name').annotate(frequency=Sum('quantity')).order_by('-frequency')[:3]

        fast_moving = []
        for fi in frequent_items:
            fast_moving.append({
                'item_name': fi['stock_item__name'],
                'volume': float(fi['frequency'] or 0)
            })

        return {
            'low_stock': low_stock_items,
            'fast_moving': fast_moving
        }
    except Exception as e:
        logger.error(f"Error computing inventory metrics: {e}", exc_info=True)
        return {'low_stock': [], 'fast_moving': []}


def calculate_forecasting_metrics(company) -> dict:
    """Calculates a simple moving average trend prediction for the next month sales/expenses."""
    try:
        sales = calculate_revenue_metrics(company)
        expenses = calculate_expense_metrics(company)

        monthly_sales = [x['amount'] for x in sales.get('monthly_trends', [])]
        monthly_exp = [x['amount'] for x in expenses.get('monthly_expense_trends', [])]

        # Simple 3-month moving average prediction
        projected_sales = sum(monthly_sales[-3:]) / 3 if len(monthly_sales) >= 3 else sum(monthly_sales) / len(monthly_sales) if monthly_sales else 0.00
        projected_expenses = sum(monthly_exp[-3:]) / 3 if len(monthly_exp) >= 3 else sum(monthly_exp) / len(monthly_exp) if monthly_exp else 0.00

        return {
            'projected_sales': round(projected_sales, 2),
            'projected_expenses': round(projected_expenses, 2)
        }
    except Exception as e:
        logger.error(f"Error computing forecasting: {e}", exc_info=True)
        return {'projected_sales': 0.00, 'projected_expenses': 0.00}


def calculate_financial_health_score(company, metrics=None) -> dict:
    """Calculates overall corporate health rating (0 - 100)."""
    score = 100
    deductions = []

    try:
        if not metrics:
            metrics = {
                'sales': calculate_revenue_metrics(company),
                'expenses': calculate_expense_metrics(company),
                'cashflow': calculate_cashflow_metrics(company),
                'approvals': calculate_approval_metrics(company)
            }

        # 1. Expense-to-sales ratio deduction
        ratio = metrics['expenses'].get('expense_ratio', 0)
        if ratio > 80:
            score -= 15
            deductions.append("High operational expenses compared to top-line sales.")
        elif ratio > 60:
            score -= 8
            deductions.append("Moderate to high operating expense margins.")

        # 2. Liquidity / Cashflow checks
        net_cash = metrics['cashflow'].get('net_cashflow', 0)
        if net_cash < 0:
            score -= 15
            deductions.append("Monthly cash balance is negative (Outflows exceed Inflows).")

        # 3. Pending approvals counts
        pending = metrics['approvals'].get('pending_approvals', 0)
        if pending > 10:
            score -= 10
            deductions.append("High volume of pending approvals stalling voucher accounting.")
        elif pending > 5:
            score -= 5
            deductions.append("Voucher approvals queue is moderate.")

        # 4. Outstandings checks
        receivables = metrics['cashflow'].get('receivables', 0)
        payables = metrics['cashflow'].get('payables', 0)
        if payables > receivables * 1.5 and payables > 10000:
            score -= 10
            deductions.append("Supplier payables significantly outpace client receivables.")

        score = max(20, score) # minimum threshold
        
        status = "EXCELLENT"
        if score < 50:
            status = "AT RISK"
        elif score < 80:
            status = "STABLE"

        return {
            'score': score,
            'status': status,
            'deductions': deductions
        }
    except Exception as e:
        logger.error(f"Error calculating health score: {e}", exc_info=True)
        return {'score': 80, 'status': 'STABLE', 'deductions': []}
