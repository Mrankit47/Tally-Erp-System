import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
try:
    django.setup()
except Exception:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

from tally_integration.client import TallyClient

client = TallyClient()

xml = """<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>Export</TALLYREQUEST>
        <TYPE>COLLECTION</TYPE>
        <ID>VoucherCollection</ID>
    </HEADER>
    <BODY>
        <DESC>
            <STATICVARIABLES>
                <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                <SVFROMDATE>20260301</SVFROMDATE>
                <SVTODATE>20260302</SVTODATE>
            </STATICVARIABLES>
            <TDL>
                <TDLMESSAGE>
                    <COLLECTION NAME="VoucherCollection" ISINITIALIZE="Yes">
                        <TYPE>Voucher</TYPE>
                        <FILTER>TypeFilter</FILTER>
                        <FETCH>*, AllLedgerEntries.*, AllInventoryEntries.*, LedgerEntries.*, AccountingAllocations.*</FETCH>
                    </COLLECTION>
                    <SYSTEM TYPE="FORMULAE" NAME="TypeFilter">
                        $VoucherTypeName = "Sales"
                    </SYSTEM>
                </TDLMESSAGE>
            </TDL>
        </DESC>
    </BODY>
</ENVELOPE>"""

resp = client.post_with_retry(xml)
print('RAW XML LENGTH:', len(resp))
print('RAW XML excerpt:', resp[:2000])

from tally_integration.xml_utilities import TallyXMLParser
parser = TallyXMLParser()
parsed = parser.parse_vouchers_fetch(resp)
print('\nPARSED:', parsed)
