"""Debug: Test with NEGATIVE amounts in inventory entries (Tally convention)."""
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
        print(f"Result: {'SUCCESS' if success else 'FAILED'}")
        print(f"Created={created}, Errors={errors}, Exceptions={exceptions}")
        if not success:
            lineerror = root.findtext('.//LINEERROR', '')
            if lineerror:
                print(f"LINEERROR: {lineerror}")
    except Exception as e:
        print(f"Error: {e}")

# Test 1: Negative amounts in inventory (as per Tally convention for sales outward)
test_xml("Negative AMOUNT in inventory + accounting allocation", """<ENVELOPE>
    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME></REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Sales" ACTION="Create">
                        <DATE>20260401</DATE>
                        <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>TEST-NEG-001</VOUCHERNUMBER>
                        <PARTYLEDGERNAME>Rahul Book Store</PARTYLEDGERNAME>
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>Rahul Book Store</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-4450.00</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>
                        <ALLINVENTORYENTRIES.LIST>
                            <STOCKITEMNAME>Notebook</STOCKITEMNAME>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <RATE>89.00/Nos</RATE>
                            <AMOUNT>-4450.00</AMOUNT>
                            <ACTUALQTY>50 Nos</ACTUALQTY>
                            <BILLEDQTY>50 Nos</BILLEDQTY>
                            <ACCOUNTINGALLOCATIONS.LIST>
                                <LEDGERNAME>Sale A/c</LEDGERNAME>
                                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                                <AMOUNT>-4450.00</AMOUNT>
                            </ACCOUNTINGALLOCATIONS.LIST>
                        </ALLINVENTORYENTRIES.LIST>
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>""")

# Test 2: Using QUANTITY instead of ACTUALQTY/BILLEDQTY
test_xml("QUANTITY tag instead of ACTUALQTY/BILLEDQTY", """<ENVELOPE>
    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME></REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Sales" ACTION="Create">
                        <DATE>20260401</DATE>
                        <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>TEST-NEG-002</VOUCHERNUMBER>
                        <PARTYLEDGERNAME>Rahul Book Store</PARTYLEDGERNAME>
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>Rahul Book Store</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-4450.00</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>
                        <ALLINVENTORYENTRIES.LIST>
                            <STOCKITEMNAME>Notebook</STOCKITEMNAME>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <RATE>89.00/Nos</RATE>
                            <AMOUNT>-4450.00</AMOUNT>
                            <QUANTITY>50 Nos</QUANTITY>
                            <ACCOUNTINGALLOCATIONS.LIST>
                                <LEDGERNAME>Sale A/c</LEDGERNAME>
                                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                                <AMOUNT>-4450.00</AMOUNT>
                            </ACCOUNTINGALLOCATIONS.LIST>
                        </ALLINVENTORYENTRIES.LIST>
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>""")

# Test 3: Full voucher with tax + negative inventory amounts
test_xml("Full voucher with tax + negative inventory amounts", """<ENVELOPE>
    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME></REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Sales" ACTION="Create">
                        <DATE>20260401</DATE>
                        <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>TEST-NEG-003</VOUCHERNUMBER>
                        <PARTYLEDGERNAME>Rahul Book Store</PARTYLEDGERNAME>
                        <ISINVOICE>Yes</ISINVOICE>
                        <HASINVENTORYENTRIES>Yes</HASINVENTORYENTRIES>
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>Rahul Book Store</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-4984.00</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>CGST 6%</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>267.00</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>SGST 6%</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>267.00</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>
                        <ALLINVENTORYENTRIES.LIST>
                            <STOCKITEMNAME>Notebook</STOCKITEMNAME>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <RATE>89.00/Nos</RATE>
                            <AMOUNT>-4450.00</AMOUNT>
                            <ACTUALQTY>50 Nos</ACTUALQTY>
                            <BILLEDQTY>50 Nos</BILLEDQTY>
                            <ACCOUNTINGALLOCATIONS.LIST>
                                <LEDGERNAME>Sale A/c</LEDGERNAME>
                                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                                <AMOUNT>-4450.00</AMOUNT>
                            </ACCOUNTINGALLOCATIONS.LIST>
                        </ALLINVENTORYENTRIES.LIST>
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>""")
