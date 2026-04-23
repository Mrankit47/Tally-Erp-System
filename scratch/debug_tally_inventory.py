"""Debug: Test inventory voucher variations to find the exact format Tally accepts."""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from tally_integration.client import TallyClient
from tally_integration.xml_utilities import TallyXMLParser

client = TallyClient()
parser = TallyXMLParser()

def test_xml(label, xml):
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print(f"{'='*60}")
    try:
        response = client.post_with_retry(xml)
        success = parser.is_import_successful(response)
        stats = parser.extract_import_stats(response)
        # Also check exceptions
        import xml.etree.ElementTree as ET
        root = ET.fromstring(parser.sanitize_xml(response))
        exceptions = root.findtext('.//EXCEPTIONS', '0')
        print(f"Result: {'SUCCESS' if success else 'FAILED'}")
        print(f"Created={stats['created']}, Errors={stats['errors']}, Exceptions={exceptions}")
        if not success:
            print(f"Full Response: {response.strip()}")
    except Exception as e:
        print(f"Error: {e}")

# Test 1: Sales with inventory - simple (just stock item, no tax)
test_xml("Simple inventory voucher (no tax)", """<ENVELOPE>
    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME></REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Sales" ACTION="Create">
                        <DATE>20260401</DATE>
                        <EFFECTIVEDATE>20260401</EFFECTIVEDATE>
                        <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>TEST-INV-001</VOUCHERNUMBER>
                        <PARTYLEDGERNAME>Rahul Book Store</PARTYLEDGERNAME>
                        <ISINVOICE>Yes</ISINVOICE>
                        <HASINVENTORYENTRIES>Yes</HASINVENTORYENTRIES>
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>Rahul Book Store</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-4450.00</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>
                        <ALLINVENTORYENTRIES.LIST>
                            <STOCKITEMNAME>Notebook</STOCKITEMNAME>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <RATE>89.00/Nos</RATE>
                            <AMOUNT>4450.00</AMOUNT>
                            <ACTUALQTY>50 Nos</ACTUALQTY>
                            <BILLEDQTY>50 Nos</BILLEDQTY>
                            <ACCOUNTINGALLOCATIONS.LIST>
                                <LEDGERNAME>Sale A/c</LEDGERNAME>
                                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                                <AMOUNT>4450.00</AMOUNT>
                            </ACCOUNTINGALLOCATIONS.LIST>
                        </ALLINVENTORYENTRIES.LIST>
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>""")

# Test 2: Same but with whole numbers in quantity (no decimals)
test_xml("Inventory with whole qty and full tax", """<ENVELOPE>
    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME></REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Sales" ACTION="Create">
                        <DATE>20260401</DATE>
                        <EFFECTIVEDATE>20260401</EFFECTIVEDATE>
                        <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>TEST-INV-002</VOUCHERNUMBER>
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
                            <AMOUNT>4450.00</AMOUNT>
                            <ACTUALQTY>50 Nos</ACTUALQTY>
                            <BILLEDQTY>50 Nos</BILLEDQTY>
                            <ACCOUNTINGALLOCATIONS.LIST>
                                <LEDGERNAME>Sale A/c</LEDGERNAME>
                                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                                <AMOUNT>4450.00</AMOUNT>
                            </ACCOUNTINGALLOCATIONS.LIST>
                        </ALLINVENTORYENTRIES.LIST>
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>""")

# Test 3: With VCHSTATUSDATE and GUID (like original)
test_xml("With GUID and VCHSTATUSDATE + tax", """<ENVELOPE>
    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME></REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Sales" ACTION="Create">
                        <GUID>test-guid-003</GUID>
                        <DATE>20260401</DATE>
                        <EFFECTIVEDATE>20260401</EFFECTIVEDATE>
                        <VCHSTATUSDATE>20260401</VCHSTATUSDATE>
                        <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>TEST-INV-003</VOUCHERNUMBER>
                        <PARTYLEDGERNAME>Rahul Book Store</PARTYLEDGERNAME>
                        <NARRATION></NARRATION>
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
                            <AMOUNT>4450.00</AMOUNT>
                            <ACTUALQTY>50 Nos</ACTUALQTY>
                            <BILLEDQTY>50 Nos</BILLEDQTY>
                            <ACCOUNTINGALLOCATIONS.LIST>
                                <LEDGERNAME>Sale A/c</LEDGERNAME>
                                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                                <AMOUNT>4450.00</AMOUNT>
                            </ACCOUNTINGALLOCATIONS.LIST>
                        </ALLINVENTORYENTRIES.LIST>
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>""")
