from django.urls import path

from . import views

app_name = "shop"

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("categorie/<slug:categorie>/", views.product_list, name="category"),
    path("cos/", views.cart_detail, name="cart"),
    path("comanda/", views.checkout, name="checkout"),
    path("<slug:slug>/", views.product_detail, name="product_detail"),
]
