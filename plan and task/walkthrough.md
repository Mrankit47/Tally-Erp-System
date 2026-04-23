# Production Security & PostgreSQL Upgrade — Walkthrough

The ERP system has been upgraded to production-grade standards, focusing on data integrity, environment security, and Role-Based Access Control (RBAC).

---

## 🚀 Key Improvements

### 1. PostgreSQL & Environmental Security
- **Database Engine Change**: The project is now configured to use **PostgreSQL** (Supabase compatible) via `psycopg2-binary`.
- **Environment Decoupling**: All sensitive credentials (keys, DB passwords, Tally URLs) have been moved to environment variables.
- **`.env.example`**: Created a template for the required secrets.
- **Migration Guide**: Documentation provided for safely moving from SQLite to PostgreSQL without data loss.

### 2. Role-Based Access Control (RBAC)
- **Security Groups**: Created a management command to auto-generate three core roles:
  - `Admin`: Full system access.
  - `Accountant`: Access to sync, reports, and financial data.
  - `User`: Restricted access (Dashboard viewing only).
- **`@role_required` Decorator**: A custom backend guard that isolates financial views. Only Admins and Accountants can now trigger Tally syncs or view Profit & Loss/Trial Balance reports.

### 3. Advanced Logging & Monitoring
- **Decoupled Logs**: Security alerts and request errors are now sent to specialized audit files:
  - `logs/security.log`: Tracks failed auth attempts and permission denials.
  - `logs/error.log`: Captures application-level crashes and 500 errors.

### 4. Accounting Integrity (Hardened Models)
- **Strict Voucher Balancing**: The `Voucher.clean()` method was refactored. The system now strictly blocks any attempt to "Post" a voucher that isn't mathematically balanced (Total Debit must equal Total Credit).
- **CSRF Protection**: Verified that all AJAX-based sync actions use `fetchWithCSRF`, securing the system against cross-site request forgery.

---

## 🛠️ Verification & Next Steps

1. **Initialize Production Roles**:
   Run `python manage.py setup_roles` to create the default Admin and Accountant groups in your new database.
2. **Assign Users**:
   Assign your staff users to the appropriate groups in the Django Admin to enable their permissions.
3. **Follow the Migration Guide**:
   Refer to `migrate_db.md` when you are ready to switch your live data from SQLite to Supabase.
