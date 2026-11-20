import os
import uuid
import zipfile

from django import forms
from django.core.exceptions import ValidationError

from .models import Document
from .utils import detect_page_count
from .validators import validate_document_file

PDF_MAGIC = b"%PDF-"
ZIP_MAGIC = b"PK\x03\x04"
MAX_PAGES = 5000


class DocumentUploadForm(forms.ModelForm):
    page_count = forms.IntegerField(
        label="Number of pages", min_value=1, max_value=MAX_PAGES, required=False,
        help_text="Detected automatically. For DOCX files, enter it only if we ask you to.",
    )

    class Meta:
        model = Document
        fields = ("file", "page_count")
        labels = {"file": "PDF or DOCX file (max 25 MB)"}
        widgets = {"file": forms.ClearableFileInput(attrs={"accept": ".pdf,.docx"})}

    original_name = ""
    file_ext = ""

    def clean_file(self):
        upload = self.cleaned_data["file"]
        validate_document_file(upload)  # BR-03: extension + 25 MB
        ext = os.path.splitext(upload.name)[1].lower()

        # Check the real content, not just the extension.
        head = upload.read(1024)
        upload.seek(0)
        if ext == ".pdf" and PDF_MAGIC not in head:
            raise ValidationError("This file is not a valid PDF.")
        if ext == ".docx":
            valid = head.startswith(ZIP_MAGIC)
            if valid:
                try:
                    with zipfile.ZipFile(upload) as archive:
                        valid = "word/document.xml" in archive.namelist()
                except zipfile.BadZipFile:
                    valid = False
                upload.seek(0)
            if not valid:
                raise ValidationError("This file is not a valid DOCX document.")

        self.original_name = os.path.basename(upload.name)[:255]
        self.file_ext = ext
        # Random stored name so file URLs cannot be guessed.
        upload.name = f"{uuid.uuid4().hex}{ext}"
        return upload

    def clean(self):
        cleaned = super().clean()
        upload = cleaned.get("file")
        if not upload or "file" in self.errors:
            return cleaned

        pages = detect_page_count(upload, self.file_ext)
        if self.file_ext == ".pdf":
            if pages is None:
                if not cleaned.get("page_count"):
                    self.add_error(
                        "page_count",
                        "We couldn't detect the page count. Please enter it.",
                    )
            else:
                cleaned["page_count"] = pages
        else:  # .docx
            if pages:
                cleaned["page_count"] = pages
            elif not cleaned.get("page_count"):
                self.add_error("page_count", "We couldn't detect the page count. Please enter it.")
        if (cleaned.get("page_count") or 0) > MAX_PAGES:
            self.add_error("file", f"Documents are limited to {MAX_PAGES} pages.")
        return cleaned
