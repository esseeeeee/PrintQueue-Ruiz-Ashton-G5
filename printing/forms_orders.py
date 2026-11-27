from decimal import Decimal

from django import forms

from .models import Document, PrintOrder, PrintPrice


class OrderForm(forms.ModelForm):
    """Student picks a document + a shop's price rule. The shop comes from the rule;
    the total is computed on the server (pages x price per page)."""

    class Meta:
        model = PrintOrder
        fields = ("document", "price")
        labels = {"document": "Document", "price": "Shop & print settings"}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.user = user
        doc_field, price_field = self.fields["document"], self.fields["price"]
        doc_field.queryset = Document.objects.for_student(user).order_by("-uploaded_at")  # BR-07
        doc_field.label_from_instance = lambda d: f"{d.file_name} ({d.page_count} pages)"
        doc_field.empty_label = "Select a document"
        price_field.queryset = (
            PrintPrice.objects.filter(shop__is_active=True)
            .select_related("shop").order_by("shop__name", "paper_size", "color_option")
        )
        price_field.label_from_instance = (
            lambda p: f"{p.shop.name} — {p.paper_size}, {p.color_option} — ₱{p.price_per_page}/page"
        )
        price_field.empty_label = "Select a shop & settings"

    def clean(self):
        cleaned = super().clean()
        price, document = cleaned.get("price"), cleaned.get("document")
        if price:
            self.instance.shop = price.shop
        if price and document:
            # Stops double-clicks / repeated submits from creating the same order twice.
            duplicates = PrintOrder.objects.filter(
                user=self.instance.user, document=document, price=price,
                status=PrintOrder.Status.PENDING)
            if self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise forms.ValidationError(
                    "You already have a pending order for this document with these settings.")
        return cleaned


class OrderFilterForm(forms.Form):
    q = forms.CharField(required=False, max_length=100, widget=forms.TextInput(attrs={"placeholder": "Search file, shop or student"}))
    status = forms.ChoiceField(
        required=False, choices=[("", "All statuses")] + list(PrintOrder.Status.choices))
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("date_from"), cleaned.get("date_to")
        if start and end and start > end:
            raise forms.ValidationError("The 'From' date must be before the 'To' date.")
        return cleaned


class PaymentForm(forms.Form):
    amount_paid = forms.DecimalField(
        label="Cash received (₱)", min_value=Decimal("0"), max_digits=12, decimal_places=2)
