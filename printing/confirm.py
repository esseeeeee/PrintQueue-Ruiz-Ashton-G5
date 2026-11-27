from django.shortcuts import render


def render_confirm(request, *, title, message, action_url, cancel_url, confirm_label="Yes, delete"):
    """Server-side 'Are you sure?' page. The real action only happens when the form is POSTed."""
    return render(request, "printing/confirm.html", {
        "title": title, "message": message, "action_url": action_url,
        "cancel_url": cancel_url, "confirm_label": confirm_label})
