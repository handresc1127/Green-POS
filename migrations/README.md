Migration files for Green-POS

This directory contains migration helper scripts and SQL used to modify the SQLite schema.

How to run the sample migration (Windows / project root):

```powershell
# run from project root
python migrations/migration_add_inventory_flag.py
```

What it does:
- Adds `is_inventory` BOOLEAN DEFAULT 0 to `product_stock_log`.
- Creates index `idx_stock_log_inventory` on `product_stock_log(is_inventory, created_at)`.

Notes:
- The migration script looks for `migration_add_inventory_flag.sql` in the same folder as the script. If you run the script from the project root (e.g. `python migrations/migration_add_inventory_flag.py`) the script will still find and execute the SQL because it now resolves the SQL file relative to the script file.
- If you prefer the script to execute built-in fallback SQL, it will run built-in statements when the .sql file is missing.
- Always backup `instance/app.db` before running migrations in production.
