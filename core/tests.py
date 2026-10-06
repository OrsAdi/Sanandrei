from django.test import TestCase
from django.urls import reverse

from .models import ContactMessage, News


class CoreTests(TestCase):
    def test_contact_form_saves_message(self):
        response = self.client.post(reverse("contact"), {
            "name": "Ion", "email": "ion@example.com", "subject": "Înscriere copii", "message": "Salut!",
        })
        self.assertRedirects(response, reverse("contact"))
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_contact_honeypot_blocks_spam(self):
        self.client.post(reverse("contact"), {
            "name": "Bot", "email": "bot@example.com", "subject": "x", "message": "x", "website": "spam",
        })
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_news(self):
        News.objects.create(title="Victorie", slug="victorie", body="Text")
        News.objects.create(title="Ascunsă", slug="ascunsa", body="Text", is_published=False)
        response = self.client.get(reverse("news_list"))
        self.assertContains(response, "Victorie")
        self.assertNotContains(response, "Ascunsă")
        self.assertEqual(self.client.get(reverse("news_detail", args=["ascunsa"])).status_code, 404)
