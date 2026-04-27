import io
from django.template.loader import render_to_string
from django.conf import settings

def generate_invoice_pdf(obj):
    """
    Renders an Invoice or Voucher as a PDF buffer using xhtml2pdf (Pisa).
    'obj' can be an Invoice instance or a Voucher instance.
    This library is pure-Python and works great on Windows.
    """
    try:
        from xhtml2pdf import pisa
    except ImportError:
        raise ImportError("xhtml2pdf is required. Run 'pip install xhtml2pdf'.")

    # 1. Determine Type and prepare context
    from invoicing.models import Invoice
    from voucher.models import Voucher
    
    if isinstance(obj, Invoice):
        invoice = obj
        voucher = obj.voucher
        title = "TAX INVOICE"
    else:
        invoice = None
        voucher = obj
        title = f"{voucher.get_voucher_type_display().upper()} VOUCHER"

    context = {
        'title': title,
        'invoice': invoice,
        'voucher': voucher,
        'company': voucher.company,
        'gst_profile': voucher.company.gstprofile_records.filter(is_active=True).first() or \
                       voucher.company.gstprofile_records.first(),
        'entries': voucher.entries.all(),
        'tax_details': voucher.tax_details.first(),
    }

    # 2. Render HTML to String
    html_string = render_to_string('invoicing/invoice_pdf.html', context)

    # 3. Convert HTML to PDF using pisa
    result = io.BytesIO()
    pisa_status = pisa.CreatePDF(
        io.BytesIO(html_string.encode("UTF-8")),
        dest=result,
        encoding='UTF-8'
    )

    if pisa_status.err:
        raise Exception(f"PDF generation failed: {pisa_status.err}")

    return result.getvalue()
