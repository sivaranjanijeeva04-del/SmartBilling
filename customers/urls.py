from django.urls import path
from . import views

urlpatterns = [
    path('', views.customer_list, name='customers'),
    path('add/', views.add_customer, name='add_customer'),
    path('edit/<int:id>/', views.edit_customer, name='edit_customer'),
    path('delete/<int:id>/', views.delete_customer, name='delete_customer'),
]