from django.contrib import admin

from .models import Document, Payment, PrintOrder, PrintPrice, PrintShop


@admin.register(PrintShop)
class PrintShopAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "location", "is_active")
    list_filter = ("is_active",)


@admin.register(PrintPrice)
class PrintPriceAdmin(admin.ModelAdmin):
    list_display = ("shop", "paper_size", "color_option", "price_per_page")
    list_filter = ("paper_size", "color_option")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("file_name", "user", "page_count", "uploaded_at")


@admin.register(PrintOrder)
class PrintOrderAdmin(admin.ModelAdmin):
    list_display = ("order_id", "user", "shop", "status", "total_amount", "order_date")
    list_filter = ("status", "shop")
    readonly_fields = ("total_amount",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "amount_paid", "collected_by", "payment_date")
