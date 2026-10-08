from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Ticket(models.Model):
    """Billet : demande de critique sur un livre ou un article."""

    title = models.CharField("titre", max_length=128)
    description = models.TextField("description", max_length=2048, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tickets",
        verbose_name="auteur",
    )
    image = models.ImageField("image", upload_to="tickets/", null=True, blank=True)
    time_created = models.DateTimeField("date de création", auto_now_add=True)

    class Meta:
        verbose_name = "billet"
        ordering = ["-time_created"]

    def __str__(self):
        return self.title


class Review(models.Model):
    """Critique : réponse à un billet, avec une note de 0 à 5."""

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="billet",
    )
    rating = models.PositiveSmallIntegerField(
        "note", validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="auteur",
    )
    headline = models.CharField("titre", max_length=128)
    body = models.TextField("commentaire", max_length=8192, blank=True)
    time_created = models.DateTimeField("date de création", auto_now_add=True)

    class Meta:
        verbose_name = "critique"
        ordering = ["-time_created"]
        constraints = [
            # Wireframe : on bloque les critiques sur un billet qui en a déjà une
            models.UniqueConstraint(fields=["ticket"], name="une_critique_par_billet"),
            models.CheckConstraint(
                condition=models.Q(rating__gte=0, rating__lte=5),
                name="note_entre_0_et_5",
            ),
        ]

    def __str__(self):
        return f"{self.headline} ({self.rating}/5)"


class UserFollows(models.Model):
    """Abonnement : `user` suit `followed_user`."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following",
        verbose_name="abonné",
    )
    followed_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="followed_by",
        verbose_name="utilisateur suivi",
    )

    class Meta:
        verbose_name = "abonnement"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "followed_user"], name="abonnement_unique"
            ),
            models.CheckConstraint(
                condition=~models.Q(user=models.F("followed_user")),
                name="pas_d_abonnement_a_soi_meme",
            ),
        ]

    def __str__(self):
        return f"{self.user} suit {self.followed_user}"
