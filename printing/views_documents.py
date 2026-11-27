import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, ProtectedError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.decorators import role_required
from accounts.models import User

from .confirm import render_confirm
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
            with transaction.atomic():
                document = form.save(commit=False)
                document.user = request.user
                document.file_name = form.original_name
                document.save()
            messages.success(
                request,
                f"“{document.file_name}” uploaded successfully ({document.page_count} pages).",
            )
            return redirect("printing:document_list")  # redirect after POST: no duplicate uploads
        messages.error(request, "Upload failed. Please fix the errors below.")
    else:
        form = DocumentUploadForm()
    return render(request, "printing/documents/upload.html", {"form": form})


@role_required(STUDENT)
@require_http_methods(["GET", "POST"])
def document_delete(request, pk):
    """GET = 'Are you sure?' page (changes nothing). POST = delete."""
    document = get_object_or_404(Document.objects.for_student(request.user), pk=pk)
    if document.orders.exists():  # BR-09
        messages.error(request, "This document is used by an order, so it can't be deleted.")
        return redirect("printing:document_list")

    if request.method == "GET":
        return render_confirm(
            request, title="Delete this document?",
            message=f"“{document.file_name}” will be deleted permanently. This cannot be undone.",
            action_url=request.path, cancel_url="/printing/documents/")

    name = document.file_name
    try:
        with transaction.atomic():
            document.delete()  # the file on disk is removed by a signal (printing/signals.py)
    except ProtectedError:
        messages.error(request, "This document is used by an order, so it can't be deleted.")
        return redirect("printing:document_list")
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
