from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Invoice
from .services.pdf_service import generate_invoice_pdf


@login_required
def download_invoice_pdf(request, voucher_id):
    """
    View to fetch a document (Invoice or Voucher) and return it as a PDF download.
    Enforces multi-tenancy by filtering via the user's active company.
    """
    from voucher.models import Voucher, VoucherType
    from .services.invoice_service import generate_invoice_from_voucher
    
    active_company = getattr(request, 'active_company', None)
    
    # 1. Fetch the Voucher first to determine type
    voucher = get_object_or_404(Voucher, pk=voucher_id, company=active_company)
    
    # 2. Validation: Block download if voucher is not approved
    if hasattr(voucher, 'status') and voucher.status != "APPROVED":
        return HttpResponse(
            f"Document Access Denied: Voucher {voucher.number} is currently in '{voucher.status}' status. "
            "Please approve the voucher before downloading the PDF.", 
            status=403
        )
    
    try:
        # 2. Handle Sales (Invoice Flow)
        if voucher.voucher_type == VoucherType.SALES:
            # Check if invoice already exists
            invoice = Invoice.objects.filter(voucher=voucher).first()
            if not invoice:
                # Generate invoice on-the-fly if missing
                invoice = generate_invoice_from_voucher(voucher)
            
            pdf_content = generate_invoice_pdf(invoice)
            filename = f"Invoice_{invoice.invoice_number}.pdf"
        
        # 3. Handle Other Types (Generic Voucher Flow)
        else:
            # For now, we can use a simpler version or reuse the PDF service
            # We'll adapt generate_invoice_pdf to handle raw vouchers too
            pdf_content = generate_invoice_pdf(voucher) 
            filename = f"{voucher.voucher_type}_{voucher.number}.pdf"

        # 4. Return Response
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"PDF Generation Error: {str(e)}")
        return HttpResponse(f"Error generating document: {str(e)}", status=500)
