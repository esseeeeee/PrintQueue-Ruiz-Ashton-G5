from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User

from .forms_orders import OrderFilterForm, PaymentForm
from .models import Payment, PrintOrder
from .views_orders import apply_order_filters, paginate, warn_if_bad_filter
from .workflow import allowed_next, next_actions

OWNER = User.Role.SHOP_OWNER
READY = PrintOrder.Status.READY.value
COMPLETED = PrintOrder.Status.COMPLETED.value


def _owner_orders(user):
    return PrintOrder.objects.for_shop_owner(user)  # BR-08


@role_required(OWNER)
def shop_order_list(request):
    base = _owner_orders(request.user)
    counts = base.aggregate(
        pending=Count("pk", filter=Q(status="PENDING")),
        printing=Count("pk", filter=Q(status="PRINTING")),
        ready=Count("pk", filter=Q(status="READY FOR PICKUP")),
    )
    form = OrderFilterForm(request.GET or None)
    warn_if_bad_filter(request, form)
    orders = base.select_related("user", "shop", "document", "price").order_by("-order_date")
    page_obj, querystring = paginate(request, apply_order_filters(orders, form, for_owner=True))
    return render(request, "printing/queue/list.html", {
        "page_obj": page_obj, "querystring": querystring, "filter_form": form, "counts": counts})


@role_required(OWNER)
def shop_order_detail(request, pk):
    order = get_object_or_404(
        _owner_orders(request.user).select_related("user", "shop", "document", "price"), pk=pk)
    return render(request, "printing/queue/detail.html", {
        "order": order,
        "actions": next_actions(order.status),
        "payment": Payment.objects.filter(order=order).first(),
        "payment_form": PaymentForm(initial={"amount_paid": order.total_amount}),
        "can_download": order.status != PrintOrder.Status.CANCELLED.value,
    })


@role_required(OWNER)
@require_POST
def shop_order_status(request, pk):
    new_status = request.POST.get("status", "")
    with transaction.atomic():
        order = get_object_or_404(
            _owner_orders(request.user).select_for_update(of=("self",)), pk=pk)
        if new_status not in allowed_next(order.status):
            messages.error(request, f"Order #{order.order_id} can't move from {order.status} to {new_status or '—'}.")
        else:
            order.status = new_status
            order.save(update_fields=["status"])
            messages.success(request, f"Order #{order.order_id} is now {order.get_status_display()}.")
    if request.POST.get("from") == "list":
        return redirect("printing:shop_order_list")
    return redirect("printing:shop_order_detail", pk=pk)


@role_required(OWNER)
@require_POST
def shop_order_payment(request, pk):
    """F-07 / BR-10: record cash only for READY FOR PICKUP orders, then complete the order."""
    with transaction.atomic():
        order = get_object_or_404(
            _owner_orders(request.user).select_for_update(of=("self",)), pk=pk)
        form = PaymentForm(request.POST)
        if order.status != READY:
            messages.error(request, "Cash can only be recorded when the order is Ready for pickup.")
        elif Payment.objects.filter(order=order).exists():
            messages.error(request, "A payment was already recorded for this order.")
        elif not form.is_valid():
            messages.error(request, "Enter a valid cash amount.")
        elif form.cleaned_data["amount_paid"] < order.total_amount:
            messages.error(request, f"Cash received is less than the total (₱{order.total_amount}).")
        else:
            try:
                Payment.objects.create(
                    order=order, amount_paid=form.cleaned_data["amount_paid"], collected_by=request.user)
            except ValidationError as error:
                messages.error(request, " ".join(error.messages))
            else:
                order.status = COMPLETED
                order.save(update_fields=["status"])
                messages.success(request, f"Payment recorded. Order #{order.order_id} is completed.")
    return redirect("printing:shop_order_detail", pk=pk)
