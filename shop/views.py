from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .cart import Cart
from .forms import AddToCartForm, CheckoutForm
from .models import Category, OrderItem, Product


def product_list(request):
    products = Product.objects.filter(is_active=True).select_related("category")
    category = None
    slug = request.GET.get("categorie")
    if slug:
        category = get_object_or_404(Category, slug=slug)
        products = products.filter(category=category)
    return render(request, "shop/product_list.html", {
        "products": products,
        "categories": Category.objects.filter(products__is_active=True).distinct(),
        "category": category,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    form = AddToCartForm(request.POST or None, product=product)
    if request.method == "POST" and form.is_valid():
        if not product.in_stock:
            messages.error(request, "Produsul nu mai este în stoc.")
        else:
            Cart(request).add(product, form.cleaned_data.get("size", ""), form.cleaned_data["quantity"])
            messages.success(request, f"„{product.name}” a fost adăugat în coș.")
            return redirect("shop:cart")
    return render(request, "shop/product_detail.html", {"product": product, "form": form})


def cart_detail(request):
    cart = Cart(request)
    return render(request, "shop/cart.html", {"items": list(cart.items()), "total": cart.total()})


@require_POST
def cart_update(request):
    cart = Cart(request)
    key = request.POST.get("key", "")
    try:
        quantity = int(request.POST.get("quantity", 0))
    except ValueError:
        quantity = 0
    if key in cart.data:
        cart.set(key, quantity)
    return redirect("shop:cart")


def checkout(request):
    cart = Cart(request)
    items = list(cart.items())
    if not items:
        messages.info(request, "Coșul este gol.")
        return redirect("shop:product_list")
    form = CheckoutForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            order = form.save()
            for i in items:
                OrderItem.objects.create(order=order, product=i["product"], size=i["size"],
                                         quantity=i["quantity"], price=i["product"].price)
        cart.clear()
        return render(request, "shop/order_done.html", {"order": order})
    return render(request, "shop/checkout.html", {"form": form, "items": items, "total": cart.total()})
