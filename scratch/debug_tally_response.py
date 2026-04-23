"""Debug: Check the actual Tally response for SAL-0002 failure and try a manual push."""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from tally_integration.models import SyncLog
from voucher.models import Voucher
from tally_integration.xml_utilities import TallyXMLGenerator, TallyXMLParser
from tally_integration.client import TallyClient

# 1. Check stored response from last failed sync
print("=" * 60)
print("STEP 1: Checking SyncLog for SAL-0002 failure response")
print("=" * 60)
logs = SyncLog.objects.filter(
    model_name='Voucher',
    operation='PUSH',
).order_by('-created_at')[:5]

for log in logs:
    print(f"\n--- Log ID: {log.id} | Status: {log.status} | Created: {log.created_at} ---")
    print(f"Message: {log.message}")
    if log.response_xml:
        print(f"Response XML:\n{log.response_xml}")
    else:
        print("(No response_xml stored)")

# 2. Get the voucher and generate the XML
print("\n" + "=" * 60)
print("STEP 2: Generating current XML for SAL-0002")
print("=" * 60)
v = Voucher.objects.filter(number='SAL-0002').first()
if not v:
    print("ERROR: Voucher SAL-0002 not found!")
    sys.exit(1)

gen = TallyXMLGenerator()
xml = gen.get_sales_voucher_xml(v)
print(xml)

# 3. Try sending to Tally directly and capture the FULL response
print("\n" + "=" * 60)
print("STEP 3: Sending to Tally and capturing FULL response")
print("=" * 60)
try:
    client = TallyClient()
    response = client.post_with_retry(xml)
    print(f"FULL Tally Response:\n{response}")
    
    # Parse it
    parser = TallyXMLParser()
    print(f"\nIs Successful: {parser.is_import_successful(response)}")
    print(f"Error Message: {parser.extract_error_message(response)}")
    print(f"Import Stats: {parser.extract_import_stats(response)}")
except Exception as e:
    print(f"Connection Error: {e}")
