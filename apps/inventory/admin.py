from django.contrib import admin
from .models import StockGroup, StockCategory, StockItem, Unit, Location, StockTransaction

@admin.register(StockGroup)
class StockGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'parent', 'sync_status')
    list_filter = ('company', 'sync_status')
    search_fields = ('name',)

@admin.register(StockCategory)
class StockCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'parent')
    list_filter = ('company',)
    search_fields = ('name',)

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('formal_name', 'symbol', 'decimal_places', 'company')
    list_filter = ('company',)
    search_fields = ('formal_name', 'symbol')

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'parent')
    list_filter = ('company',)
    search_fields = ('name',)

@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'group', 'category', 'unit', 'opening_stock_qty')
    list_filter = ('company', 'group', 'category', 'sync_status')
    search_fields = ('name',)

@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('stock_item', 'transaction_type', 'quantity', 'rate', 'location', 'company')
    list_filter = ('company', 'transaction_type')
    search_fields = ('stock_item__name',)
