from django.contrib import admin
from .models import LedgerGroup, Ledger, Currency, Budget, Scenario

@admin.register(LedgerGroup)
class LedgerGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'parent')
    list_filter = ('company',)
    search_fields = ('name',)

@admin.register(Ledger)
class LedgerAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'group', 'opening_balance', 'credit_limit')
    list_filter = ('company', 'group')
    search_fields = ('name', 'alias')

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('formal_name', 'symbol', 'exchange_rate', 'company')
    list_filter = ('company',)
    search_fields = ('formal_name', 'symbol')

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount', 'from_date', 'to_date', 'company')
    list_filter = ('company',)
    search_fields = ('name',)

@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'include_actuals', 'exclude_forex_gains')
    list_filter = ('company', 'include_actuals')
    search_fields = ('name',)
