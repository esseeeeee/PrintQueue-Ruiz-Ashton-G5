from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

# Uploaded files are NOT served from a public /media/ URL.
# Documents and profile photos are sent only by permission-checked views.
urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("printing/", include("printing.urls")),
    path("", RedirectView.as_view(pattern_name="accounts:dashboard", permanent=False)),
]

# Custom error pages live in templates/404.html, 403.html, 400.html and 500.html.