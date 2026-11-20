from django.contrib import messages
from django.db import transaction
from django.db.models import Count, ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User

from .forms_pricing import PriceForm, ShopForm
from .models import PrintPrice, PrintShop

OWNER = User.Role.SHOP_OWNER


@role_required(OWNER)
def shop_list(request):
    shops = (
        PrintShop.objects.filter(owner=request.user)  # only my shops
        .prefetch_related("prices")
        .annotate(order_count=Count("orders"))
        .order_by("name")
    )
    return render(request, "printing/pricing/shop_list.html", {"shops": shops})


@role_required(OWNER)
def shop_create(request):
    form = ShopForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        shop = form.save(commit=False)
        shop.owner = request.user
        shop.save()
        messages.success(request, f"“{shop.name}” was created. Now add your price rules.")
        return redirect("printing:shop_list")
    if request.method == "POST":
        messages.error(request, "Please fix the errors below.")
    return render(request, "printing/pricing/shop_form.html", {"form": form, "title": "Add a print shop"})


@role_required(OWNER)
def shop_edit(request, pk):
    shop = get_object_or_404(PrintShop, pk=pk, owner=request.user)
    form = ShopForm(request.POST or None, instance=shop)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Shop updated.")
        return redirect("printing:shop_list")
    if request.method == "POST":
        messages.error(request, "Please fix the errors below.")
    return render(request, "printing/pricing/shop_form.html", {"form": form, "title": f"Edit {shop.name}"})


@role_required(OWNER)
@require_POST
def shop_delete(request, pk):
    shop = get_object_or_404(PrintShop, pk=pk, owner=request.user)
    if shop.orders.exists():
        messages.error(request, "This shop has orders and can't be deleted. Mark it closed instead.")
        return redirect("printing:shop_list")
    try:
        with transaction.atomic():
            shop.delete()
    except ProtectedError:
        messages.error(request, "This shop has orders and can't be deleted. Mark it closed instead.")
    else:
        messages.success(request, "Shop deleted.")
    return redirect("printing:shop_list")


@role_required(OWNER)
def price_create(request, shop_pk):
    shop = get_object_or_404(PrintShop, pk=shop_pk, owner=request.user)
    form = PriceForm(request.POST or None, shop=shop)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Price rule added.")
        return redirect("printing:shop_list")
    if request.method == "POST":
        messages.error(request, "Please fix the errors below.")
    return render(request, "printing/pricing/price_form.html", {"form": form, "shop": shop, "title": "Add a price rule"})


@role_required(OWNER)
def price_edit(request, pk):
    price = get_object_or_404(PrintPrice.objects.select_related("shop"), pk=pk, shop__owner=request.user)
    form = PriceForm(request.POST or None, instance=price, shop=price.shop)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Price rule updated. Existing orders keep the total they were placed with.")
        return redirect("printing:shop_list")
    if request.method == "POST":
        messages.error(request, "Please fix the errors below.")
    return render(request, "printing/pricing/price_form.html", {"form": form, "shop": price.shop, "title": "Edit price rule"})


@role_required(OWNER)
@require_POST
def price_delete(request, pk):
    price = get_object_or_404(PrintPrice, pk=pk, shop__owner=request.user)
    if price.orders.exists():
        messages.error(request, "This price rule is used by existing orders and can't be deleted.")
        return redirect("printing:shop_list")
    try:
        with transaction.atomic():
            price.delete()
    except ProtectedError:
        messages.error(request, "This price rule is used by existing orders and can't be deleted.")
    else:
        messages.success(request, "Price rule deleted.")
    return redirect("printing:shop_list")
