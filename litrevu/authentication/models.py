from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Modèle utilisateur personnalisé.

    Vide pour l'instant, mais le déclarer AVANT la première migration
    permet de l'étendre plus tard sans casser la base de données.
    """

    pass
