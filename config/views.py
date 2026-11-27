from django.shortcuts import render


def csrf_failure(request, reason=""):
    """Shown when a form is sent without a valid CSRF token."""
    return render(request, "csrf_failure.html", status=403)
