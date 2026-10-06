from decimal import Decimal

from .models import Product

SESSION_KEY = "cart"


class Cart:
    """Coș de cumpărături păstrat în sesiune: {"<product_id>|<size>": quantity}."""

    def __init__(self, request):
        self.session = request.session
        self.data = self.session.get(SESSION_KEY, {})

    def _save(self):
        self.session[SESSION_KEY] = self.data
        self.session.modified = True

    @staticmethod
    def key(product_id, size=""):
        return f"{product_id}|{size}"

    def add(self, product, size="", quantity=1):
        k = self.key(product.pk, size)
        self.data[k] = min(self.data.get(k, 0) + quantity, 99)
        self._save()

    def set(self, key, quantity):
        if quantity <= 0:
            self.data.pop(key, None)
        else:
            self.data[key] = min(quantity, 99)
        self._save()

    def clear(self):
        self.data = {}
        self._save()

    def __len__(self):
        return sum(self.data.values())

    def items(self):
        ids = {int(k.split("|")[0]) for k in self.data}
        products = Product.objects.in_bulk(ids)
        for k, qty in self.data.items():
            pid, size = k.split("|", 1)
            product = products.get(int(pid))
            if product is None or not product.is_active:
                continue
            yield {"key": k, "product": product, "size": size, "quantity": qty,
                   "subtotal": product.price * qty}

    def total(self):
        return sum((i["subtotal"] for i in self.items()), Decimal("0"))
