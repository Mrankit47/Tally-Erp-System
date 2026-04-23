"""Debug: Export an existing sales voucher from Tally to see the EXACT format Tally uses."""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from tally_integration.client import TallyClient
from tally_integration.xml_utilities import TallyXMLParser

client = TallyClient()
parser = TallyXMLParser()

# Fetch ALL sales vouchers from Tally to see what already exists
xml_request = """<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>Export</TALLYREQUEST>
        <TYPE>COLLECTION</TYPE>
        <ID>ExportVouchers</ID>
    </HEADER>
    <BODY>
        <DESC>
            <STATICVARIABLES>
                <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                <SVCURRENTCOMPANY>The Virtual Canvas</SVCURRENTCOMPANY>
                <SVFROMDATE TYPE="Date">20250401</SVFROMDATE>
                <SVTODATE TYPE="Date">20270331</SVTODATE>
            </STATICVARIABLES>
            <TDL>
                <TDLMESSAGE>
                    <COLLECTION NAME="ExportVouchers" ISINITIALIZE="Yes">
                        <TYPE>Voucher</TYPE>
                        <FILTER>SalesFilter</FILTER>
                        <FETCH>*, AllLedgerEntries.*, AllInventoryEntries.*, AllInventoryEntries.AccountingAllocations.*</FETCH>
                    </COLLECTION>
                    <SYSTEM TYPE="FORMULAE" NAME="SalesFilter">
                        $VoucherTypeName = "Sales"
                    </SYSTEM>
                </TDLMESSAGE>
            </TDL>
        </DESC>
    </BODY>
</ENVELOPE>"""

print("Fetching sales vouchers from Tally...")
response = client.post_with_retry(xml_request)

# Save to file for inspection
with open('scratch/tally_sales_export.xml', 'w', encoding='utf-8') as f:
    f.write(response)

print(f"Response length: {len(response)} bytes")
print(f"Saved to scratch/tally_sales_export.xml")
print()

# Print the first 5000 chars
print("=" * 60)
print("EXPORTED SALES VOUCHER XML (first 5000 chars):")
print("=" * 60)
print(response[:5000])
