from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q

phone_validator = RegexValidator(
    regex=r"^\+?[0-9\s\-]{7,15}$",
    message="Enter a valid contact number (7-15 digits, may start with +).",
)


class User(AbstractUser):
    """SDD table: users. Must exist BEFORE the first migrate."""

    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        SHOP_OWNER = "SHOP_OWNER", "Print Shop Owner"
        ADMIN = "ADMIN", "Administrator"

    user_id = models.AutoField(primary_key=True)
    email = models.EmailField("email address", unique=True)          # BR-01
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    phone_number = models.CharField(max_length=20, blank=True, validators=[phone_validator])
    profile_photo = models.ImageField(upload_to="profile_photos/", blank=True, null=True)

    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "users"
        constraints = [
            # BR-02
            models.CheckConstraint(
                condition=Q(role__in=["STUDENT", "SHOP_OWNER", "ADMIN"]),
                name="users_role_valid",
            ),
        ]

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_shop_owner(self):
        return self.role == self.Role.SHOP_OWNER

    @property
    def is_platform_admin(self):
        return self.role == self.Role.ADMIN

    def get_dashboard_url_name(self):
        return {
            self.Role.SHOP_OWNER: "accounts:shop_dashboard",
            self.Role.ADMIN: "accounts:admin_dashboard",
        }.get(self.role, "accounts:student_dashboard")

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()  # BR-01: no duplicates that differ only by letter case
        if self.is_superuser:  # createsuperuser -> Administrator role
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
