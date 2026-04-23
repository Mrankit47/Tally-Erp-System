"""Debug: Test Payment voucher XML to find what Tally accepts."""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from tally_integration.client import TallyClient
from tally_integration.xml_utilities import TallyXMLParser
import xml.etree.ElementTree as ET

client = TallyClient()
parser = TallyXMLParser()

def test_xml(label, xml):
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print(f"{'='*60}")
    try:
        response = client.post_with_retry(xml)
        success = parser.is_import_successful(response)
        root = ET.fromstring(parser.sanitize_xml(response))
        exceptions = root.findtext('.//EXCEPTIONS', '0')
        errors = root.findtext('.//ERRORS', '0')
        created = root.findtext('.//CREATED', '0')
        lineerror = root.findtext('.//LINEERROR', '')
        print(f"Result: {'SUCCESS' if success else 'FAILED'}")
        print(f"Created={created}, Errors={errors}, Exceptions={exceptions}")
        if lineerror:
            print(f"LINEERROR: {lineerror}")
        if not success and not lineerror:
            print(f"Full: {response.strip()}")
    except Exception as e:
        print(f"Error: {e}")

# Test 1: EXACT current output for Payment
test_xml("Current Output format", """<ENVELOPE>
    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME></REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Payment" ACTION="Create">
                        <DATE>20260401</DATE>
                        <EFFECTIVEDATE>20260401</EFFECTIVEDATE>
                        <VCHSTATUSDATE>20260401</VCHSTATUSDATE>
                        <VOUCHERTYPENAME>Payment</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>PAY-TEST-001</VOUCHERNUMBER>
                        <PARTYLEDGERNAME>Rent Expense</PARTYLEDGERNAME>
                        <NARRATION>Test payment</NARRATION>
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>Rent Expense</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-1000.00</AMOUNT>
                        </LEDGERENTRIES.LIST>
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>Cash</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>1000.00</AMOUNT>
                        </LEDGERENTRIES.LIST>
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>""")

# Test 2: Without PARTYLEDGERNAME (Payment vouchers typically don't have this unless in single entry mode, and it might expect the Cash/Bank ledger, not the Expense ledger)
test_xml("Without PARTYLEDGERNAME", """<ENVELOPE>
    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME></REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Payment" ACTION="Create">
                        <DATE>20260401</DATE>
                        <EFFECTIVEDATE>20260401</EFFECTIVEDATE>
                        <VCHSTATUSDATE>20260401</VCHSTATUSDATE>
                        <VOUCHERTYPENAME>Payment</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>PAY-TEST-002</VOUCHERNUMBER>
                        <NARRATION>Test payment</NARRATION>
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>Rent Expense</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-1000.00</AMOUNT>
                        </LEDGERENTRIES.LIST>
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>Cash</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>1000.00</AMOUNT>
                        </LEDGERENTRIES.LIST>
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>""")

# Test 3: With ALLLEDGERENTRIES.LIST instead of LEDGERENTRIES.LIST
test_xml("ALLLEDGERENTRIES.LIST", """<ENVELOPE>
    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME></REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Payment" ACTION="Create">
                        <DATE>20260401</DATE>
                        <EFFECTIVEDATE>20260401</EFFECTIVEDATE>
                        <VCHSTATUSDATE>20260401</VCHSTATUSDATE>
                        <VOUCHERTYPENAME>Payment</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>PAY-TEST-003</VOUCHERNUMBER>
                        <NARRATION>Test payment</NARRATION>
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>Rent Expense</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-1000.00</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>Cash</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>1000.00</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>""")
