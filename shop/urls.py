from django.urls import path

from . import views

app_name = "shop"

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("cos/", views.cart_detail, name="cart"),
    path("cos/actualizeaza/", views.cart_update, name="cart_update"),
    path("comanda/", views.checkout, name="checkout"),
    path("<slug:slug>/", views.product_detail, name="product_detail"),
]
