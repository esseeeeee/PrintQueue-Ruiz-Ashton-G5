from django.urls import path

from . import views_orders as orders
from . import views_queue as queue

urlpatterns = [
    # Student: orders
    path("orders/", orders.order_list, name="order_list"),
    path("orders/new/", orders.order_create, name="order_create"),
    path("orders/<int:pk>/", orders.order_detail, name="order_detail"),
    path("orders/<int:pk>/edit/", orders.order_edit, name="order_edit"),
    path("orders/<int:pk>/cancel/", orders.order_cancel, name="order_cancel"),
    path("orders/<int:pk>/delete/", orders.order_delete, name="order_delete"),
    # Shop owner: incoming order queue
    path("shop/orders/", queue.shop_order_list, name="shop_order_list"),
    path("shop/orders/<int:pk>/", queue.shop_order_detail, name="shop_order_detail"),
    path("shop/orders/<int:pk>/status/", queue.shop_order_status, name="shop_order_status"),
    path("shop/orders/<int:pk>/payment/", queue.shop_order_payment, name="shop_order_payment"),
]
