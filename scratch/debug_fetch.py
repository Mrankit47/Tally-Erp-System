"""Debug: Fetch single voucher XML from Tally."""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from tally_integration.client import TallyClient
client = TallyClient()

xml = """<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Export Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Voucher Register</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>The Virtual Canvas</SVCURRENTCOMPANY>
                    <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
                    <SVFROMDATE>20260401</SVFROMDATE>
                    <SVTODATE>20260430</SVTODATE>
                </STATICVARIABLES>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""

response = client.post_with_retry(xml)
print(response[:3000])
