from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User

from .forms_orders import OrderFilterForm, OrderForm
from .models import Document, PrintOrder, PrintPrice
from .workflow import STUDENT_DELETABLE, STUDENT_EDITABLE

STUDENT = User.Role.STUDENT
PENDING = PrintOrder.Status.PENDING.value
CANCELLED = PrintOrder.Status.CANCELLED.value


def apply_order_filters(queryset, form, *, for_owner=False):
    """F-08: search/filter by status, date range, text."""
    if not form.is_valid():
        return queryset
    data = form.cleaned_data
    if data.get("status"):
        queryset = queryset.filter(status=data["status"])
    if data.get("date_from"):
        queryset = queryset.filter(order_date__date__gte=data["date_from"])
    if data.get("date_to"):
        queryset = queryset.filter(order_date__date__lte=data["date_to"])
    if data.get("q"):
        q = data["q"]
        text = Q(document__file_name__icontains=q)
        if for_owner:
            text |= Q(user__username__icontains=q) | Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q)
        else:
            text |= Q(shop__name__icontains=q)
        queryset = queryset.filter(text)
    return queryset


def paginate(request, queryset, per_page=10):
    page_obj = Paginator(queryset, per_page).get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)
    return page_obj, query.urlencode()


@role_required(STUDENT)
def order_list(request):
    form = OrderFilterForm(request.GET or None)
    orders = (
        PrintOrder.objects.for_student(request.user)  # BR-07
        .select_related("shop", "document", "price").order_by("-order_date")
    )
    page_obj, querystring = paginate(request, apply_order_filters(orders, form))
    return render(request, "printing/orders/list.html", {
        "page_obj": page_obj, "querystring": querystring, "filter_form": form})


@role_required(STUDENT)
def order_create(request):
    user = request.user
    if not Document.objects.for_student(user).exists():
        messages.info(request, "Upload a document first, then you can order prints.")
        return redirect("printing:document_upload")

    if request.method == "POST":
        form = OrderForm(request.POST, user=user)
        if form.is_valid():
            order = form.save()  # total_amount is computed in PrintOrder.save()
            messages.success(
                request, f"Order #{order.order_id} placed at {order.shop.name}. Total: ₱{order.total_amount}.")
            return redirect("printing:order_detail", pk=order.pk)
        messages.error(request, "We couldn't place the order. Please fix the errors below.")
    else:
        form = OrderForm(user=user, initial={"document": request.GET.get("document") or None})
    if not form.fields["price"].queryset.exists():
        messages.warning(request, "No open shop has set its prices yet.")
    return render(request, "printing/orders/form.html", _form_context(form, "Place a print order"))


def _form_context(form, title):
    return {
        "form": form,
        "title": title,
        "pages_map": {d.pk: d.page_count for d in form.fields["document"].queryset},
        "rates_map": {p.pk: str(p.price_per_page) for p in form.fields["price"].queryset},
    }


@role_required(STUDENT)
def order_detail(request, pk):
    order = get_object_or_404(
        PrintOrder.objects.for_student(request.user).select_related("shop", "document", "price"), pk=pk)
    return render(request, "printing/orders/detail.html", {
        "order": order,
        "can_edit": order.status in STUDENT_EDITABLE,
        "can_delete": order.status in STUDENT_DELETABLE,
    })


@role_required(STUDENT)
def order_edit(request, pk):
    user = request.user
    order = get_object_or_404(PrintOrder.objects.for_student(user), pk=pk)
    if order.status not in STUDENT_EDITABLE:
        messages.error(request, "Only pending orders can be edited.")
        return redirect("printing:order_detail", pk=pk)

    if request.method == "POST":
        with transaction.atomic():
            locked = get_object_or_404(
                PrintOrder.objects.for_student(user).select_for_update(of=("self",)), pk=pk)
            if locked.status not in STUDENT_EDITABLE:
                messages.error(request, "The shop already started this order, so it can't be edited.")
                return redirect("printing:order_detail", pk=pk)
            form = OrderForm(request.POST, instance=locked, user=user)
            if form.is_valid():
                updated = form.save(commit=False)
                updated.total_amount = updated.compute_total()  # recompute automatically
                updated.save()
                messages.success(request, f"Order #{updated.order_id} updated. New total: ₱{updated.total_amount}.")
                return redirect("printing:order_detail", pk=pk)
        messages.error(request, "Please fix the errors below.")
    else:
        form = OrderForm(instance=order, user=user)
    return render(request, "printing/orders/form.html", _form_context(form, f"Edit order #{order.order_id}"))


@role_required(STUDENT)
@require_POST
def order_cancel(request, pk):
    with transaction.atomic():
        order = get_object_or_404(
            PrintOrder.objects.for_student(request.user).select_for_update(of=("self",)), pk=pk)
        if order.status != PENDING:
            messages.error(request, "Only pending orders can be cancelled.")
        else:
            order.status = CANCELLED
            order.save(update_fields=["status"])
            messages.success(request, f"Order #{order.order_id} was cancelled.")
    return redirect("printing:order_detail", pk=pk)


@role_required(STUDENT)
@require_POST
def order_delete(request, pk):
    with transaction.atomic():
        order = get_object_or_404(
            PrintOrder.objects.for_student(request.user).select_for_update(of=("self",)), pk=pk)
        if order.status not in STUDENT_DELETABLE:
            messages.error(request, "Only pending or cancelled orders can be deleted.")
            return redirect("printing:order_detail", pk=pk)
        number = order.order_id
        order.delete()
    messages.success(request, f"Order #{number} was deleted.")
    return redirect("printing:order_list")
