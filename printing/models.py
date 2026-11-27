"""Models mirroring the SDD data dictionary (Section 4.4)."""
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from .validators import validate_document_file

User = settings.AUTH_USER_MODEL


# on_delete summary (PD3 data integrity):
#   PrintShop.owner        PROTECT  - a user who owns shops cannot be deleted by accident
#   PrintPrice.shop        CASCADE  - prices have no meaning without their shop
#   Document.user          CASCADE  - a student's unused files go with the student
#                                     (files used by orders are still protected by PrintOrder.document)
#   PrintOrder.*           PROTECT  - order history must never disappear silently
#   Payment.order/collected_by PROTECT - payment records must be kept


# ---------- print_shops ----------
class PrintShop(models.Model):
    shop_id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="shops",
        limit_choices_to={"role": "SHOP_OWNER"},
    )
    name = models.CharField(max_length=150)
    location = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "print_shops"
        constraints = [
            # One owner cannot have two shops with the same name (ignoring upper/lower case)
            models.UniqueConstraint(Lower("name"), "owner", name="unique_shop_name_per_owner"),
        ]

    def __str__(self):
        return self.name


# ---------- print_prices ----------
class PrintPrice(models.Model):
    class PaperSize(models.TextChoices):
        SHORT = "Short", "Short"
        A4 = "A4", "A4"
        LONG = "Long", "Long"

    class ColorOption(models.TextChoices):
        BW = "Black & White", "Black & White"
        FULL = "Full Color", "Full Color"

    price_id = models.AutoField(primary_key=True)
    shop = models.ForeignKey(PrintShop, on_delete=models.CASCADE, related_name="prices")
    paper_size = models.CharField(max_length=20, choices=PaperSize.choices)
    color_option = models.CharField(max_length=20, choices=ColorOption.choices)
    price_per_page = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "print_prices"
        constraints = [
            # One price rule per shop + paper size + color (also protects against double clicks)
            models.UniqueConstraint(
                fields=["shop", "paper_size", "color_option"], name="unique_price_rule_per_shop"),
            models.CheckConstraint(condition=Q(price_per_page__gt=0), name="price_per_page_positive"),  # BR-04
            models.CheckConstraint(condition=Q(paper_size__in=["Short", "A4", "Long"]), name="paper_size_valid"),
            models.CheckConstraint(
                condition=Q(color_option__in=["Black & White", "Full Color"]), name="color_option_valid"),
        ]

    def __str__(self):
        return f"{self.shop} – {self.paper_size} {self.color_option} (₱{self.price_per_page}/page)"


# ---------- documents ----------
class DocumentQuerySet(models.QuerySet):
    def for_student(self, user):  # BR-07
        return self.filter(user=user)


class Document(models.Model):
    document_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    file_name = models.CharField(max_length=255, blank=True)
    file = models.FileField(
        upload_to="documents/%Y/%m/", max_length=255, db_column="file_path",
        validators=[validate_document_file],
    )
    page_count = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    uploaded_at = models.DateTimeField(auto_now_add=True)

    objects = DocumentQuerySet.as_manager()

    class Meta:
        db_table = "documents"
        constraints = [
            models.CheckConstraint(condition=Q(page_count__gte=1), name="document_page_count_positive"),
        ]

    def save(self, *args, **kwargs):
        if not self.file_name and self.file:
            self.file_name = os.path.basename(self.file.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.file_name or f"Document #{self.pk}"


# ---------- print_orders ----------
class PrintOrderQuerySet(models.QuerySet):
    def for_student(self, user):  # BR-07
        return self.filter(user=user)

    def for_shop_owner(self, user):  # BR-08
        return self.filter(shop__owner=user)


class PrintOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PRINTING = "PRINTING", "Printing"
        READY = "READY FOR PICKUP", "Ready for pickup"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    order_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders")
    shop = models.ForeignKey(PrintShop, on_delete=models.PROTECT, related_name="orders")
    # BR-09: a document linked to an order cannot be deleted
    document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name="orders")
    price = models.ForeignKey(PrintPrice, on_delete=models.PROTECT, related_name="orders")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    order_date = models.DateTimeField(auto_now_add=True)

    objects = PrintOrderQuerySet.as_manager()

    class Meta:
        db_table = "print_orders"
        constraints = [
            models.CheckConstraint(condition=Q(total_amount__gte=0), name="order_total_non_negative"),  # BR-06
            models.CheckConstraint(                                                                    # BR-05
                condition=Q(status__in=["PENDING", "PRINTING", "READY FOR PICKUP", "COMPLETED", "CANCELLED"]),
                name="order_status_valid",
            ),
        ]

    def compute_total(self):
        """Objective 4: pages x price per page."""
        return self.document.page_count * self.price.price_per_page

    def clean(self):
        if self.document_id and self.user_id and self.document.user_id != self.user_id:
            raise ValidationError("You can only order your own documents.")
        if self.price_id and self.shop_id and self.price.shop_id != self.shop_id:
            raise ValidationError("The selected price rule does not belong to this shop.")

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.clean()
            self.total_amount = self.compute_total()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.pk} – {self.status}"


# ---------- payments ----------
class Payment(models.Model):
    payment_id = models.AutoField(primary_key=True)
    order = models.OneToOneField(PrintOrder, on_delete=models.PROTECT, related_name="payment")
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    collected_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="collected_payments",
        limit_choices_to={"role": "SHOP_OWNER"},
    )
    payment_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payments"
        constraints = [
            models.CheckConstraint(condition=Q(amount_paid__gte=0), name="payment_amount_non_negative"),
        ]

    def clean(self):
        if self.order_id:
            # BR-10: cash is only recorded when the order is READY FOR PICKUP
            if self.order.status != PrintOrder.Status.READY:
                raise ValidationError("Cash can only be recorded when the order is READY FOR PICKUP.")
            # BR-08: only the shop's owner can collect for that shop
            if self.collected_by_id and self.order.shop.owner_id != self.collected_by_id:
                raise ValidationError("Only the owner of this shop can collect its payments.")

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payment for order #{self.order_id}: ₱{self.amount_paid}"
