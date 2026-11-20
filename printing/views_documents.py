import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, ProtectedError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User

from .forms_documents import DocumentUploadForm
from .models import Document
from .workflow import SHOP_VISIBLE_DOWNLOAD

STUDENT = User.Role.STUDENT


@role_required(STUDENT)
def document_list(request):
    documents = (
        Document.objects.for_student(request.user)  # BR-07
        .annotate(order_count=Count("orders"))
        .order_by("-uploaded_at")
    )
    return render(request, "printing/documents/list.html", {"documents": documents})


@role_required(STUDENT)
def document_upload(request):
    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.user = request.user
            document.file_name = form.original_name
            document.save()
            messages.success(
                request,
                f"“{document.file_name}” uploaded successfully ({document.page_count} pages).",
            )
            return redirect("printing:document_list")
        messages.error(request, "Upload failed. Please fix the errors below.")
    else:
        form = DocumentUploadForm()
    return render(request, "printing/documents/upload.html", {"form": form})


@role_required(STUDENT)
@require_POST
def document_delete(request, pk):
    document = get_object_or_404(Document.objects.for_student(request.user), pk=pk)
    if document.orders.exists():  # BR-09
        messages.error(request, "This document is used by an order, so it can't be deleted.")
        return redirect("printing:document_list")

    name, storage, stored_name = document.file_name, document.file.storage, document.file.name
    try:
        with transaction.atomic():
            document.delete()
    except ProtectedError:
        messages.error(request, "This document is used by an order, so it can't be deleted.")
        return redirect("printing:document_list")
    storage.delete(stored_name)
    messages.success(request, f"“{name}” was deleted.")
    return redirect("printing:document_list")


@login_required
def document_download(request, pk):
    """Students: their own files. Shop owners: files of non-cancelled orders sent to their shops."""
    user = request.user
    if user.is_student:
        queryset = Document.objects.for_student(user).filter(pk=pk)
    elif user.is_shop_owner:
        queryset = Document.objects.filter(
            pk=pk, orders__shop__owner=user, orders__status__in=SHOP_VISIBLE_DOWNLOAD)
    else:
        raise Http404
    document = queryset.distinct().first()
    if document is None:
        raise Http404
    try:
        handle = document.file.open("rb")
    except (FileNotFoundError, ValueError):
        raise Http404("The file is missing from storage.")
    filename = document.file_name or os.path.basename(document.file.name)
    return FileResponse(handle, as_attachment=True, filename=filename)
