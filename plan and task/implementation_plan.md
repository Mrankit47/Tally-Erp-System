# Reports & Analytics Module (Ultra-Professional Build)

This plan outlines the architecture for the enhanced, demo-ready reporting suite including Trial Balance, Profit & Loss statements, visual analytics, CSV exports, and performance optimization.

## Proposed Changes

### `reports` Services (`apps/reports/services.py`)
- `get_ledger_category(ledger)`: Recursive categorization into 'Assets', 'Liabilities', 'Income', 'Expenses' logic.
- `generate_trial_balance(company)`: 
    - Compute balances intelligently (Debit vs Credit splits).
    - Track `total_debit` and `total_credit`.
    - Provide `difference` validation.
- `generate_profit_and_loss(company)`:
    - Track `total_income`, `total_expenses`, and `net_profit`.
- `get_top_expenses(company, limit=5)`:
    - Subquery aggregating total `DEBIT` entries specifically for ledgers identified as Expenses.

### URL Routing & Django Views (`apps/reports/urls.py` & `apps/reports/views.py`)
- **Web Views**:
    - `trial_balance_view`: Assemble TB data. Add empty state context.
    - `profit_loss_view`: Assemble P&L data + Top 5 expenses + Chart.js datasets filtered to the last 6-12 months.
- **CSV Export Endpoints**:
    - `export_trial_balance_csv` & `export_profit_loss_csv`: Generates the file. **Includes a top metadata header** (`Generated on: [date]`, `Company: [name]`) before injecting data headers.

*(Note: We will append the `reports/urls.py` module directly to `config/urls.py` via `include()`.)*

### UI Utilities & Templates Component

#### [NEW] Custom Template Filter (`apps/core/templatetags/currency_tags.py`)
- Add a custom `{{ value|indian_currency }}` filter to aggressively ensure all values render as `₹ 1,25,000.00` correctly across the module.

#### [MODIFY] `templates/base.html`
- Inject the Analytics drop-down into the sidebar including the new URLs.
- Include a lightweight global CSS spinner for page-load UX.

#### [NEW] `templates/reports/trial_balance.html`
- **Tables**: `sticky top-0 bg-white z-10` headers with `hover:bg-gray-50 transition-all duration-200` row effects.
- **UX**: Inject the "Difference Check" floating UI. If `diff == 0`, show green "Balanced". Else red mismatch banner.
- **Empty States**: If no data, show a beautiful centered SVG Heroicon with `Start adding vouchers to see reports`.

#### [NEW] `templates/reports/profit_loss.html`
- **Layout**: Dynamic Summary Top-Cards (Income, Expense, Net Result) conditionally styled Red/Green. Dual-Column Income vs Expense rendering. Section headings correctly mapped.
- **Charts**: 
  - Income vs Expenses Bar Chart / Net Profit Trend.
  - **Tooltip Formatting**: Injected JS callback using `Intl.NumberFormat('en-IN')` to display exact Indian currency strings on hover dynamically.
- **Empty States**: SVGs for no data.

## Verification Plan
- **Template Logic Check**: Verify `indian_currency` tag runs natively.
- **End-to-End**: Test CSV outputs to ensure the top two rows contain the Metadata before CSV ingestion starts.
