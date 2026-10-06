from django.db import models
from django.urls import reverse
from django.utils import timezone


class News(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    summary = models.CharField(max_length=300, blank=True)
    body = models.TextField()
    image = models.ImageField(upload_to="news/", blank=True)
    published_at = models.DateTimeField(default=timezone.now)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["-published_at"]
        verbose_name_plural = "news"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("news_detail", args=[self.slug])


class ContactMessage(models.Model):
    name = models.CharField("Nume", max_length=100)
    email = models.EmailField()
    phone = models.CharField("Telefon", max_length=30, blank=True)
    subject = models.CharField("Subiect", max_length=150)
    message = models.TextField("Mesaj")
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} – {self.name}"


class Sponsor(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to="sponsors/", blank=True)
    website = models.URLField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name
