"""
Reports Services.

Handles the heavy lifting of financial reporting calculations and Ledger classification.
Ensures zero N+1 queries through bulk aggregations and memory caching.
"""
from decimal import Decimal
from django.db.models import Sum
from ledger.models import Ledger, LedgerGroup
from voucher.models import VoucherEntry, EntryType

def get_ledger_category(root_group_name):
    """
    Categorizes the Tally top-level group into Asset, Liability, Income, or Expense.
    """
    root = root_group_name.lower()
    if 'income' in root or 'sales' in root:
        return 'Income'
    elif 'expense' in root or 'purchase' in root:
        return 'Expenses'
    elif 'liabilit' in root or 'capital' in root or 'loan' in root or 'suspense' in root or 'branch' in root:
        return 'Liabilities'
    else:
        # Fallback to Assets (Current Assets, Fixed Assets, Investments etc.)
        return 'Assets'

def generate_trial_balance(company):
    """
    Generates a difference-validated Trial Balance using bulk memory aggregation.
    """
    ledgers = Ledger.objects.filter(company=company).select_related('group')
    groups = list(LedgerGroup.objects.filter(company=company))
    group_map = {g.id: g for g in groups}

    # Memoize root group fetch to prevent db round-trips
    def get_root_group_mem(group_id):
        current = group_map.get(group_id)
        while current and current.parent_id:
            current = group_map.get(current.parent_id)
        return current

    # Bulk aggregate all voucher entries to prevent N+1 per ledger
    entries_agg = VoucherEntry.objects.filter(
        ledger__company=company
    ).values('ledger_id', 'entry_type').annotate(total=Sum('amount'))

    ledger_totals = {}
    for agg in entries_agg:
        l_id = agg['ledger_id']
        if l_id not in ledger_totals:
            ledger_totals[l_id] = {'debit': Decimal('0.00'), 'credit': Decimal('0.00')}
        
        if agg['entry_type'] == EntryType.DEBIT:
            ledger_totals[l_id]['debit'] = agg['total']
        elif agg['entry_type'] == EntryType.CREDIT:
            ledger_totals[l_id]['credit'] = agg['total']

    tb_data = {
        'Assets': [],
        'Liabilities': [],
        'Income': [],
        'Expenses': []
    }
    
    total_debit = Decimal('0.00')
    total_credit = Decimal('0.00')

    for ledger in ledgers:
        root_group = get_root_group_mem(ledger.group_id)
        root_name = root_group.name if root_group else "Unknown"
        category = get_ledger_category(root_name)
        
        # Calculate dynamic balance manually from our agg cache
        totals = ledger_totals.get(ledger.id, {'debit': Decimal('0.00'), 'credit': Decimal('0.00')})
        dr_sum = totals['debit']
        cr_sum = totals['credit']
        
        balance = ledger.opening_balance + dr_sum - cr_sum
        
        if balance > 0:
            dr = balance
            cr = Decimal('0.00')
            total_debit += dr
        elif balance < 0:
            dr = Decimal('0.00')
            cr = abs(balance)
            total_credit += cr
        else:
            dr = Decimal('0.00')
            cr = Decimal('0.00')
            
        tb_data[category].append({
            'name': ledger.name,
            'debit': dr,
            'credit': cr,
            'balance': balance,
            'category': category
        })
        
    difference = total_debit - total_credit
    is_balanced = (difference == 0)
    
    # Sort children alphabetically
    for key in tb_data:
        tb_data[key].sort(key=lambda x: x['name'])
    
    return {
        'data': tb_data,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'difference': abs(difference),
        'is_balanced': is_balanced
    }


def generate_profit_and_loss(company):
    """
    Generates P&L statement from the Trial Balance data.
    """
    tb = generate_trial_balance(company)
    
    incomes = tb['data']['Income']
    expenses = tb['data']['Expenses']
    
    # In trial balance: 
    # Credit means negative balance. Since Income typically has Credit balance, we sum (Cr - Dr).
    total_income = sum(item['credit'] - item['debit'] for item in incomes)
    
    # Expense typically has Debit balance, so we sum (Dr - Cr).
    total_expenses = sum(item['debit'] - item['credit'] for item in expenses)
    
    net_result = total_income - total_expenses
    is_profit = (net_result >= 0)
    
    return {
        'incomes': incomes,
        'expenses': expenses,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'net_result': abs(net_result),
        'is_profit': is_profit,
        'raw_net_result': net_result
    }


def get_top_expenses(company, limit=5):
    """
    Fetches the highest grossing Expense accounts by analyzing total debits.
    """
    ledgers = Ledger.objects.filter(company=company).select_related('group')
    groups = list(LedgerGroup.objects.filter(company=company))
    group_map = {g.id: g for g in groups}

    def get_root_group_mem(group_id):
        current = group_map.get(group_id)
        while current and current.parent_id:
            current = group_map.get(current.parent_id)
        return current

    # We only care about debits for expenses
    entries_agg = VoucherEntry.objects.filter(
        ledger__company=company,
        entry_type=EntryType.DEBIT
    ).values('ledger_id').annotate(total=Sum('amount'))
    
    debit_totals = {agg['ledger_id']: agg['total'] for agg in entries_agg}

    expenses_list = []
    for ledger in ledgers:
        root_group = get_root_group_mem(ledger.group_id)
        root_name = root_group.name if root_group else "Unknown"
        
        if get_ledger_category(root_name) == 'Expenses':
            dr_total = debit_totals.get(ledger.id, Decimal('0.00'))
            if dr_total > 0:
                expenses_list.append({
                    'name': ledger.name, 
                    'amount': dr_total
                })
            
    # Sort descending
    expenses_list.sort(key=lambda x: x['amount'], reverse=True)
    
    # Pre-calculate percentage for the UI Chart directly
    if expenses_list:
        max_amount = expenses_list[0]['amount']
        for expense in expenses_list:
            expense['percent'] = int((expense['amount'] / max_amount) * 100) if max_amount > 0 else 0

    return expenses_list[:limit]
