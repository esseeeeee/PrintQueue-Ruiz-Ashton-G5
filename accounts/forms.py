from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User

MAX_PHOTO_BYTES = 2 * 1024 * 1024  # 2 MB


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(
        choices=[(User.Role.STUDENT, "Student"), (User.Role.SHOP_OWNER, "Print Shop Owner")],
        initial=User.Role.STUDENT,
    )  # ADMIN accounts are created by createsuperuser / the admin site only

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "role", "phone_number")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username


class LoginForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Invalid username or password. Please try again.",
    }


class ProfileUpdateForm(forms.ModelForm):
    """Role, username and password are intentionally NOT editable here."""

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone_number", "profile_photo")
        widgets = {"profile_photo": forms.FileInput(attrs={"accept": "image/*"})}

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is used by another account.")
        return email

    def save(self, commit=True):
        old_name = None
        if self.instance.pk and "profile_photo" in self.changed_data:
            old_name = (User.objects.filter(pk=self.instance.pk)
                        .values_list("profile_photo", flat=True).first())
        user = super().save(commit)
        new_name = user.profile_photo.name if user.profile_photo else ""
        if commit and old_name and old_name != new_name:
            user.profile_photo.storage.delete(old_name)  # no orphaned files
        return user

    def clean_profile_photo(self):
        photo = self.cleaned_data.get("profile_photo")
        if photo and hasattr(photo, "size"):
            if photo.size > MAX_PHOTO_BYTES:
                raise forms.ValidationError("Photo must be 2 MB or smaller.")
            content_type = getattr(photo, "content_type", "")
            if content_type and not content_type.startswith("image/"):
                raise forms.ValidationError("Upload an image file.")
        return photo
