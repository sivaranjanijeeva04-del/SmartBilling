from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    path("invoices/", views.invoice_list, name="invoices"),

    path(
        "invoices/add/",
        views.add_invoice,
        name="add_invoice"
    ),

    path(
        "invoices/<int:id>/",
        views.invoice_detail,
        name="invoice_detail"
    ),

    path(
        "invoices/<int:id>/pdf/",
        views.download_invoice_pdf,
        name="download_invoice_pdf"
    ),

    path(
        "sales-history/",
        views.sales_history,
        name="sales_history"
    ),
]