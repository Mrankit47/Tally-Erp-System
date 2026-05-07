import os
import json
import logging
from groq import Groq

logger = logging.getLogger('apps.ai')

def parse_ocr_text_to_json(ocr_text: str) -> dict:
    """
    Calls Groq SDK using llama-3.1-8b-instant with strict JSON formatting.
    Converts raw invoice OCR text into structured financial invoice data.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.error("Missing GROQ_API_KEY in environment.")
        raise ValueError("AI parser is not configured: GROQ_API_KEY is missing.")

    # Enforce safe defaults if OCR text is empty
    if not ocr_text.strip():
        return {
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
        client = Groq(api_key=api_key)
        
        system_prompt = """You are an expert AI accounting agent specialized in parsing raw OCR text from Indian GST financial invoices into structured data.

Your goal is to parse the raw text and extract EXACTLY the specified fields. Follow these rules:
1. Normalize dates to standard ISO format 'YYYY-MM-DD'. If the date is missing or illegible, output "".
2. Numeric values must be parsed as positive floats/decimals. Do not include currency symbols or commas.
3. If tax values are not explicitly separated into CGST/SGST, but rather CGST and SGST are applied, split them.
4. If IGST is applied, set igst, and set cgst/sgst to 0.00.
5. In the 'items' list, extract each stock item with its name, quantity, rate, amount, and HSN code. If HSN is missing, output "".
6. Assign an overall integer 'confidence_score' between 0 and 100 representing how complete the extracted data feels.

You MUST return your output in the following STRICT JSON layout:
{
  "vendor_name": "Name of the supplier or company billing",
  "gst_number": "Indian GSTIN format of the vendor (15 characters), empty if not found",
  "invoice_number": "Invoice number or bill reference, empty if not found",
  "invoice_date": "YYYY-MM-DD",
  "subtotal": 0.00,
  "cgst": 0.00,
  "sgst": 0.00,
  "igst": 0.00,
  "total_amount": 0.00,
  "items": [
    {
      "item_name": "Full name or description of the stock item/service",
      "quantity": 1.0,
      "rate": 0.00,
      "amount": 0.00,
      "hsn_code": "HSN/SAC digits, empty if not found"
    }
  ],
  "confidence_score": 90
}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"RAW OCR TEXT:\n\n{ocr_text}"}
        ]

        logger.debug("Requesting structured invoice parse from Groq llama-3.1-8b-instant")
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.1,  # Factual, highly deterministic parsing
            max_tokens=1500,
            response_format={"type": "json_object"}  # Direct JSON format enforcement!
        )

        response_content = response.choices[0].message.content.strip()
        parsed_data = json.loads(response_content)
        
        logger.info(f"Groq parse completed with confidence: {parsed_data.get('confidence_score', 0)}")
        return parsed_data

    except json.JSONDecodeError as e:
        logger.error(f"Malformed JSON returned by Groq parser: {e}")
        raise ValueError("AI parser output could not be decoded. Please retry.")
    except Exception as e:
        logger.error(f"Error in parse_ocr_text_to_json: {e}", exc_info=True)
        raise e
