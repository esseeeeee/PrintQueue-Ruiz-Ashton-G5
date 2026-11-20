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

## Setup
```bash
git clone https://github.com/<your-username>/<your-repo-name>.git
cd <your-repo-name>
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env           # macOS/Linux: cp .env.example .env
# edit .env: SECRET_KEY + your Supabase (Session pooler) or local PostgreSQL values
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
Run the tests: `python manage.py test`

## Notes
- `.env`, `venv/` and `__pycache__/` are git-ignored. Never commit real credentials.
- After changing a model, run `python manage.py makemigrations` and commit the new migration file.
