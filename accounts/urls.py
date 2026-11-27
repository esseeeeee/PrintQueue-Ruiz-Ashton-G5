from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("login/", views.PrintQueueLoginView.as_view(), name="login"),
    path("logout/", views.PrintQueueLogoutView.as_view(), name="logout"),  # POST only (Django 5)
    path("dashboard/", views.dashboard_redirect, name="dashboard"),
    path("student/dashboard/", views.student_dashboard, name="student_dashboard"),
    path("shop/dashboard/", views.shop_dashboard, name="shop_dashboard"),
    path("administrator/dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/photo/", views.profile_photo, name="profile_photo"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
]
