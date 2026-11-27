from django.urls import path, register_converter

from .converters import DbIdConverter
from . import views_orders as orders
from . import views_queue as queue

register_converter(DbIdConverter, "dbid")

urlpatterns = [
    # Student: orders
    path("orders/", orders.order_list, name="order_list"),
    path("orders/new/", orders.order_create, name="order_create"),
    path("orders/<dbid:pk>/", orders.order_detail, name="order_detail"),
    path("orders/<dbid:pk>/edit/", orders.order_edit, name="order_edit"),
    path("orders/<dbid:pk>/cancel/", orders.order_cancel, name="order_cancel"),
    path("orders/<dbid:pk>/delete/", orders.order_delete, name="order_delete"),
    # Shop owner: incoming order queue
    path("shop/orders/", queue.shop_order_list, name="shop_order_list"),
    path("shop/orders/<dbid:pk>/", queue.shop_order_detail, name="shop_order_detail"),
    path("shop/orders/<dbid:pk>/status/", queue.shop_order_status, name="shop_order_status"),
    path("shop/orders/<dbid:pk>/payment/", queue.shop_order_payment, name="shop_order_payment"),
]
