import os
import django
import sys

# Setup paths
root = r'c:\Users\Ankit\OneDrive\Desktop\Major Project'
sys.path.insert(0, root)
sys.path.insert(0, os.path.join(root, 'apps'))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from voucher.models import Voucher
from tally_integration.xml_utilities import TallyXMLGenerator

v = Voucher.objects.filter(number='SAL-0001').first()
if v:
    xml = TallyXMLGenerator.get_sales_voucher_xml(v)
    print("--- XML START ---")
    print(xml)
    print("--- XML END ---")
else:
    print("Voucher SAL-0001 not found")
