import mimetypes

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render

from .decorators import role_required
from .forms import LoginForm, ProfileUpdateForm, RegistrationForm
from printing.models import Document, PrintOrder, PrintShop

from .models import User


def register_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()  # password is hashed by UserCreationForm
            messages.success(request, "Account created successfully! You can now log in.")
            return redirect("accounts:login")
        messages.error(request, "Please fix the errors below.")
    else:
        form = RegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


class PrintQueueLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        name = self.request.user.first_name or self.request.user.username
        messages.success(self.request, f"Welcome back, {name}!")
        return response


class PrintQueueLogoutView(LogoutView):
    """POST-only logout (Django 5) that also confirms to the user."""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.success(request, "You have been logged out.")
        return response


@login_required
def dashboard_redirect(request):
    """Post-login router: sends each user to the dashboard of their role."""
    return redirect(request.user.get_dashboard_url_name())


@role_required(User.Role.STUDENT)
def student_dashboard(request):
    orders = (
        PrintOrder.objects.for_student(request.user)  # BR-07
        .select_related("shop", "document")
        .order_by("-order_date")[:10]
    )
    return render(request, "student/dashboard.html", {"orders": orders})


@role_required(User.Role.SHOP_OWNER)
def shop_dashboard(request):
    orders = (
        PrintOrder.objects.for_shop_owner(request.user)  # BR-08
        .select_related("user", "document", "shop")
        .order_by("-order_date")[:20]
    )
    shops = PrintShop.objects.filter(owner=request.user)
    return render(request, "shop/dashboard.html", {"orders": orders, "shops": shops})


@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    context = {
        "student_count": User.objects.filter(role=User.Role.STUDENT).count(),
        "owner_count": User.objects.filter(role=User.Role.SHOP_OWNER).count(),
        "shop_count": PrintShop.objects.count(),
        "order_count": PrintOrder.objects.count(),
        "document_count": Document.objects.count(),
    }
    return render(request, "administrator/dashboard.html", context)


@login_required
def profile_view(request):
    # Always request.user -> nobody can open another user's profile by URL.
    return render(request, "accounts/profile.html", {"profile_user": request.user})


@login_required
def profile_edit(request):
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:profile")
        messages.error(request, "Please fix the errors below.")
    else:
        form = ProfileUpdateForm(instance=request.user)
    return render(request, "accounts/profile_edit.html", {"form": form})


@login_required
def profile_photo(request):
    """Sends the signed-in user's OWN photo. Works with DEBUG=False (fixes PD2 ISS-02)."""
    photo = request.user.profile_photo
    if not photo:
        raise Http404("No profile photo.")
    try:
        handle = photo.open("rb")
    except (FileNotFoundError, ValueError):
        raise Http404("Photo file is missing.")
    content_type = mimetypes.guess_type(photo.name)[0] or "application/octet-stream"
    response = FileResponse(handle, content_type=content_type)
    response["Cache-Control"] = "private, no-cache"
    return response
