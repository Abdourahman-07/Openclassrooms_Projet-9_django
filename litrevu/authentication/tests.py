from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class AuthenticationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="MotDePasse!2026")

    def test_custom_user_model(self):
        self.assertEqual(User._meta.label, "authentication.User")

    def test_login_and_signup_pages_public(self):
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)
        self.assertEqual(self.client.get(reverse("signup")).status_code, 200)

    def test_flux_requires_login(self):
        response = self.client.get(reverse("flux"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('flux')}")

    def test_login_redirects_to_flux(self):
        response = self.client.post(
            reverse("login"), {"username": "alice", "password": "MotDePasse!2026"}
        )
        self.assertRedirects(response, reverse("flux"))

    def test_bad_login_shows_alert(self):
        response = self.client.post(reverse("login"), {"username": "alice", "password": "faux"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'role="alert"')

    def test_signup_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("signup"),
            {"username": "bob", "password1": "UnMotDePasse!42", "password2": "UnMotDePasse!42"},
        )
        self.assertRedirects(response, reverse("flux"))
        self.assertTrue(User.objects.filter(username="bob").exists())

    def test_signup_errors_are_linked_to_fields(self):
        response = self.client.post(
            reverse("signup"),
            {"username": "alice", "password1": "abc", "password2": "xyz"},
        )
        html = response.content.decode()
        self.assertIn('aria-invalid="true"', html)
        self.assertIn('id="id_username_errors"', html)
        self.assertIn('aria-describedby="id_username_errors', html)

    def test_logout_is_post_only(self):
        self.client.login(username="alice", password="MotDePasse!2026")
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))

    def test_logged_user_redirected_from_login(self):
        self.client.login(username="alice", password="MotDePasse!2026")
        self.assertRedirects(self.client.get(reverse("login")), reverse("flux"))
        self.assertRedirects(self.client.get(reverse("signup")), reverse("flux"))
