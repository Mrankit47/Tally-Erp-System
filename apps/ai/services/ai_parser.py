import logging
from .router import ai_router
from .utils import extract_json_from_text

logger = logging.getLogger('apps.ai')

def parse_ocr_text_to_json(ocr_text: str, company_name: str = "", company_gstin: str = "") -> dict:
    """
    Calls AI Router for the 'invoice' task using Gemini.
    Converts raw OCR text into structured financial document data (Sales, Purchase, Receipt, Payment).
    """
    # Enforce safe defaults if OCR text is empty
    if not ocr_text.strip():
        return {
            "document_type": "Purchase",
            "vendor_name": "",
            "gst_number": "",
            "invoice_number": "",
            "invoice_date": "",
            "subtotal": 0.00,
            "cgst": 0.00,
            "sgst": 0.00,
            "igst": 0.00,
            "total_amount": 0.00,
            "items": [],
            "confidence_score": 0
        }

    try:
        system_prompt = f"""You are an expert AI accounting agent specialized in parsing raw OCR text from Indian GST financial documents into structured data.

Your goal is to parse the raw text and extract EXACTLY the specified fields. Follow these rules:
1. Normalize dates to standard ISO format 'YYYY-MM-DD'. If the date is missing or illegible, output "".
2. Numeric values must be parsed as positive floats/decimals. Do not include currency symbols or commas.
3. If tax values are not explicitly separated into CGST/SGST, but rather CGST and SGST are applied, split them.
4. If IGST is applied, set igst, and set cgst/sgst to 0.00.
5. In the 'items' list, extract each stock item with its name, quantity, rate, amount, and HSN code. If HSN is missing, output "". If it is a Receipt or Payment advice, the items list should be empty.
6. Assign an overall integer 'confidence_score' between 0 and 100 representing how complete the extracted data feels.
7. CRITICAL: Classify the document_type as exactly one of: "Sales", "Purchase", "Receipt", or "Payment".
   - The active ERP company processing this document is: Name="{company_name}", GSTIN="{company_gstin}".
   - If the active company is the seller/biller, it is a "Sales" invoice.
   - If the active company is the buyer/recipient, it is a "Purchase" invoice.
   - If the document is an incoming payment receipt (money received by the active company), it is a "Receipt".
   - If the document is an outgoing payment advice (money paid by the active company), it is a "Payment".
   - If the active company context is empty, default to "Purchase".

You MUST return your output in the following STRICT json layout ONLY (no markdown backticks):
{{
  "document_type": "Sales",
  "vendor_name": "Name of the opposite party (customer/supplier/payer)",
  "gst_number": "Indian GSTIN format of the opposite party (15 characters), empty if not found",
  "invoice_number": "Invoice number or bill reference, empty if not found",
  "invoice_date": "YYYY-MM-DD",
  "subtotal": 0.00,
  "cgst": 0.00,
  "sgst": 0.00,
  "igst": 0.00,
  "total_amount": 0.00,
  "items": [
    {{
      "item_name": "Full name or description of the stock item/service",
      "quantity": 1.0,
      "rate": 0.00,
      "amount": 0.00,
      "hsn_code": "HSN/SAC digits, empty if not found"
    }}
  ],
  "confidence_score": 90
}}
"""
        
        user_prompt = f"RAW OCR TEXT:\n\n{ocr_text}"
        
        logger.debug("Routing parse request to AI router for 'invoice' task.")
        
        # Route to AI via Gemini (with Groq fallback)
        response_content = ai_router.route_request(
            task="invoice",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1
        )

        parsed_data = extract_json_from_text(response_content)
        
        logger.info(f"AI parse completed with confidence: {parsed_data.get('confidence_score', 0)}")
        return parsed_data

    except Exception as e:
        logger.error(f"Error in parse_ocr_text_to_json: {e}", exc_info=True)
        raise ValueError(f"{str(e)}")
