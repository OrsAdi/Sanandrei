"""
Magazinul pe site-ul static: coșul e păstrat în browser (localStorage), iar comanda
e trimisă pe emailul clubului prin Web3Forms. Vezi static/js/site.js.
"""

from django.shortcuts import get_object_or_404, render

from .models import Category, Product


def _catalog():
    """Date despre produse folosite de coș în browser: {slug: {...}}."""
    return {
        p.slug: {
            "name": p.name,
            "price": float(p.price),
            "url": p.get_absolute_url(),
            "image": p.image.url if p.image else "",
            "sizes": p.size_list,
            "in_stock": p.in_stock,
        }
        for p in Product.objects.filter(is_active=True)
    }


def product_list(request, categorie=None):
    products = Product.objects.filter(is_active=True).select_related("category")
    category = None
    if categorie:
        category = get_object_or_404(Category, slug=categorie)
        products = products.filter(category=category)
    return render(request, "shop/product_list.html", {
        "products": products,
        "categories": Category.objects.filter(products__is_active=True).distinct(),
        "category": category,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    return render(request, "shop/product_detail.html", {"product": product})


def cart_detail(request):
    return render(request, "shop/cart.html", {"catalog": _catalog()})


def checkout(request):
    return render(request, "shop/checkout.html", {"catalog": _catalog()})
