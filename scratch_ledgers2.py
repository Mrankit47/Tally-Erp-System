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
from tally_integration.xml_utilities import TallyXMLParser

client = TallyClient()

xml = """<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>Export</TALLYREQUEST>
        <TYPE>COLLECTION</TYPE>
        <ID>LedgerCollection</ID>
    </HEADER>
    <BODY>
        <DESC>
            <STATICVARIABLES>
                <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
            </STATICVARIABLES>
            <TDL>
                <TDLMESSAGE>
                    <COLLECTION NAME="LedgerCollection" ISINITIALIZE="Yes">
                        <TYPE>Ledger</TYPE>
                        <FETCH>Name, Parent, OpeningBalance</FETCH>
                    </COLLECTION>
                </TDLMESSAGE>
            </TDL>
        </DESC>
    </BODY>
</ENVELOPE>"""

try:
    resp = client.post_with_retry(xml)
    print("RAW LEDGERS XML (excerpt):", resp[:1500])
    
    parser = TallyXMLParser()
    ledgers = parser.parse_ledgers(resp)
    print("\nPARSED LEDGERS:")
    for l in ledgers:
        if l['name'] not in ['CGST', 'SGST/UTGST', 'IGST']:
            print(f"Name: {l['name']} | Parent: {l['parent']}")
except Exception as e:
    print("Error:", e)
