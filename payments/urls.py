from django.urls import path
from . import views

urlpatterns = [
    path("", views.payment_list, name="payments"),
    path("add/", views.add_payment, name="add_payment"),
]