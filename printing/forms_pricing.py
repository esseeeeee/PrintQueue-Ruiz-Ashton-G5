from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from .models import PrintPrice, PrintShop


class ShopForm(forms.ModelForm):
    class Meta:
        model = PrintShop
        fields = ("name", "location", "is_active")
        labels = {"is_active": "Shop is open (accepting orders)"}

    def __init__(self, *args, owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        duplicates = PrintShop.objects.filter(owner=self.owner, name__iexact=name)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise ValidationError("You already have a shop with this name.")
        return name

    def clean_location(self):
        return " ".join(self.cleaned_data["location"].split())


class PriceForm(forms.ModelForm):
    price_per_page = forms.DecimalField(
        label="Price per page (₱)", min_value=Decimal("0.01"), max_digits=10, decimal_places=2,
    )  # BR-04: must be greater than zero

    class Meta:
        model = PrintPrice
        fields = ("paper_size", "color_option", "price_per_page")

    def __init__(self, *args, shop, **kwargs):
        super().__init__(*args, **kwargs)
        self.shop = shop
        self.instance.shop = shop

    def clean(self):
        cleaned = super().clean()
        paper, color = cleaned.get("paper_size"), cleaned.get("color_option")
        if paper and color:
            duplicates = PrintPrice.objects.filter(shop=self.shop, paper_size=paper, color_option=color)
            if self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise ValidationError("This shop already has a price for that paper size and color.")
        return cleaned
