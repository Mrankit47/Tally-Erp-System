# Phase 6: Ultra-Professional Reporting — Task List

- [ ] Core Logic & Utilities
  - [ ] Implement `apps/core/templatetags/currency_tags.py` for standard Indian Rupee formatting.
  - [ ] Update `reports/services.py` with difference-checking Trial Balance generation logic.
  - [ ] Update `reports/services.py` with P&L and `get_top_expenses()` logic.
- [ ] Views & Exports (`apps/reports/views.py` & `urls.py`)
  - [ ] Implement `trial_balance_view` and `profit_loss_view`.
  - [ ] Implement CSV export endpoints: Generates HTTP Response loaded with dynamic header rows (Generation Date, Company Name).
  - [ ] Map URLs and update `config/urls.py` correctly.
- [ ] Ultimate UX / Templates
  - [ ] Create `templates/reports/trial_balance.html`. Apply `sticky top-0` table headers, dynamic Difference Check badges, and empty-state SVGs.
  - [ ] Create `templates/reports/profit_loss.html`. Incorporate Chart.js dynamic tooltips, hovering T-shaped dual tables, Top 5 Expenses UI.
  - [ ] Update Sidebar in `base.html` for navigation & global CSS loading spinner.
- [ ] Verification
  - [ ] Test the template tag initialization.
  - [ ] Run Django system checks & validation.
