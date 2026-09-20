from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("billing.urls")),

    path("products/", include("products.urls")),

    path("customers/", include("customers.urls")),

    path("payments/", include("payments.urls")),

    path("reports/", include("reports.urls")),

    path("accounts/", include("accounts.urls")),
]