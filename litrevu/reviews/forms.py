from django import forms

from authentication.forms import AccessibleFormMixin

from .models import Review, Ticket

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
