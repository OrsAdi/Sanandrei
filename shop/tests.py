from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Order, Product


class ShopTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(name="Tricou oficial", slug="tricou", price=Decimal("80"), stock=5, sizes="S,M,L")

    def test_add_to_cart_and_checkout(self):
        self.client.post(self.product.get_absolute_url(), {"quantity": 2, "size": "M"})
        response = self.client.get(reverse("shop:cart"))
        self.assertContains(response, "160,00")
        response = self.client.post(reverse("shop:checkout"), {"full_name": "Ana Pop", "phone": "0700000000"})
        self.assertContains(response, "Mulțumim")
        order = Order.objects.get()
        self.assertEqual(order.total, Decimal("160"))
        self.assertEqual(order.items.get().size, "M")
        self.assertEqual(self.client.session.get("cart"), {})

    def test_invalid_size_rejected(self):
        self.client.post(self.product.get_absolute_url(), {"quantity": 1, "size": "XXL"})
        self.assertEqual(self.client.session.get("cart", {}), {})

    def test_out_of_stock(self):
        self.product.stock = 0
        self.product.save()
        self.client.post(self.product.get_absolute_url(), {"quantity": 1, "size": "M"})
        self.assertEqual(self.client.session.get("cart", {}), {})

    def test_cart_update_removes_item(self):
        self.client.post(self.product.get_absolute_url(), {"quantity": 1, "size": "S"})
        self.client.post(reverse("shop:cart_update"), {"key": f"{self.product.pk}|S", "quantity": 0})
        self.assertEqual(self.client.session.get("cart"), {})
