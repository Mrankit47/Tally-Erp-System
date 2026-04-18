from django.apps import AppConfig


class VoucherConfig(AppConfig):
    """Transaction voucher management (Journal, Payment, Receipt, etc.)."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'voucher'
    verbose_name = 'Vouchers'
