from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Count, ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.decorators import role_required
from accounts.models import User

from .confirm import render_confirm
from .forms_pricing import PriceForm, ShopForm
from .models import PrintPrice, PrintShop

OWNER = User.Role.SHOP_OWNER
DUPLICATE_SHOP = "You already have a shop with this name."
DUPLICATE_PRICE = "This shop already has a price for that paper size and color."


@role_required(OWNER)
def shop_list(request):
    shops = (
        PrintShop.objects.filter(owner=request.user)  # only my shops
        .prefetch_related("prices")
        .annotate(order_count=Count("orders"))
        .order_by("name")
    )
    return render(request, "printing/pricing/shop_list.html", {"shops": shops})


def _save_shop(request, form, success_message):
    """Saves the shop; returns True on success. A race with another request is shown as a form error."""
    try:
        with transaction.atomic():
            shop = form.save(commit=False)
            shop.owner = request.user
            shop.save()
    except IntegrityError:
        form.add_error("name", DUPLICATE_SHOP)
        return False
    messages.success(request, success_message % shop.name)
    return True


@role_required(OWNER)
def shop_create(request):
    form = ShopForm(request.POST or None, owner=request.user)
    if request.method == "POST":
        if form.is_valid() and _save_shop(request, form, "“%s” was created. Now add your price rules."):
            return redirect("printing:shop_list")
        messages.error(request, "Please fix the errors below.")
    return render(request, "printing/pricing/shop_form.html", {"form": form, "title": "Add a print shop"})


@role_required(OWNER)
def shop_edit(request, pk):
    shop = get_object_or_404(PrintShop, pk=pk, owner=request.user)
    form = ShopForm(request.POST or None, instance=shop, owner=request.user)
    if request.method == "POST":
        if form.is_valid() and _save_shop(request, form, "“%s” was updated."):
            return redirect("printing:shop_list")
        messages.error(request, "Please fix the errors below.")
    return render(request, "printing/pricing/shop_form.html", {"form": form, "title": f"Edit {shop.name}"})


@role_required(OWNER)
@require_http_methods(["GET", "POST"])
def shop_delete(request, pk):
    shop = get_object_or_404(PrintShop, pk=pk, owner=request.user)
    if shop.orders.exists():
        messages.error(request, "This shop has orders and can't be deleted. Mark it closed instead.")
        return redirect("printing:shop_list")
    if request.method == "GET":
        return render_confirm(
            request, title="Delete this shop?",
            message=f"“{shop.name}” and all of its price rules will be deleted. This cannot be undone.",
            action_url=request.path, cancel_url="/printing/shop/shops/")
    try:
        with transaction.atomic():
            shop.delete()
    except ProtectedError:
        messages.error(request, "This shop has orders and can't be deleted. Mark it closed instead.")
    else:
        messages.success(request, "Shop deleted.")
    return redirect("printing:shop_list")


def _save_price(request, form, success_message):
    try:
        with transaction.atomic():
            form.save()
    except IntegrityError:
        form.add_error(None, DUPLICATE_PRICE)
        return False
    messages.success(request, success_message)
    return True


@role_required(OWNER)
def price_create(request, shop_pk):
    shop = get_object_or_404(PrintShop, pk=shop_pk, owner=request.user)
    form = PriceForm(request.POST or None, shop=shop)
    if request.method == "POST":
        if form.is_valid() and _save_price(request, form, "Price rule added."):
            return redirect("printing:shop_list")
        messages.error(request, "Please fix the errors below.")
    return render(request, "printing/pricing/price_form.html", {"form": form, "shop": shop, "title": "Add a price rule"})


@role_required(OWNER)
def price_edit(request, pk):
    price = get_object_or_404(PrintPrice.objects.select_related("shop"), pk=pk, shop__owner=request.user)
    form = PriceForm(request.POST or None, instance=price, shop=price.shop)
    if request.method == "POST":
        ok = form.is_valid() and _save_price(
            request, form, "Price rule updated. Existing orders keep the total they were placed with.")
        if ok:
            return redirect("printing:shop_list")
        messages.error(request, "Please fix the errors below.")
    return render(request, "printing/pricing/price_form.html", {"form": form, "shop": price.shop, "title": "Edit price rule"})


@role_required(OWNER)
@require_http_methods(["GET", "POST"])
def price_delete(request, pk):
    price = get_object_or_404(PrintPrice.objects.select_related("shop"), pk=pk, shop__owner=request.user)
    if price.orders.exists():
        messages.error(request, "This price rule is used by existing orders and can't be deleted.")
        return redirect("printing:shop_list")
    if request.method == "GET":
        return render_confirm(
            request, title="Delete this price rule?",
            message=f"{price.shop.name}: {price.paper_size}, {price.color_option} (₱{price.price_per_page}/page) will be deleted.",
            action_url=request.path, cancel_url="/printing/shop/shops/")
    try:
        with transaction.atomic():
            price.delete()
    except ProtectedError:
        messages.error(request, "This price rule is used by existing orders and can't be deleted.")
    else:
        messages.success(request, "Price rule deleted.")
    return redirect("printing:shop_list")
