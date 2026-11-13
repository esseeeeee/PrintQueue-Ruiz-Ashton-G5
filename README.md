# PrintQueue – Phase 1 (Account Feature)

## Data model (SDD Section 4)
`accounts.User` -> `users`; `printing` app -> `print_shops`, `print_prices`, `documents`,
`print_orders`, `payments`, with CHECK / UNIQUE / PROTECT rules for BR-01 to BR-10.
Roles: STUDENT, SHOP_OWNER, ADMIN (superusers are ADMIN automatically).

## Setup
```bash
python -m venv venv
venv\Scripts\activate          # Windows   (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env         # then fill in SECRET_KEY + Supabase DB values
python manage.py makemigrations accounts printing
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
Run tests: `python manage.py test`

## Git
```bash
git init
git add .
git commit -m "Phase 1: account feature"
git branch -M main
git remote add origin https://github.com/<your-username>/PrintQueue-Ruiz-Ashton-G3.git
git push -u origin main
```
