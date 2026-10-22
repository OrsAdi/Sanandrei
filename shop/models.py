from django.db import models
from django.urls import reverse


class Category(models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to="products/", blank=True)
    sizes = models.CharField(max_length=100, blank=True, help_text="Mărimi separate prin virgulă, ex: S,M,L,XL")
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("shop:product_detail", args=[self.slug])

    @property
    def size_list(self):
        return [s.strip() for s in self.sizes.split(",") if s.strip()]

    @property
    def description_html(self):
        from core.content import render_markdown

        return render_markdown(self.description)

    @property
    def in_stock(self):
        return self.stock > 0


class Order(models.Model):
    STATUS = [
        ("new", "Nouă"),
        ("confirmed", "Confirmată"),
        ("ready", "Pregătită de ridicare"),
        ("done", "Finalizată"),
        ("cancelled", "Anulată"),
    ]

    full_name = models.CharField("Nume complet", max_length=120)
    phone = models.CharField("Telefon", max_length=30)
    email = models.EmailField(blank=True)
    note = models.TextField("Observații", blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="new")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comanda #{self.pk} – {self.full_name}"

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    size = models.CharField(max_length=20, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} × {self.product}"

    @property
    def subtotal(self):
        return self.price * self.quantity
