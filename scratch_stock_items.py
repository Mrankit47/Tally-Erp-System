import os
import django
import xml.etree.ElementTree as ET

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
try:
    django.setup()
except Exception:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

from apps.tally_integration.services import TallySyncService
from apps.company.models import Company
from django.contrib.auth import get_user_model

User = get_user_model()
try:
    company = Company.objects.first()
    user = User.objects.first()
    service = TallySyncService(company, user)

    print("Fetching stock items...")
    xml_request = service.generator.get_fetch_stock_item_xml()
    print("XML Request:", xml_request[:500])
    
    xml_response = service.client.post_with_retry(xml_request)
    print(f"XML Response Length: {len(xml_response)} bytes")
    
    if len(xml_response) < 1000:
        print("Raw XML response:")
        print(xml_response)

    items = service.parser.parse_stock_items(xml_response)
    print(f"Total parsed items: {len(items)}")
    for item in items[:5]:
        print(item)

    print("Attempting sync logic...")
    count = service.sync_stock_items_from_tally()
    print(f"Sync returned success count: {count}")

except Exception as e:
    import traceback
    traceback.print_exc()
