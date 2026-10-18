# Sofia Sweet Moments — admin orders

This package adds a password-protected admin panel at `/admin/login` and an order submission endpoint at `/api/orders`.

Required Render environment variables:
- `ADMIN_USER` — admin login (for example `sofia`)
- `ADMIN_PASSWORD` — a strong unique admin password; store only in Render Environment, never in GitHub
- `FLASK_SECRET_KEY` — long random secret

Important: the current example stores orders in SQLite under `/tmp`. Render's temporary filesystem can be cleared after restart/redeploy, so this version is for testing only. Before accepting real orders, connect persistent storage (a persistent disk or external PostgreSQL database).
