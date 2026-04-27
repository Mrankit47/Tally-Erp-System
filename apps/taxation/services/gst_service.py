from decimal import Decimal, ROUND_HALF_UP


def round_currency(value):
    """
    Rounds a value to 2 decimal places using ROUND_HALF_UP.
    Ensures consistency in financial calculations.
    """
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_gst(amount, seller_state_code, buyer_state_code, tax_rate):
    """
    Calculates GST components (CGST, SGST, IGST) based on state codes and tax rate.
    
    Rules:
    - If seller_state_code == buyer_state_code: Intra-state (CGST + SGST)
    - If seller_state_code != buyer_state_code: Inter-state (IGST)
    
    Args:
        amount (float/Decimal): Base taxable value
        seller_state_code (str): GST State Code of the supplier
        buyer_state_code (str): GST State Code of the recipient
        tax_rate (float/Decimal): Total GST percentage (e.g., 18)
        
    Returns:
        dict: Structured breakdown of calculations
    """
    
    # 1. Validations
    if amount <= 0:
        raise ValueError("Taxable amount must be positive.")
    if tax_rate < 0:
        raise ValueError("Tax rate cannot be negative.")
    if not str(seller_state_code).strip() or not str(buyer_state_code).strip():
        raise ValueError("Both seller and buyer state codes are required for GST calculation.")

    # 2. Convert to Decimal for precision
    amount = Decimal(str(amount))
    tax_rate = Decimal(str(tax_rate))
    
    cgst_rate = Decimal('0')
    sgst_rate = Decimal('0')
    igst_rate = Decimal('0')

    # 3. Determine Tax Type (Intra-state vs Inter-state)
    is_intra_state = str(seller_state_code).strip() == str(buyer_state_code).strip()

    if is_intra_state:
        # Split tax equally between Center and State
        cgst_rate = tax_rate / 2
        sgst_rate = tax_rate / 2
    else:
        # Full tax goes to Integrated GST
        igst_rate = tax_rate

    # 4. Calculate Amounts
    cgst_amount = amount * (cgst_rate / 100)
    sgst_amount = amount * (sgst_rate / 100)
    igst_amount = amount * (igst_rate / 100)
    
    total_tax = cgst_amount + sgst_amount + igst_amount
    total_amount = amount + total_tax

    # 5. Return Rounded Response
    return {
        "base_amount": float(round_currency(amount)),
        "cgst_rate": float(cgst_rate),
        "sgst_rate": float(sgst_rate),
        "igst_rate": float(igst_rate),
        "cgst_amount": float(round_currency(cgst_amount)),
        "sgst_amount": float(round_currency(sgst_amount)),
        "igst_amount": float(round_currency(igst_amount)),
        "total_tax": float(round_currency(total_tax)),
        "total_amount": float(round_currency(total_amount)),
        "is_intra_state": is_intra_state
    }


# Example Usage:
# result = calculate_gst(amount=1000, seller_state_code="27", buyer_state_code="27", tax_rate=18)
# print(result)
# Output: {'base_amount': 1000.0, 'cgst_rate': 9.0, 'sgst_rate': 9.0, 'igst_rate': 0.0, ...}
