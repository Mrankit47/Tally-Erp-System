"""
Tally XML Utilities.

Generator and Parser for Tally-compliant XML envelopes.
Supports Ledger masters and Sales Voucher (Invoice) operations.
"""

import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from decimal import Decimal
import logging

logger = logging.getLogger('apps.tally_integration')


# =============================================================================
# XML GENERATOR
# =============================================================================

class TallyXMLGenerator:
    """
    Constructs XML envelopes for various Tally operations.
    """

    @staticmethod
    def _get_static_variables(company_name=None, extra_vars=""):
        company_tag = f'\n                <SVCURRENTCOMPANY>{escape(company_name)}</SVCURRENTCOMPANY>' if company_name else ''
        return f"""<STATICVARIABLES>
                <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>{company_tag}{extra_vars}
            </STATICVARIABLES>"""

    @staticmethod
    def get_fetch_companies_xml():
        """
        Returns XML to fetch all companies open in Tally.
        """
        return """<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>Export</TALLYREQUEST>
        <TYPE>COLLECTION</TYPE>
        <ID>ListOfCompanies</ID>
    </HEADER>
    <BODY>
        <DESC>
            <STATICVARIABLES>
                <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
            </STATICVARIABLES>
            <TDL>
                <TDLMESSAGE>
                    <COLLECTION NAME="ListOfCompanies" ISINITIALIZE="Yes">
                        <TYPE>Company</TYPE>
                        <FETCH>Name, GUID</FETCH>
                    </COLLECTION>
                </TDLMESSAGE>
            </TDL>
        </DESC>
    </BODY>
</ENVELOPE>"""

    @staticmethod
    def get_fetch_ledger_xml(company_name=None):
        """
        Returns XML to fetch all Ledger masters from Tally using Collection method.
        We explicitly fetch Name, Parent, and OpeningBalance.
        """
        return f"""<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>Export</TALLYREQUEST>
        <TYPE>COLLECTION</TYPE>
        <ID>LedgersCollection</ID>
    </HEADER>
    <BODY>
        <DESC>
            {TallyXMLGenerator._get_static_variables(company_name)}
            <TDL>
                <TDLMESSAGE>
                    <COLLECTION NAME="LedgersCollection" ISINITIALIZE="Yes">
                        <TYPE>Ledger</TYPE>
                        <FETCH>Name, Parent, OpeningBalance</FETCH>
                    </COLLECTION>
                </TDLMESSAGE>
            </TDL>
        </DESC>
    </BODY>
</ENVELOPE>"""

    @staticmethod
    def get_fetch_stock_item_xml(company_name=None):
        """
        Returns XML to fetch all Stock Items from Tally using Collection method.
        """
        return f"""<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>Export</TALLYREQUEST>
        <TYPE>COLLECTION</TYPE>
        <ID>StockItemsCollection</ID>
    </HEADER>
    <BODY>
        <DESC>
            {TallyXMLGenerator._get_static_variables(company_name)}
            <TDL>
                <TDLMESSAGE>
                    <COLLECTION NAME="StockItemsCollection" ISINITIALIZE="Yes">
                        <TYPE>StockItem</TYPE>
                        <FETCH>Name, Parent, OpeningBalance, OpeningValue, BaseUnits, ClosingBalance, ClosingValue, OpeningRate, ClosingRate</FETCH>
                    </COLLECTION>
                </TDLMESSAGE>
            </TDL>
        </DESC>
    </BODY>
</ENVELOPE>"""

    @staticmethod
    def get_create_stock_item_xml(name, group="Primary", unit="Nos", opening_balance=0, opening_value=0):
        """
        Returns XML to create a Stock Item in Tally.
        """
        return f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>All Masters</REPORTNAME>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <STOCKITEM NAME="{name}" ACTION="Create">
                        <NAME>{name}</NAME>
                        <PARENT>{group}</PARENT>
                        <BASEUNITS>{unit}</BASEUNITS>
                        <OPENINGBALANCE>{opening_balance}</OPENINGBALANCE>
                        <OPENINGVALUE>{opening_value}</OPENINGVALUE>
                    </STOCKITEM>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""

    @staticmethod
    def get_fetch_vouchers_xml(voucher_type, from_date, to_date, company_name=None):
        """
        Returns XML to fetch vouchers of a specific type within a date range.
        Dates should be 'YYYYMMDD' format.
        """
        return f"""<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>Export</TALLYREQUEST>
        <TYPE>COLLECTION</TYPE>
        <ID>VoucherCollection</ID>
    </HEADER>
    <BODY>
        <DESC>
            {TallyXMLGenerator._get_static_variables(company_name, f'''
                <SVFROMDATE TYPE="Date">{from_date}</SVFROMDATE>
                <SVTODATE TYPE="Date">{to_date}</SVTODATE>''')}
            <TDL>
                <TDLMESSAGE>
                    <COLLECTION NAME="VoucherCollection" ISINITIALIZE="Yes">
                        <TYPE>Voucher</TYPE>
                        <FILTER>TypeFilter</FILTER>
                        <FETCH>*, AllLedgerEntries.*, AllInventoryEntries.*, LedgerEntries.*, AccountingAllocations.*</FETCH>
                    </COLLECTION>
                    <SYSTEM TYPE="FORMULAE" NAME="TypeFilter">
                        $VoucherTypeName = "{voucher_type}"
                    </SYSTEM>
                </TDLMESSAGE>
            </TDL>
        </DESC>
    </BODY>
</ENVELOPE>"""

    @staticmethod
    def get_create_ledger_xml(name, parent, opening_balance=0):
        """
        Returns XML to create a new Ledger master in Tally.
        """
        return f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>All Masters</REPORTNAME>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <LEDGER NAME="{escape(name)}" ACTION="Create">
                        <NAME.LIST>
                            <NAME>{escape(name)}</NAME>
                        </NAME.LIST>
                        <PARENT>{escape(parent)}</PARENT>
                        <OPENINGBALANCE>{opening_balance}</OPENINGBALANCE>
                        <ISBILLWISEON>Yes</ISBILLWISEON>
                    </LEDGER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""

    @staticmethod
    def get_sales_voucher_xml(voucher):
        """
        Generates a complete Tally Sales Voucher (Invoice) XML.

        Accounting: Customer (Dr) / Sales Revenue (Cr)
        Party Detection: First DEBIT entry = Party Ledger (Customer)
        """
        return TallyXMLGenerator._build_voucher_xml(
            voucher=voucher,
            vch_type='Sales',
            party_from='DEBIT',
            is_invoice=True,
            include_inventory=True,
        )

    @staticmethod
    def get_purchase_voucher_xml(voucher):
        """
        Generates a complete Tally Purchase Voucher XML.

        Accounting: Purchase Account (Dr) / Vendor (Cr)
        Party Detection: First CREDIT entry = Party Ledger (Vendor)
        """
        return TallyXMLGenerator._build_voucher_xml(
            voucher=voucher,
            vch_type='Purchase',
            party_from='CREDIT',
            is_invoice=True,
            include_inventory=True,
        )

    @staticmethod
    def get_payment_voucher_xml(voucher):
        """
        Generates a complete Tally Payment Voucher XML.

        Accounting: Expense/Vendor (Dr) / Cash or Bank (Cr)
        Party Detection: First DEBIT entry = Party Ledger (Expense/Vendor)

        In a Payment voucher:
            - You pay money FROM Cash/Bank (Credit side)
            - You pay TO an expense or a vendor (Debit side)
        """
        return TallyXMLGenerator._build_voucher_xml(
            voucher=voucher,
            vch_type='Payment',
            party_from='DEBIT',
            is_invoice=False,
            include_inventory=False,
        )

    @staticmethod
    def get_receipt_voucher_xml(voucher):
        """
        Generates a complete Tally Receipt Voucher XML.

        Accounting: Cash/Bank (Dr) / Party or Income (Cr)
        Party Detection: First CREDIT entry = Party Ledger (Customer/Income)

        In a Receipt voucher:
            - You receive money INTO Cash/Bank (Debit side)
            - The money comes FROM a customer or income source (Credit side)
        """
        return TallyXMLGenerator._build_voucher_xml(
            voucher=voucher,
            vch_type='Receipt',
            party_from='CREDIT',
            is_invoice=False,
            include_inventory=False,
        )

    @staticmethod
    def _build_voucher_xml(voucher, vch_type, party_from, is_invoice=False, include_inventory=False):
        """
        Internal helper that constructs the Tally Voucher XML envelope.

        Args:
            voucher: Django Voucher model instance.
            vch_type: Tally voucher type string ('Sales', 'Payment', 'Receipt').
            party_from: Which side to detect the party ledger from ('DEBIT' or 'CREDIT').
            is_invoice: Whether to include <ISINVOICE>Yes</ISINVOICE>.
            include_inventory: Whether to scan for ALLINVENTORYENTRIES.

        Returns:
            str: Complete Tally-compliant XML string.
        """
        from voucher.models import EntryType

        import uuid
        # Tally requires dates in YYYYMMDD format
        tally_date = voucher.date.strftime('%Y%m%d')
        guid = str(uuid.uuid4())

        debit_entries = voucher.entries.filter(entry_type=EntryType.DEBIT).select_related('ledger')
        credit_entries = voucher.entries.filter(entry_type=EntryType.CREDIT).select_related('ledger')

        # ─── Party Ledger Detection ───
        party_ledger_name = ''
        if party_from == 'DEBIT' and debit_entries.exists():
            party_ledger_name = debit_entries.first().ledger.name
        elif party_from == 'CREDIT' and credit_entries.exists():
            party_ledger_name = credit_entries.first().ledger.name

        # ─── Identify entries that have inventory (stock) transactions ───
        # These are handled via INVENTORYENTRIES.LIST with ACCOUNTINGALLOCATIONS,
        # so they must NOT appear again in LEDGERENTRIES.LIST (double-counting).
        inventory_entry_ids = set()
        inventory_entries_list = []
        if include_inventory:
            for entry in list(debit_entries) + list(credit_entries):
                if entry.stock_transactions.exists():
                    inventory_entry_ids.add(entry.id)
                    inventory_entries_list.append(entry)

        # ─── Build LEDGERENTRIES.LIST / ALLLEDGERENTRIES.LIST ───
        # Tally convention: If voucher has no inventory, it requires ALLLEDGERENTRIES.LIST
        # If it has inventory, it requires LEDGERENTRIES.LIST and INVENTORYENTRIES.LIST
        ledger_tag_name = "LEDGERENTRIES.LIST" if include_inventory else "ALLLEDGERENTRIES.LIST"
        
        ledger_entries_xml = ''
        for entry in debit_entries:
            if entry.id in inventory_entry_ids:
                continue
            ledger_entries_xml += f"""
                    <{ledger_tag_name}>
                        <LEDGERNAME>{escape(entry.ledger.name)}</LEDGERNAME>
                        <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                        <AMOUNT>-{entry.amount}</AMOUNT>
                    </{ledger_tag_name}>"""

        for entry in credit_entries:
            if entry.id in inventory_entry_ids:
                continue
            ledger_entries_xml += f"""
                    <{ledger_tag_name}>
                        <LEDGERNAME>{escape(entry.ledger.name)}</LEDGERNAME>
                        <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                        <AMOUNT>{entry.amount}</AMOUNT>
                    </{ledger_tag_name}>"""

        # ─── Build INVENTORYENTRIES.LIST (optional) ───
        inventory_xml = ''
        if include_inventory:
            for entry in inventory_entries_list:
                is_debit = entry.entry_type == EntryType.DEBIT
                is_deemed_positive = 'Yes' if is_debit else 'No'
                # Tally convention: Debit amounts are negative, Credit amounts are positive
                sign = '-' if is_debit else ''
                
                stock_txs = entry.stock_transactions.select_related('stock_item').all()
                for tx in stock_txs:
                    unit = escape(tx.stock_item.unit_of_measure or 'Nos')
                    amt = f"{sign}{tx.quantity * tx.rate}"
                    
                    inventory_xml += f"""
                    <INVENTORYENTRIES.LIST>
                        <STOCKITEMNAME>{escape(tx.stock_item.name)}</STOCKITEMNAME>
                        <ISDEEMEDPOSITIVE>{is_deemed_positive}</ISDEEMEDPOSITIVE>
                        <RATE>{tx.rate}/{unit}</RATE>
                        <AMOUNT>{amt}</AMOUNT>
                        <ACTUALQTY>{tx.quantity} {unit}</ACTUALQTY>
                        <BILLEDQTY>{tx.quantity} {unit}</BILLEDQTY>
                        <ACCOUNTINGALLOCATIONS.LIST>
                            <LEDGERNAME>{escape(entry.ledger.name)}</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>{is_deemed_positive}</ISDEEMEDPOSITIVE>
                            <AMOUNT>{amt}</AMOUNT>
                        </ACCOUNTINGALLOCATIONS.LIST>
                    </INVENTORYENTRIES.LIST>"""

        has_inventory = 'Yes' if inventory_xml else 'No'
        invoice_tag = '\n                        <ISINVOICE>Yes</ISINVOICE>' if is_invoice else ''
        inventory_flag = f'\n                        <HASINVENTORYENTRIES>{has_inventory}</HASINVENTORYENTRIES>' if include_inventory else ''

        return f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="{vch_type}" ACTION="Create">
                        <GUID>{guid}</GUID>
                        <DATE>{tally_date}</DATE>
                        <EFFECTIVEDATE>{tally_date}</EFFECTIVEDATE>
                        <VCHSTATUSDATE>{tally_date}</VCHSTATUSDATE>
                        <VOUCHERTYPENAME>{vch_type}</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>{escape(voucher.number)}</VOUCHERNUMBER>
                        <PARTYLEDGERNAME>{escape(party_ledger_name)}</PARTYLEDGERNAME>
                        <NARRATION>{escape(voucher.narration or '')}</NARRATION>{invoice_tag}{inventory_flag}{ledger_entries_xml}{inventory_xml}
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""


# =============================================================================
# XML PARSER
# =============================================================================

class TallyXMLParser:
    """
    Parses Tally responses into Python data structures.
    """

    @staticmethod
    def sanitize_xml(xml_string):
        """Removes invalid XML control characters that cause ET.fromstring to crash.
        Handles both raw control chars and XML-encoded references like &#4;
        """
        if not xml_string:
            return ""
        import re
        # 1. Remove XML-encoded control character references (&#0; through &#31; except &#9;, &#10;, &#13;)
        xml_string = re.sub(r'&#(?:0*[0-8]|0*1[0-2]|0*1[4-9]|0*2[0-9]|0*3[01]);', '', xml_string)
        # 2. Remove raw control characters
        xml_string = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', xml_string)
        return xml_string

    @staticmethod
    def parse_companies(xml_content):
        """Parses Tally companies."""
        try:
            xml_content = TallyXMLParser.sanitize_xml(xml_content)
            root = ET.fromstring(xml_content)
            companies = []
            for comp_node in root.iter('COMPANY'):
                name = comp_node.findtext('NAME')
                guid = comp_node.findtext('GUID')
                if name:
                    companies.append({
                        'name': name.strip(),
                        'guid': guid.strip() if guid else None
                    })
            return companies
        except Exception as e:
            logger.error(f"Failed to parse Tally companies XML: {str(e)}")
            return []

    @staticmethod
    def _extract_quantity(raw_str):
        """
        Extracts the numeric quantity from Tally's quantity format.
        Examples: ' 50 Nos' -> 50, '100 Nos' -> 100, '0' -> 0, '' -> 0
        """
        if not raw_str:
            return Decimal('0')
        raw_str = raw_str.strip()
        if not raw_str:
            return Decimal('0')
        # Take only the numeric part (before any space/unit suffix)
        import re
        match = re.match(r'[\s]*([\d.\-]+)', raw_str)
        if match:
            return Decimal(match.group(1))
        return Decimal('0')

    @staticmethod
    def parse_stock_items(xml_content):
        """Parses Tally stock items with opening/closing quantities and groups."""
        try:
            xml_content = TallyXMLParser.sanitize_xml(xml_content)
            root = ET.fromstring(xml_content)
            items = []
            for item_node in root.iter('STOCKITEM'):
                name = item_node.get('NAME') or (item_node.find('NAME').text if item_node.find('NAME') is not None else None)
                if not name:
                    continue
                name = name.strip()
                # Skip CMPINFO's <STOCKITEM>0</STOCKITEM> nodes
                if not name or name == '0':
                    continue

                opening_qty = TallyXMLParser._extract_quantity(
                    item_node.findtext('OPENINGBALANCE', '0')
                )
                closing_qty = TallyXMLParser._extract_quantity(
                    item_node.findtext('CLOSINGBALANCE', '0')
                )

                items.append({
                    'name': name,
                    'parent': item_node.findtext('PARENT', 'Primary').strip(),
                    'opening_balance': opening_qty,
                    'closing_balance': closing_qty,
                    'unit_of_measure': item_node.findtext('BASEUNITS', 'Nos').strip(),
                })
            return items
        except Exception as e:
            logger.error(f"Failed to parse stock items: {str(e)}")
            return []

    @staticmethod
    def parse_vouchers_fetch(xml_content):
        """Parses fetched vouchers from Tally."""
        try:
            xml_content = TallyXMLParser.sanitize_xml(xml_content)
            root = ET.fromstring(xml_content)
            vouchers = []
            for v_node in root.iter('VOUCHER'):
                number = v_node.findtext('VOUCHERNUMBER')
                if not number:
                    continue
                    
                v_data = {
                    'date': v_node.findtext('DATE'),
                    'number': number,
                    'party_name': v_node.findtext('PARTYLEDGERNAME'),
                    'narration': v_node.findtext('NARRATION'),
                    'entries': []
                }
                # Basic Ledger Entries
                # Tally can output either ALLLEDGERENTRIES.LIST or LEDGERENTRIES.LIST
                import itertools
                for l_entry in itertools.chain(v_node.iter('ALLLEDGERENTRIES.LIST'), v_node.iter('LEDGERENTRIES.LIST')):
                    ledger_name = l_entry.findtext('LEDGERNAME')
                    if not ledger_name:
                        continue
                        
                    v_data['entries'].append({
                        'ledger': ledger_name,
                        'amount': abs(Decimal(l_entry.findtext('AMOUNT', '0'))),
                        'is_debit': Decimal(l_entry.findtext('AMOUNT', '0')) < 0
                    })
                # Inventory Details
                for inv_entry in v_node.iter('ALLINVENTORYENTRIES.LIST'):
                    stock_item = inv_entry.findtext('STOCKITEMNAME')
                    if not stock_item:
                        continue
                        
                    # Extract ledger name from Accounting Allocations if present
                    ledger_name = None
                    alloc_list = inv_entry.find('ACCOUNTINGALLOCATIONS.LIST')
                    if alloc_list is not None:
                        ledger_name = alloc_list.findtext('LEDGERNAME')
                        
                    v_data['entries'].append({
                        'stock_item': stock_item,
                        'ledger': ledger_name,
                        'quantity': Decimal(inv_entry.findtext('BILLEDQTY', '0').split(' ')[0] or '0'),
                        'amount': abs(Decimal(inv_entry.findtext('AMOUNT', '0'))),
                        'is_debit': Decimal(inv_entry.findtext('AMOUNT', '0')) < 0
                    })
                vouchers.append(v_data)
            return vouchers
        except Exception:
            return []

    @staticmethod
    def parse_ledgers(xml_content):
        """
        Parses the 'List of Accounts' response and returns a list of ledger dicts.
        Handles both attribute-based naming and child-tag naming.
        """
        try:
            xml_content = TallyXMLParser.sanitize_xml(xml_content)
            root = ET.fromstring(xml_content)
            ledgers = []

            # Tally Returns ledgers in BODY/DATA/COLLECTION/LEDGER
            # or sometimes direct LEDGER nodes if customized. 
            # We use iter() for maximum flexibility.
            for ledger_node in root.iter('LEDGER'):
                # 1. Check NAME attribute (Modern Tally format)
                name = ledger_node.get('NAME')
                
                # 2. Check child <NAME> or nested <NAME.LIST><NAME>
                if not name:
                    name_node = ledger_node.find('NAME')
                    if name_node is not None:
                        name = name_node.text
                    else:
                        # Fallback: check for <NAME.LIST><NAME>
                        list_node = ledger_node.find('NAME.LIST')
                        if list_node is not None:
                            sub_name = list_node.find('NAME')
                            if sub_name is not None:
                                name = sub_name.text

                # 3. Handle specific Tally-formatted parents and balances
                if name:
                    # Tally sometimes prefixes parents with a space or group prefix
                    parent_node = ledger_node.find('PARENT')
                    opening_node = ledger_node.find('OPENINGBALANCE')

                    ledgers.append({
                        'name': name.strip(),
                        'parent': parent_node.text.strip() if parent_node is not None and parent_node.text else 'Primary',
                        'opening_balance': Decimal(opening_node.text or '0.00') if opening_node is not None else Decimal('0.00')
                    })
            
            return ledgers
        except ET.ParseError as e:
            logger.error(f"Failed to parse Tally ledger XML: {str(e)}")
            return []

    @staticmethod
    def extract_error_message(xml_content):
        """
        Deep search for error messages in a Tally Import response.
        Captures LINEERROR, ERROR, ERRORMSG, DESC, and other common tags.
        """
        try:
            xml_content = TallyXMLParser.sanitize_xml(xml_content)
            root = ET.fromstring(xml_content)
            error_tags = (
                'LINEERROR', 'ERROR', 'ERRORMSG', 'DESC',
                'DESCRIPTION', 'ERRDESC', 'SVCERROR',
            )
            errors = [
                node.text.strip() for node in root.iter()
                if node.tag in error_tags and node.text and node.text.strip()
            ]
            if errors:
                return " | ".join(errors)

            # Fallback: check if CREATED and ALTERED are 0 and show raw text
            created = root.findtext('.//CREATED', '0')
            altered = root.findtext('.//ALTERED', '0')
            if created == '0' and altered == '0':
                # Try to get any text content as a clue
                all_text = ' '.join(
                    t.strip() for t in root.itertext() if t.strip()
                )
                return f"Import failed (Created=0, Altered=0). Raw: {all_text[:500]}"

            return "Unknown error (no error tags found in response)"
        except Exception as e:
            return f"XML Parse Error: {str(e)}"

    @staticmethod
    def is_import_successful(xml_content):
        """
        Checks if the master/voucher creation or alteration was successful.
        Looks for <CREATED>1</CREATED> or <ALTERED>1</ALTERED> in the response.
        """
        try:
            xml_content = TallyXMLParser.sanitize_xml(xml_content)
            root = ET.fromstring(xml_content)
            created = root.findtext('.//CREATED', '0')
            altered = root.findtext('.//ALTERED', '0')
            return int(created) > 0 or int(altered) > 0
        except Exception:
            return False

    @staticmethod
    def extract_import_stats(xml_content):
        """
        Extracts detailed import statistics from a Tally response.
        
        Returns:
            dict: {'created': int, 'altered': int, 'deleted': int, 'errors': int}
        """
        stats = {'created': 0, 'altered': 0, 'deleted': 0, 'errors': 0}
        try:
            xml_content = TallyXMLParser.sanitize_xml(xml_content)
            root = ET.fromstring(xml_content)
            for key in stats:
                node = root.find(f'.//{key.upper()}')
                if node is not None and node.text:
                    stats[key] = int(node.text)
        except Exception:
            pass
        return stats
