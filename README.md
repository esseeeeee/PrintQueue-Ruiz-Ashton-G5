# PrintQueue – Student Project Printing and Document Pickup Portal

Full-stack Django (templates) + PostgreSQL / Supabase. No SQLite.

## Project Development 1 – Account Feature
| Requirement | Implementation |
|---|---|
| Registration | Required fields, valid email, unique username + email (case-insensitive), password confirmation, Django password hashing, success/error messages |
| Login / Logout | Invalid-credential message, POST-only logout that ends the session, `@login_required` redirects anonymous users to the login page |
| Role-based dashboards | `STUDENT`, `SHOP_OWNER`, `ADMIN`; login routes each user to their own dashboard; typing another role's URL returns **403** |
| Profile | View / edit name, email, contact number and photo; always operates on `request.user`, so users can only see and edit their own profile |

Roles: students and shop owners register themselves; **ADMIN** accounts come from `createsuperuser` or the Django admin only.

The `printing` app already contains the SDD data model (`print_shops`, `print_prices`, `documents`, `print_orders`, `payments`) with the business-rule constraints BR-01 to BR-10.

## Project Development 2 – Document Upload & Print Order Queue
| Role | What they can do |
|---|---|
| Student | Upload PDF/DOCX (max 25 MB, content-checked, pages auto-detected) · delete unused documents · place an order (shop + paper size + color) with an automatic total · edit/cancel pending orders · delete pending/cancelled orders · view and filter order history |
| Shop owner | Create shops · set price rules per paper size and color · see only their own shops' orders · download files · move orders PENDING → PRINTING → READY FOR PICKUP · record cash payment (completes the order) · cancel orders · filter by status/date/search |
| Admin | Dashboard counts + Django admin |

Main URLs: `/printing/documents/`, `/printing/orders/`, `/printing/shop/shops/`, `/printing/shop/orders/`.
Business rules BR-03 to BR-10 are enforced in forms/views and by database constraints. Git workflow: see `GIT_WORKFLOW.md`.

## Project Development 3 – Hardening
No new features. The existing features were made reliable, secure and tested. Details and evidence: `docs/PrintQueue-Ruiz-Ashton-G5-PD3.pdf`.

| Area | What was done |
|---|---|
| PD2 issues | ISS-01 tests no longer ask to delete the old test database · ISS-02 profile photos work with `DEBUG=False` (served by a login-protected view; there is no public `/media/` URL) · ISS-03 tests can run on a local PostgreSQL and use a fast password hasher |
| Validation / errors | Server-side validation on every form · duplicate and bad-date filters handled · custom 404, 403, 400, 500 and CSRF pages · bad or huge IDs return 404 |
| Security | Login + role check inside every view · other users' records give 404 · POST-only actions · CSRF everywhere · no raw SQL, no `|safe` · secrets and `DEBUG` come from `.env` |
| Data integrity | Unique and check constraints (migration `0002`) · correct `on_delete` rules · `transaction.atomic()` on multi-step saves · redirect after POST + double-click protection · confirmation page before every delete · files removed from disk when a document is deleted |
| Tests | 60 automated Django tests (`python manage.py test`), including invalid input, duplicate submissions, access control, and confirmation flows |

## Running the tests
```bash
python manage.py test            # all tests (never asks questions)
python manage.py test printing   # only the core feature
python manage.py test accounts   # only the account features
```
Tests use a separate PostgreSQL database (`printqueue_test`), so your real data is safe.
The test runner keeps and reuses this database between runs, avoiding cleanup errors when a PostgreSQL session is still connected.
Running on Supabase is slow. To run the tests on a **local PostgreSQL** instead, add these to your `.env` (see `.env.example`):
```
TEST_DB_HOST=localhost
TEST_DB_PASSWORD=<your local postgres password>
```

## Setup
```bash
git clone https://github.com/<your-username>/<your-repo-name>.git
cd <your-repo-name>
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env           # macOS/Linux: cp .env.example .env
# edit .env: SECRET_KEY + your Supabase (Session pooler) or local PostgreSQL values
# Keep DEBUG=False outside local development; DEBUG=True enables detailed error pages.
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Notes
- `.env`, `venv/` and `__pycache__/` are git-ignored. Never commit real credentials.
- After changing a model, run `python manage.py makemigrations` and commit the new migration file.
