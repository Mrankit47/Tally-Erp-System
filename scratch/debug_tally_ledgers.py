"""Debug: Check if ledgers exist in Tally and test with a minimal voucher."""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from tally_integration.client import TallyClient
from tally_integration.xml_utilities import TallyXMLGenerator, TallyXMLParser

client = TallyClient()
parser = TallyXMLParser()

# 1. Check what ledgers exist in Tally
print("=" * 60)
print("STEP 1: Fetching all ledgers from Tally to check names")
print("=" * 60)
gen = TallyXMLGenerator()
xml = gen.get_fetch_ledger_xml(company_name="The Virtual Canvas")
response = client.post_with_retry(xml)
ledgers = parser.parse_ledgers(response)
print(f"Found {len(ledgers)} ledgers in Tally:")
for l in ledgers:
    print(f"  - '{l['name']}' (Parent: {l['parent']})")

# 2. Check the specific ledgers we need
needed = ['Rahul Book Store', 'Sale A/c', 'CGST 6%', 'SGST 6%']
print(f"\nChecking needed ledgers:")
ledger_names = [l['name'] for l in ledgers]
for name in needed:
    exists = name in ledger_names
    print(f"  '{name}' -> {'FOUND' if exists else 'MISSING!'}")

# 3. Check stock items in Tally
print("\n" + "=" * 60)
print("STEP 2: Fetching stock items from Tally")
print("=" * 60)
xml = gen.get_fetch_stock_item_xml(company_name="The Virtual Canvas")
response = client.post_with_retry(xml)
items = parser.parse_stock_items(response)
print(f"Found {len(items)} stock items:")
for i in items:
    print(f"  - '{i['name']}' (Unit: {i['unit_of_measure']}, Parent: {i['parent']})")

stock_names = [i['name'] for i in items]
print(f"\n  'Notebook' -> {'FOUND' if 'Notebook' in stock_names else 'MISSING!'}")

# 4. Test: Accounting balance check
print("\n" + "=" * 60)
print("STEP 3: Accounting Balance Check")
print("=" * 60)
# DR: Rahul Book Store = 4984
# CR (ledger entries): CGST 6% = 267 + SGST 6% = 267 = 534
# CR (via inventory/accounting allocation): Sale A/c = 4450
# Total CR = 534 + 4450 = 4984
print(f"DR Total: 4984.00")
print(f"CR Total (Ledger): 267.00 + 267.00 = 534.00")
print(f"CR Total (Inventory Allocation): 4450.00")
print(f"CR Grand Total: {534 + 4450}")
print(f"Balanced: {4984 == 534 + 4450}")

# 5. Try a MINIMAL sales voucher without inventory to isolate the issue
print("\n" + "=" * 60)
print("STEP 4: Testing MINIMAL voucher (no inventory)")
print("=" * 60)
minimal_xml = """<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Sales" ACTION="Create">
                        <DATE>20260401</DATE>
                        <EFFECTIVEDATE>20260401</EFFECTIVEDATE>
                        <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>TEST-MINIMAL-001</VOUCHERNUMBER>
                        <PARTYLEDGERNAME>Rahul Book Store</PARTYLEDGERNAME>
                        <NARRATION>Test minimal voucher</NARRATION>
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>Rahul Book Store</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-1000.00</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>Sale A/c</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>1000.00</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""

print("Sending minimal test voucher...")
response = client.post_with_retry(minimal_xml)
print(f"Response:\n{response}")
print(f"Success: {parser.is_import_successful(response)}")
