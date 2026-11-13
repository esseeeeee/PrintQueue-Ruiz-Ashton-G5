import os

from django.core.exceptions import ValidationError

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def validate_document_file(uploaded):
    """BR-03: PDF or DOCX only, 25 MB maximum."""
    ext = os.path.splitext(uploaded.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError("Only PDF and DOCX files are allowed.")
    if uploaded.size > MAX_UPLOAD_BYTES:
        raise ValidationError("File must be 25 MB or smaller.")
