from django import forms
from django.contrib.auth import get_user_model

from authentication.forms import AccessibleFormMixin

from .models import Review, Ticket, UserFollows

RATING_CHOICES = [(rating, str(rating)) for rating in range(6)]


class TicketForm(AccessibleFormMixin, forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ("title", "description", "image")
        widgets = {"image": forms.ClearableFileInput(attrs={"accept": "image/*"})}


class ReviewForm(AccessibleFormMixin, forms.ModelForm):
    # Boutons radio de 0 à 5, comme sur le wireframe
    rating = forms.TypedChoiceField(
        label="Note", choices=RATING_CHOICES, coerce=int, widget=forms.RadioSelect
    )

    class Meta:
        model = Review
        fields = ("headline", "rating", "body")


class FollowForm(AccessibleFormMixin, forms.Form):
    """Recherche d'un utilisateur à suivre par son nom."""

    label_as_placeholder = True  # wireframe : champ « Nom d'utilisateur » sans libellé visible

    username = forms.CharField(label="Nom d'utilisateur", max_length=150)

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        try:
            followed_user = get_user_model().objects.get(username__iexact=username)
        except get_user_model().DoesNotExist:
            raise forms.ValidationError(f"Aucun utilisateur ne s'appelle « {username} ».")
        if followed_user == self.user:
            raise forms.ValidationError("Vous ne pouvez pas vous abonner à vous-même.")
        if UserFollows.objects.filter(user=self.user, followed_user=followed_user).exists():
            raise forms.ValidationError(f"Vous êtes déjà abonné à {followed_user.username}.")
        self.followed_user = followed_user
        return followed_user.username
