from django.urls import path

from . import views_documents as docs
from . import views_pricing as pricing

urlpatterns = [
    # Student: documents
    path("documents/", docs.document_list, name="document_list"),
    path("documents/upload/", docs.document_upload, name="document_upload"),
    path("documents/<int:pk>/delete/", docs.document_delete, name="document_delete"),
    path("documents/<int:pk>/download/", docs.document_download, name="document_download"),
    # Shop owner: shops and price rules
    path("shop/shops/", pricing.shop_list, name="shop_list"),
    path("shop/shops/new/", pricing.shop_create, name="shop_create"),
    path("shop/shops/<int:pk>/edit/", pricing.shop_edit, name="shop_edit"),
    path("shop/shops/<int:pk>/delete/", pricing.shop_delete, name="shop_delete"),
    path("shop/shops/<int:shop_pk>/prices/new/", pricing.price_create, name="price_create"),
    path("shop/prices/<int:pk>/edit/", pricing.price_edit, name="price_edit"),
    path("shop/prices/<int:pk>/delete/", pricing.price_delete, name="price_delete"),
]
