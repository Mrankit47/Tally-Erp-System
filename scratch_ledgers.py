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

xml = gen.get_fetch_ledger_xml()
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
