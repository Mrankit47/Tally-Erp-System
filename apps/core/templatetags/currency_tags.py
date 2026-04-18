from django import template
from decimal import Decimal

register = template.Library()

@register.filter(name='indian_currency')
def indian_currency(value):
    """
    Formats a number as Indian Currency (e.g., ₹ 1,25,000.00).
    Handles integers, floats, decimals, and strings that can be cast to float.
    """
    try:
        # Check if the value is essentially zero or empty
        if value is None or value == '':
            return "₹ 0.00"

        # Convert to float for formatting
        num = float(value)
        
        # Format to 2 decimal places to get strings like '125000.50'
        num_str = f"{num:.2f}"
        
        # Split integer and fractional parts
        if '.' in num_str:
            integer_part, fractional_part = num_str.split('.')
        else:
            integer_part, fractional_part = num_str, "00"
            
        # Handle negative sign
        is_negative = False
        if integer_part.startswith('-'):
            is_negative = True
            integer_part = integer_part[1:]

        # Format integer part according to Indian numbering system:
        # Last 3 digits separated by comma, then every 2 digits.
        if len(integer_part) > 3:
            last_three = integer_part[-3:]
            remaining = integer_part[:-3]
            # Group the remaining by 2
            reversed_remaining = remaining[::-1]
            groups = [reversed_remaining[i:i+2][::-1] for i in range(0, len(reversed_remaining), 2)]
            # Reconstruct
            formatted_integer = ','.join(groups[::-1]) + ',' + last_three
        else:
            formatted_integer = integer_part

        formatted = f"₹ {formatted_integer}.{fractional_part}"
        if is_negative:
            formatted = f"-{formatted}"
            
        return formatted

    except (ValueError, TypeError):
        return value  # If it cannot be formatted, return as-is

@register.filter(name='split')
def split(value, key=' '):
    return value.split(key)

@register.filter(name='get_item')
def get_item(dictionary, key):
    return dictionary.get(key)
