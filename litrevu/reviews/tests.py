from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Review, Ticket, UserFollows

User = get_user_model()


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
