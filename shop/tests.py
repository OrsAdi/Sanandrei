from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Category, Product


class ShopTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Echipament", slug="echipament")
        self.product = Product.objects.create(name="Tricou oficial", slug="tricou", price=Decimal("80"), stock=1,
                                              sizes="S,M,L", category=self.cat)

    def test_product_page_has_cart_form(self):
        response = self.client.get(self.product.get_absolute_url())
        self.assertContains(response, 'data-add-to-cart="tricou"')
        self.assertContains(response, '<option value="M">')

    def test_cart_and_checkout_embed_catalog(self):
        for name in ("shop:cart", "shop:checkout"):
            response = self.client.get(reverse(name))
            self.assertContains(response, 'id="shop-catalog"')
            self.assertContains(response, '"tricou"')

    def test_category_page(self):
        Product.objects.create(name="Fular", slug="fular", price=Decimal("40"), stock=1)
        response = self.client.get(reverse("shop:category", args=["echipament"]))
        self.assertContains(response, "Tricou oficial")
        self.assertNotContains(response, "Fular")

    def test_out_of_stock_has_no_cart_form(self):
        self.product.stock = 0
        self.product.save()
        self.assertNotContains(self.client.get(self.product.get_absolute_url()), "data-add-to-cart")
