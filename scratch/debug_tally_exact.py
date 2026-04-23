"""Debug: Test exact same format as Tally export - match as closely as possible."""
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

# Test 1: Match the EXACT structure from Tally export
# Key differences from our code:
# - Add OBJVIEW attribute
# - Add PERSISTEDVIEW tag
# - AMOUNT is POSITIVE in inventory 
# - Add ISINVOICE, HASINVENTORYENTRIES
# - Use company scoping via STATICVARIABLES
test_xml("Exact Tally export format match (Pen 100 @ 10)", """<ENVELOPE>
    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>The Virtual Canvas</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Sales" ACTION="Create" OBJVIEW="Invoice Voucher View">
                        <DATE>20260401</DATE>
                        <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
                        <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>
                        <VOUCHERNUMBER>TEST-EXACT-001</VOUCHERNUMBER>
                        <PARTYLEDGERNAME>Rahul Book Store</PARTYLEDGERNAME>
                        <ISINVOICE>Yes</ISINVOICE>
                        <HASINVENTORYENTRIES>Yes</HASINVENTORYENTRIES>
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>Rahul Book Store</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-1000.00</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>
                        <ALLINVENTORYENTRIES.LIST>
                            <STOCKITEMNAME>Pen</STOCKITEMNAME>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <RATE>10.00/Nos</RATE>
                            <AMOUNT>1000.00</AMOUNT>
                            <ACTUALQTY> 100 Nos</ACTUALQTY>
                            <BILLEDQTY> 100 Nos</BILLEDQTY>
                            <ACCOUNTINGALLOCATIONS.LIST>
                                <LEDGERNAME>Sale A/c</LEDGERNAME>
                                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                                <AMOUNT>1000.00</AMOUNT>
                            </ACCOUNTINGALLOCATIONS.LIST>
                        </ALLINVENTORYENTRIES.LIST>
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>""")

# Test 2: Same but without OBJVIEW and PERSISTEDVIEW  
test_xml("Without OBJVIEW/PERSISTEDVIEW but with company", """<ENVELOPE>
    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>The Virtual Canvas</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Sales" ACTION="Create">
                        <DATE>20260401</DATE>
                        <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>TEST-EXACT-002</VOUCHERNUMBER>
                        <PARTYLEDGERNAME>Rahul Book Store</PARTYLEDGERNAME>
                        <ISINVOICE>Yes</ISINVOICE>
                        <HASINVENTORYENTRIES>Yes</HASINVENTORYENTRIES>
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>Rahul Book Store</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-1000.00</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>
                        <ALLINVENTORYENTRIES.LIST>
                            <STOCKITEMNAME>Pen</STOCKITEMNAME>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <RATE>10.00/Nos</RATE>
                            <AMOUNT>1000.00</AMOUNT>
                            <ACTUALQTY> 100 Nos</ACTUALQTY>
                            <BILLEDQTY> 100 Nos</BILLEDQTY>
                            <ACCOUNTINGALLOCATIONS.LIST>
                                <LEDGERNAME>Sale A/c</LEDGERNAME>
                                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                                <AMOUNT>1000.00</AMOUNT>
                            </ACCOUNTINGALLOCATIONS.LIST>
                        </ALLINVENTORYENTRIES.LIST>
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>""")

# Test 3: Without company scope (original way)
test_xml("Without company scope", """<ENVELOPE>
    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Sales" ACTION="Create" OBJVIEW="Invoice Voucher View">
                        <DATE>20260401</DATE>
                        <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
                        <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>
                        <VOUCHERNUMBER>TEST-EXACT-003</VOUCHERNUMBER>
                        <PARTYLEDGERNAME>Rahul Book Store</PARTYLEDGERNAME>
                        <ISINVOICE>Yes</ISINVOICE>
                        <HASINVENTORYENTRIES>Yes</HASINVENTORYENTRIES>
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>Rahul Book Store</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-1000.00</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>
                        <ALLINVENTORYENTRIES.LIST>
                            <STOCKITEMNAME>Pen</STOCKITEMNAME>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <RATE>10.00/Nos</RATE>
                            <AMOUNT>1000.00</AMOUNT>
                            <ACTUALQTY> 100 Nos</ACTUALQTY>
                            <BILLEDQTY> 100 Nos</BILLEDQTY>
                            <ACCOUNTINGALLOCATIONS.LIST>
                                <LEDGERNAME>Sale A/c</LEDGERNAME>
                                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                                <AMOUNT>1000.00</AMOUNT>
                            </ACCOUNTINGALLOCATIONS.LIST>
                        </ALLINVENTORYENTRIES.LIST>
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>""")

# Test 4: Using LEDGERENTRIES.LIST instead of ALLLEDGERENTRIES.LIST
test_xml("LEDGERENTRIES.LIST instead of ALLLEDGERENTRIES.LIST", """<ENVELOPE>
    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>The Virtual Canvas</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Sales" ACTION="Create" OBJVIEW="Invoice Voucher View">
                        <DATE>20260401</DATE>
                        <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
                        <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>
                        <VOUCHERNUMBER>TEST-EXACT-004</VOUCHERNUMBER>
                        <PARTYLEDGERNAME>Rahul Book Store</PARTYLEDGERNAME>
                        <ISINVOICE>Yes</ISINVOICE>
                        <HASINVENTORYENTRIES>Yes</HASINVENTORYENTRIES>
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>Rahul Book Store</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-1000.00</AMOUNT>
                        </LEDGERENTRIES.LIST>
                        <INVENTORYENTRIES.LIST>
                            <STOCKITEMNAME>Pen</STOCKITEMNAME>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <RATE>10.00/Nos</RATE>
                            <AMOUNT>1000.00</AMOUNT>
                            <ACTUALQTY> 100 Nos</ACTUALQTY>
                            <BILLEDQTY> 100 Nos</BILLEDQTY>
                            <ACCOUNTINGALLOCATIONS.LIST>
                                <LEDGERNAME>Sale A/c</LEDGERNAME>
                                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                                <AMOUNT>1000.00</AMOUNT>
                            </ACCOUNTINGALLOCATIONS.LIST>
                        </INVENTORYENTRIES.LIST>
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>""")

# Test 5: Completely use LEDGERENTRIES.LIST for ALL entries including tax
# and INVENTORYENTRIES.LIST for inventory
test_xml("LEDGERENTRIES + INVENTORYENTRIES + BATCH", """<ENVELOPE>
    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>The Virtual Canvas</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Sales" ACTION="Create" OBJVIEW="Invoice Voucher View">
                        <DATE>20260401</DATE>
                        <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
                        <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>
                        <VOUCHERNUMBER>TEST-EXACT-005</VOUCHERNUMBER>
                        <PARTYLEDGERNAME>Rahul Book Store</PARTYLEDGERNAME>
                        <ISINVOICE>Yes</ISINVOICE>
                        <HASINVENTORYENTRIES>Yes</HASINVENTORYENTRIES>
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>Rahul Book Store</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-1000.00</AMOUNT>
                        </LEDGERENTRIES.LIST>
                        <INVENTORYENTRIES.LIST>
                            <STOCKITEMNAME>Pen</STOCKITEMNAME>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <RATE>10.00/Nos</RATE>
                            <AMOUNT>1000.00</AMOUNT>
                            <ACTUALQTY> 100 Nos</ACTUALQTY>
                            <BILLEDQTY> 100 Nos</BILLEDQTY>
                            <BATCHALLOCATIONS.LIST>
                                <GODOWNNAME>Main Location</GODOWNNAME>
                                <BATCHNAME>Primary Batch</BATCHNAME>
                                <AMOUNT>1000.00</AMOUNT>
                                <ACTUALQTY> 100 Nos</ACTUALQTY>
                                <BILLEDQTY> 100 Nos</BILLEDQTY>
                            </BATCHALLOCATIONS.LIST>
                            <ACCOUNTINGALLOCATIONS.LIST>
                                <LEDGERNAME>Sale A/c</LEDGERNAME>
                                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                                <AMOUNT>1000.00</AMOUNT>
                            </ACCOUNTINGALLOCATIONS.LIST>
                        </INVENTORYENTRIES.LIST>
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>""")
