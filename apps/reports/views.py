"""
Reports views.

Thin views that delegate to the service layer.
Architecture: Views → Services → Models
"""
import csv
import json
from dateutil.relativedelta import relativedelta
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from core.permissions import role_required
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from core.templatetags.currency_tags import indian_currency
from .services import generate_trial_balance, generate_profit_and_loss, get_top_expenses
from company.models import Company
from voucher.models import VoucherEntry, EntryType, VoucherType


@login_required
@role_required(['Admin', 'Accountant'])
def trial_balance_view(request):
    """Renders the HTML Trial Balance Report."""
    company = Company.objects.first()
    tb_report = generate_trial_balance(company)
    
    # Check if there's any data
    is_empty = all(len(ledgers) == 0 for ledgers in tb_report['data'].values())
    
    context = {
        'active_page': 'trial_balance',
        'tb': tb_report,
        'company': company,
        'is_empty': is_empty
    }
    return render(request, 'reports/trial_balance.html', context)


@login_required
@role_required(['Admin', 'Accountant'])
def export_trial_balance_csv(request):
    """Exports the Trial Balance to CSV."""
    company = Company.objects.first()
    tb_report = generate_trial_balance(company)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Trial_Balance.csv"'
    response.write('\ufeff'.encode('utf8')) # BOM for Excel
    
    writer = csv.writer(response)
    writer.writerow([f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"])
    writer.writerow([f"Company: {company.name if company else 'Unknown'}"])
    writer.writerow([]) # Empty separator
    
    writer.writerow(['Category', 'Ledger Name', 'Debit Amount', 'Credit Amount'])
    
    for category in ['Assets', 'Liabilities', 'Income', 'Expenses']:
        for ledger in tb_report['data'][category]:
            writer.writerow([
                category,
                ledger['name'],
                indian_currency(ledger['debit']) if ledger['debit'] else '',
                indian_currency(ledger['credit']) if ledger['credit'] else ''
            ])
            
    writer.writerow([])
    writer.writerow(['', 'TOTAL', indian_currency(tb_report['total_debit']), indian_currency(tb_report['total_credit'])])
    
    if not tb_report['is_balanced']:
        writer.writerow(['', 'DIFFERENCE', '', indian_currency(tb_report['difference'])])
    
    return response


@login_required
@role_required(['Admin', 'Accountant'])
def profit_loss_view(request):
    """Renders the HTML Profit & Loss Statement with Visual Analytics."""
    company = Company.objects.first()
    pl_report = generate_profit_and_loss(company)
    top_expenses = get_top_expenses(company, limit=5)
    
    is_empty = len(pl_report['incomes']) == 0 and len(pl_report['expenses']) == 0
    
    # Generate Chart Data (Last 12 months)
    today = timezone.now().date()
    start_date = (today.replace(day=1) - relativedelta(months=11))
    
    def get_monthly_sums(voucher_type):
        qs = VoucherEntry.objects.filter(
            ledger__company=company,
            voucher__voucher_type=voucher_type,
            entry_type=EntryType.DEBIT,
            voucher__date__gte=start_date
        ).annotate(
            month=TruncMonth('voucher__date')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')
        
        return {item['month'].strftime('%b %Y'): float(item['total']) for item in qs if item['month']}

    sales_trend = get_monthly_sums(VoucherType.SALES)
    expenses_trend = get_monthly_sums(VoucherType.PAYMENT) # Proxy for expenses trend
    
    # Generate continuous last 12 months labels ensures no blanks
    months = []
    for i in range(11, -1, -1):
        d = today - relativedelta(months=i)
        months.append(d.strftime('%b %Y'))
        
    chart_data = {
        'labels': months,
        'income': [sales_trend.get(m, 0) for m in months],
        'expenses': [expenses_trend.get(m, 0) for m in months],
        'profit': [(sales_trend.get(m, 0) - expenses_trend.get(m, 0)) for m in months]
    }
    
    context = {
        'active_page': 'profit_loss',
        'pl': pl_report,
        'top_expenses': top_expenses,
        'company': company,
        'is_empty': is_empty,
        'chart_data_json': json.dumps(chart_data)
    }
    return render(request, 'reports/profit_loss.html', context)


@login_required
@role_required(['Admin', 'Accountant'])
def export_profit_loss_csv(request):
    """Exports the Profit & Loss statement to CSV."""
    company = Company.objects.first()
    pl_report = generate_profit_and_loss(company)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Profit_And_Loss.csv"'
    response.write('\ufeff'.encode('utf8'))
    
    writer = csv.writer(response)
    writer.writerow([f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"])
    writer.writerow([f"Company: {company.name if company else 'Unknown'}"])
    writer.writerow([])
    
    writer.writerow(['Type', 'Ledger Name', 'Amount'])
    
    writer.writerow(['INCOME', '', ''])
    for ledger in pl_report['incomes']:
        amount = ledger['credit'] - ledger['debit']
        writer.writerow(['', ledger['name'], indian_currency(amount)])
    writer.writerow(['', 'Total Income', indian_currency(pl_report['total_income'])])
    
    writer.writerow([])
    writer.writerow(['EXPENSES', '', ''])
    for ledger in pl_report['expenses']:
        amount = ledger['debit'] - ledger['credit']
        writer.writerow(['', ledger['name'], indian_currency(amount)])
    writer.writerow(['', 'Total Expenses', indian_currency(pl_report['total_expenses'])])
    
    writer.writerow([])
    status = "Net Profit" if pl_report['is_profit'] else "Net Loss"
    writer.writerow(['SUMMARY', status, indian_currency(pl_report['net_result'])])
    
    return response
