from django.test import TestCase
from django.urls import reverse

from .models import User


class AccountFeatureTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            "stud", "stud@x.com", "Pass12345!x", role=User.Role.STUDENT)
        self.owner = User.objects.create_user(
            "owner", "owner@x.com", "Pass12345!x", role=User.Role.SHOP_OWNER)

    def test_admin_dashboard_role_only(self):
        admin = User.objects.create_user("adm", "adm@x.com", "Pass12345!x", role=User.Role.ADMIN)
        self.client.login(username="stud", password="Pass12345!x")
        self.assertEqual(self.client.get(reverse("accounts:admin_dashboard")).status_code, 403)
        self.client.login(username="adm", password="Pass12345!x")
        self.assertEqual(self.client.get(reverse("accounts:admin_dashboard")).status_code, 200)

    def test_cannot_register_as_admin(self):
        self.client.post(reverse("accounts:register"), {
            "username": "sneaky", "first_name": "A", "last_name": "B", "email": "s@x.com",
            "role": "ADMIN", "password1": "Strong!Pass123", "password2": "Strong!Pass123"})
        self.assertFalse(User.objects.filter(username="sneaky").exists())

    def test_anonymous_redirected_to_login(self):
        r = self.client.get(reverse("accounts:student_dashboard"))
        self.assertRedirects(r, f"{reverse('accounts:login')}?next={reverse('accounts:student_dashboard')}")

    def test_login_routes_by_role(self):
        self.client.login(username="owner", password="Pass12345!x")
        r = self.client.get(reverse("accounts:dashboard"))
        self.assertRedirects(r, reverse("accounts:shop_dashboard"))

    def test_student_cannot_open_shop_dashboard(self):
        self.client.login(username="stud", password="Pass12345!x")
        self.assertEqual(self.client.get(reverse("accounts:shop_dashboard")).status_code, 403)

    def test_owner_cannot_open_student_dashboard(self):
        self.client.login(username="owner", password="Pass12345!x")
        self.assertEqual(self.client.get(reverse("accounts:student_dashboard")).status_code, 403)

    def test_register_password_mismatch(self):
        r = self.client.post(reverse("accounts:register"), {
            "username": "new", "first_name": "A", "last_name": "B", "email": "n@x.com",
            "role": "STUDENT", "password1": "Strong!Pass123", "password2": "different"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="new").exists())

    def test_register_duplicate_email(self):
        r = self.client.post(reverse("accounts:register"), {
            "username": "new", "first_name": "A", "last_name": "B", "email": "STUD@x.com",
            "role": "STUDENT", "password1": "Strong!Pass123", "password2": "Strong!Pass123"})
        self.assertFalse(User.objects.filter(username="new").exists())

    def test_password_is_hashed(self):
        self.assertNotEqual(self.student.password, "Pass12345!x")
        self.assertIn("$", self.student.password)            # "algorithm$salt$hash" format
        self.assertTrue(self.student.check_password("Pass12345!x"))

    def test_logout_requires_post_and_ends_session(self):
        self.client.login(username="stud", password="Pass12345!x")
        self.client.post(reverse("accounts:logout"))
        r = self.client.get(reverse("accounts:profile"))
        self.assertEqual(r.status_code, 302)

    def test_profile_edit_only_affects_self(self):
        self.client.login(username="stud", password="Pass12345!x")
        self.client.post(reverse("accounts:profile_edit"), {
            "first_name": "New", "last_name": "Name", "email": "stud@x.com", "phone_number": "09171234567"})
        self.student.refresh_from_db(); self.owner.refresh_from_db()
        self.assertEqual(self.student.first_name, "New")
        self.assertEqual(self.owner.first_name, "")
