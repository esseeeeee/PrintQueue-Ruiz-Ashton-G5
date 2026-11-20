# Git workflow for PD2 (PrintQueue-Ruiz-Ashton-G5)

Rules: `main` = stable only (turn on branch protection: "Require a pull request before merging").
Never delete the feature branches after merging.

## 0. Create `develop` and a scaffolding commit
```bash
git checkout main && git pull
git checkout -b develop
git push -u origin develop
```
Copy the project files in, then in `printing/urls.py` **comment out both `include(...)` lines** and commit only the shared files:
```bash
git add requirements.txt README.md GIT_WORKFLOW.md config/urls.py templates/base.html \
        templates/printing/base_printing.html templates/printing/_pagination.html \
        templates/printing/_order_filter.html static/css/printing.css printing/urls.py
git commit -m "chore: scaffold printing app wiring, shared templates and styles"
git push
```
## 1. Branch `feature/document-upload-pricing`
```bash
git checkout develop && git checkout -b feature/document-upload-pricing
```
Uncomment the **first** include (`printing.urls_setup`) in `printing/urls.py`, then:
```bash
git add printing/utils.py printing/forms_documents.py printing/views_documents.py \
        templates/printing/documents printing/urls_setup.py printing/urls.py
git commit -m "feat(documents): PDF/DOCX upload with 25MB + content validation and page detection"
git add printing/forms_pricing.py printing/views_pricing.py templates/printing/pricing \
        printing/test_documents_pricing.py
git commit -m "feat(pricing): shop and price-rule CRUD with ownership checks"
git push -u origin feature/document-upload-pricing
```
GitHub -> **New pull request**: base `develop` <- compare `feature/document-upload-pricing`. Merge it (do NOT tick "delete branch").

## 2. Branch `feature/print-order-queue`
```bash
git checkout develop && git pull
git checkout -b feature/print-order-queue
```
Uncomment the **second** include (`printing.urls_orders`), then:
```bash
git add printing/workflow.py printing/forms_orders.py printing/views_orders.py \
        templates/printing/orders printing/urls_orders.py printing/urls.py \
        templates/student/dashboard.html templates/shop/dashboard.html
git commit -m "feat(orders): student order create/edit/cancel/delete with automatic price calculation"
git add printing/views_queue.py templates/printing/queue printing/test_orders_queue.py
git commit -m "feat(queue): shop owner order queue, status workflow and cash payment"
git push -u origin feature/print-order-queue
```
Open a PR into `develop` and merge it (keep the branch).

## 3. Report + final PR
```bash
git checkout develop && git pull
mkdir -p docs && cp /path/to/PrintQueue-Ruiz-Ashton-G5-PD2.pdf docs/
git add docs/PrintQueue-Ruiz-Ashton-G5-PD2.pdf README.md
git commit -m "docs: add PD2 completion report and update README"
git push
```
GitHub -> PR: base `main` <- compare `develop`, title "Release: PD2 core feature (document upload + print order queue)". Merge it.

## Before every push
`git status` must NOT list `.env`, `venv/` or `__pycache__/`.
