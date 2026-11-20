from django.urls import include, path

app_name = "printing"

urlpatterns = [
    path("", include("printing.urls_setup")),    # feature/document-upload-pricing
    path("", include("printing.urls_orders")),   # feature/print-order-queue
]
