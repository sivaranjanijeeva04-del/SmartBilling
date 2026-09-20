from django.urls import path
from . import views

urlpatterns = [
    path("", views.reports_dashboard, name="reports"),
    path("export/", views.export_reports_csv, name="export_reports_csv"),
]