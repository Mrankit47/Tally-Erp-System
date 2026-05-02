import logging
from decimal import Decimal
from django.db.models import Sum
from reports.services import generate_profit_and_loss
from voucher.models import Voucher, VoucherEntry, EntryType, VoucherType
from invoicing.models import Invoice

logger = logging.getLogger('apps.ai')

def get_total_sales(company) -> str:
    """Fetch total sales for the given company."""
    try:
        # Sum of credit entries in Sales vouchers (sales is credit)
        total_sales = VoucherEntry.objects.filter(
            voucher__company=company,
            voucher__voucher_type=VoucherType.SALES,
            entry_type=EntryType.CREDIT
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        return f"Total Sales: ₹{total_sales}"
    except Exception as e:
        logger.error(f"Error fetching total sales: {e}")
        return "Total Sales: [Error fetching data]"

def get_total_expenses(company) -> str:
    """Fetch total expenses for the given company from P&L."""
    try:
        pl_data = generate_profit_and_loss(company)
        return f"Total Expenses: ₹{pl_data.get('total_expenses', Decimal('0.00'))}"
    except Exception as e:
        logger.error(f"Error fetching total expenses: {e}")
        return "Total Expenses: [Error fetching data]"

def get_profit(company) -> str:
    """Fetch net profit for the given company from P&L."""
    try:
        pl_data = generate_profit_and_loss(company)
        net_result = pl_data.get('net_result', Decimal('0.00'))
        is_profit = pl_data.get('is_profit', True)
        
        result_type = "Net Profit" if is_profit else "Net Loss"
        return f"{result_type}: ₹{net_result}"
    except Exception as e:
        logger.error(f"Error fetching profit: {e}")
        return "Net Profit: [Error fetching data]"

def get_recent_invoices(company, limit=5) -> str:
    """Fetch recent invoices for the given company."""
    try:
        invoices = Invoice.objects.filter(company=company).order_by('-invoice_date', '-invoice_number')[:limit]
        
        if not invoices:
            return "Recent Invoices: No invoices found."
            
        result = "Recent Invoices:\n"
        for inv in invoices:
            result += f"- {inv.invoice_number} ({inv.invoice_date}): {inv.customer_name} - ₹{inv.grand_total}\n"
            
        return result
    except Exception as e:
        logger.error(f"Error fetching recent invoices: {e}")
        return "Recent Invoices: [Error fetching data]"
