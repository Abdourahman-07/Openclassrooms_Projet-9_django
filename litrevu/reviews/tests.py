import shutil
import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Review, Ticket, UserFollows

User = get_user_model()

# Les images envoyées pendant les tests vont dans un dossier temporaire
TEST_MEDIA_ROOT = tempfile.mkdtemp()


def make_image(name="couverture.png"):
    buffer = BytesIO()
    Image.new("RGB", (10, 10), "red").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class ModelTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="MotDePasse!2026")
        self.bob = User.objects.create_user(username="bob", password="MotDePasse!2026")
        self.ticket = Ticket.objects.create(title="L'Origine des espèces", user=self.alice)

    def test_ticket_and_review_are_linked(self):
        review = Review.objects.create(
            ticket=self.ticket, user=self.bob, rating=5, headline="Révolutionnaire"
        )
        self.assertEqual(list(self.ticket.reviews.all()), [review])
        self.assertEqual(str(review), "Révolutionnaire (5/5)")

    def test_rating_must_be_between_0_and_5(self):
        review = Review(ticket=self.ticket, user=self.bob, rating=6, headline="Trop")
        with self.assertRaises(ValidationError):
            review.full_clean()
        with self.assertRaises(IntegrityError):
            review.save()

    def test_only_one_review_per_ticket(self):
        Review.objects.create(ticket=self.ticket, user=self.bob, rating=4, headline="Bien")
        with self.assertRaises(IntegrityError):
            Review.objects.create(ticket=self.ticket, user=self.alice, rating=3, headline="Bof")

    def test_follow_relations(self):
        UserFollows.objects.create(user=self.alice, followed_user=self.bob)
        self.assertEqual(self.alice.following.get().followed_user, self.bob)
        self.assertEqual(self.bob.followed_by.get().user, self.alice)

    def test_cannot_follow_twice_or_self(self):
        UserFollows.objects.create(user=self.alice, followed_user=self.bob)
        with self.assertRaises(IntegrityError), transaction.atomic():
            UserFollows.objects.create(user=self.alice, followed_user=self.bob)
        with self.assertRaises(IntegrityError), transaction.atomic():
            UserFollows.objects.create(user=self.alice, followed_user=self.alice)

    def test_deleting_ticket_deletes_its_reviews(self):
        Review.objects.create(ticket=self.ticket, user=self.bob, rating=4, headline="Bien")
        self.ticket.delete()
        self.assertFalse(Review.objects.exists())


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class TicketViewTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="MotDePasse!2026")
        self.bob = User.objects.create_user(username="bob", password="MotDePasse!2026")
        self.ticket = Ticket.objects.create(title="La relativité", user=self.alice)
        self.client.force_login(self.alice)

    def test_pages_require_login(self):
        self.client.logout()
        for url in [
            reverse("posts"),
            reverse("ticket_create"),
            reverse("ticket_update", args=[self.ticket.pk]),
            reverse("ticket_delete", args=[self.ticket.pk]),
        ]:
            response = self.client.get(url)
            self.assertRedirects(response, f"{reverse('login')}?next={url}")

    def test_create_ticket_with_image(self):
        response = self.client.post(
            reverse("ticket_create"),
            {"title": "Discours de la méthode", "description": "Avis ?", "image": make_image()},
        )
        self.assertRedirects(response, reverse("posts"))
        ticket = Ticket.objects.get(title="Discours de la méthode")
        self.assertEqual(ticket.user, self.alice)
        self.assertTrue(ticket.image.name.startswith("tickets/"))

    def test_create_ticket_errors_are_accessible(self):
        response = self.client.post(reverse("ticket_create"), {"title": ""})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(response, 'id="id_title_errors"')
        self.assertContains(response, '<label for="id_title">Titre</label>', html=True)

    def test_update_own_ticket(self):
        response = self.client.post(
            reverse("ticket_update", args=[self.ticket.pk]),
            {"title": "La relativité - Albert Einstein"},
        )
        self.assertRedirects(response, reverse("posts"))
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.title, "La relativité - Albert Einstein")

    def test_cannot_update_or_delete_other_users_ticket(self):
        self.client.force_login(self.bob)
        update_url = reverse("ticket_update", args=[self.ticket.pk])
        delete_url = reverse("ticket_delete", args=[self.ticket.pk])
        self.assertEqual(self.client.get(update_url).status_code, 404)
        self.assertEqual(self.client.post(update_url, {"title": "Piraté"}).status_code, 404)
        self.assertEqual(self.client.post(delete_url).status_code, 404)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.title, "La relativité")

    def test_delete_requires_post(self):
        url = reverse("ticket_delete", args=[self.ticket.pk])
        response = self.client.get(url)  # page de confirmation, rien n'est supprimé
        self.assertContains(response, '<form method="post"')
        self.assertTrue(Ticket.objects.filter(pk=self.ticket.pk).exists())
        self.assertRedirects(self.client.post(url), reverse("posts"))
        self.assertFalse(Ticket.objects.filter(pk=self.ticket.pk).exists())

    def test_delete_removes_image_file(self):
        ticket = Ticket.objects.create(title="Avec image", user=self.alice, image=make_image())
        storage, name = ticket.image.storage, ticket.image.name
        self.assertTrue(storage.exists(name))
        self.client.post(reverse("ticket_delete", args=[ticket.pk]))
        self.assertFalse(storage.exists(name))


class ReviewViewTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="MotDePasse!2026")
        self.bob = User.objects.create_user(username="bob", password="MotDePasse!2026")
        self.ticket = Ticket.objects.create(title="L'Origine des espèces", user=self.bob)
        self.client.force_login(self.alice)

    def test_review_create_creates_ticket_and_review(self):
        response = self.client.post(
            reverse("review_create"),
            {"title": "La relativité", "headline": "Exceptionnel", "rating": "5", "body": ""},
        )
        self.assertRedirects(response, reverse("posts"))
        review = Review.objects.get(headline="Exceptionnel")
        self.assertEqual((review.user, review.rating), (self.alice, 5))
        self.assertEqual((review.ticket.title, review.ticket.user), ("La relativité", self.alice))

    def test_review_create_shows_errors_of_both_forms(self):
        response = self.client.post(reverse("review_create"), {})
        self.assertContains(response, 'id="id_title_errors"')
        self.assertContains(response, 'id="id_headline_errors"')
        self.assertContains(response, 'id="id_rating_errors"')
        self.assertFalse(Ticket.objects.filter(user=self.alice).exists())

    def test_rating_is_a_group_of_radio_buttons(self):
        response = self.client.get(reverse("review_create_for_ticket", args=[self.ticket.pk]))
        self.assertContains(response, "<legend>Note</legend>", html=True)
        self.assertContains(response, 'type="radio"', count=6)

    def test_review_in_response_to_ticket(self):
        url = reverse("review_create_for_ticket", args=[self.ticket.pk])
        response = self.client.post(url, {"headline": "Révolutionnaire", "rating": "4"})
        self.assertRedirects(response, reverse("posts"))
        self.assertEqual(self.ticket.reviews.get().user, self.alice)
        # Une seule critique par billet : la seconde tentative est refusée
        self.assertRedirects(self.client.get(url), reverse("posts"))
        self.client.post(url, {"headline": "Encore", "rating": "1"})
        self.assertEqual(self.ticket.reviews.count(), 1)

    def test_update_and_delete_own_review(self):
        review = Review.objects.create(ticket=self.ticket, user=self.alice, rating=2, headline="Bof")
        response = self.client.post(
            reverse("review_update", args=[review.pk]), {"headline": "Finalement bien", "rating": "4"}
        )
        self.assertRedirects(response, reverse("posts"))
        review.refresh_from_db()
        self.assertEqual((review.headline, review.rating), ("Finalement bien", 4))

        delete_url = reverse("review_delete", args=[review.pk])
        self.client.get(delete_url)
        self.assertTrue(Review.objects.filter(pk=review.pk).exists())
        self.client.post(delete_url)
        self.assertFalse(Review.objects.filter(pk=review.pk).exists())
        self.assertTrue(Ticket.objects.filter(pk=self.ticket.pk).exists())

    def test_cannot_update_or_delete_other_users_review(self):
        review = Review.objects.create(ticket=self.ticket, user=self.bob, rating=3, headline="Moyen")
        self.assertEqual(self.client.get(reverse("review_update", args=[review.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("review_delete", args=[review.pk])).status_code, 404)
        self.assertTrue(Review.objects.filter(pk=review.pk).exists())

    def test_posts_lists_only_own_posts_with_text_rating(self):
        Review.objects.create(ticket=self.ticket, user=self.alice, rating=4, headline="Ma critique")
        Ticket.objects.create(title="Mon ticket", user=self.alice)
        Ticket.objects.create(title="Ticket de Bob", user=self.bob)
        response = self.client.get(reverse("posts"))
        self.assertContains(response, "Ma critique")
        self.assertContains(response, "Mon ticket")
        self.assertNotContains(response, "Ticket de Bob")
        self.assertContains(response, "Note : 4 sur 5")
        self.assertContains(response, 'aria-current="page"')


class SubscriptionViewTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="MotDePasse!2026")
        self.bob = User.objects.create_user(username="bob", password="MotDePasse!2026")
        self.carol = User.objects.create_user(username="carol", password="MotDePasse!2026")
        self.client.force_login(self.alice)
        self.url = reverse("subscriptions")

    def test_page_requires_login(self):
        self.client.logout()
        self.assertRedirects(self.client.get(self.url), f"{reverse('login')}?next={self.url}")

    def test_follow_user_by_name(self):
        response = self.client.post(self.url, {"username": "Bob"}, follow=True)  # casse ignorée
        self.assertRedirects(response, self.url)
        self.assertTrue(UserFollows.objects.filter(user=self.alice, followed_user=self.bob).exists())
        self.assertContains(response, "Vous êtes maintenant abonné à bob.")

    def test_unknown_user_shows_accessible_error(self):
        response = self.client.post(self.url, {"username": "inconnu"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aucun utilisateur ne s&#x27;appelle « inconnu ».")
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(response, 'id="id_username_errors"')
        self.assertFalse(UserFollows.objects.exists())

    def test_cannot_follow_self_or_twice(self):
        self.client.post(self.url, {"username": "alice"})
        self.assertFalse(UserFollows.objects.exists())
        self.client.post(self.url, {"username": "bob"})
        response = self.client.post(self.url, {"username": "bob"})
        self.assertContains(response, "Vous êtes déjà abonné à bob.")
        self.assertEqual(UserFollows.objects.count(), 1)

    def test_lists_following_and_followers(self):
        UserFollows.objects.create(user=self.alice, followed_user=self.bob)
        UserFollows.objects.create(user=self.carol, followed_user=self.alice)
        response = self.client.get(self.url)
        self.assertEqual([f.followed_user for f in response.context["following"]], [self.bob])
        self.assertEqual([f.user for f in response.context["followers"]], [self.carol])
        self.assertContains(response, "Désabonner")

    def test_unfollow_requires_post_and_own_subscription(self):
        follow = UserFollows.objects.create(user=self.alice, followed_user=self.bob)
        other = UserFollows.objects.create(user=self.carol, followed_user=self.bob)
        unfollow_url = reverse("unfollow", args=[follow.pk])
        self.assertEqual(self.client.get(unfollow_url).status_code, 405)
        self.assertEqual(self.client.post(reverse("unfollow", args=[other.pk])).status_code, 404)
        self.assertRedirects(self.client.post(unfollow_url), self.url)
        self.assertFalse(UserFollows.objects.filter(pk=follow.pk).exists())
        self.assertTrue(UserFollows.objects.filter(pk=other.pk).exists())
