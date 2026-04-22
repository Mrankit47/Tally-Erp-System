import os
import django
import xml.etree.ElementTree as ET

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
try:
    django.setup()
except Exception:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

from tally_integration.client import TallyClient
from tally_integration.xml_utilities import TallyXMLGenerator, TallyXMLParser

client = TallyClient()
gen = TallyXMLGenerator()
parser = TallyXMLParser()

# Use the updated generator
xml = gen.get_fetch_vouchers_xml('Sales', '20260301', '20260302')
resp = client.post_with_retry(xml)

print(f"Response length: {len(resp)} bytes")

# Test sanitization + parsing
sanitized = parser.sanitize_xml(resp)
root = ET.fromstring(sanitized)

print("\n=== RAW XML INSPECTION ===")
for v_node in root.iter('VOUCHER'):
    vnum = v_node.findtext('VOUCHERNUMBER')
    party = v_node.findtext('PARTYLEDGERNAME')
    date = v_node.findtext('DATE')
    ledger_entries = list(v_node.iter('ALLLEDGERENTRIES.LIST'))
    inv_entries = list(v_node.iter('ALLINVENTORYENTRIES.LIST'))
    
    if not vnum:
        print(f"  [Skipping voucher node without number]")
        continue
    
    print(f"\nVoucher #{vnum} | Date: {date} | Party: {party}")
    print(f"  Ledger Entries: {len(ledger_entries)}")
    for le in ledger_entries:
        ln = le.findtext('LEDGERNAME')
        amt = le.findtext('AMOUNT')
        deemed = le.findtext('ISDEEMEDPOSITIVE')
        is_party = le.findtext('ISPARTYLEDGER')
        print(f"    -> {ln} | Amount: {amt} | DebitSide: {deemed} | IsParty: {is_party}")
    print(f"  Inventory Entries: {len(inv_entries)}")
    for ie in inv_entries:
        sn = ie.findtext('STOCKITEMNAME')
        amt = ie.findtext('AMOUNT')
        qty = ie.findtext('BILLEDQTY')
        print(f"    -> {sn} | Amount: {amt} | Qty: {qty}")

print("\n=== PARSER OUTPUT ===")
parsed = parser.parse_vouchers_fetch(sanitized)
import json
print(json.dumps(parsed, indent=2, default=str))
