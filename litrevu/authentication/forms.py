from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm


class AccessibleFormMixin:
    """Relie chaque champ à son aide et à ses erreurs (WCAG 1.3.1, 3.3.1).

    - aria-describedby pointe vers l'aide et/ou le message d'erreur ;
    - aria-invalid="true" est ajouté aux champs en erreur ;
    - si label_as_placeholder est vrai, le libellé est repris en placeholder,
      comme sur le wireframe des pages de connexion et d'inscription
      (le <label> reste présent pour les lecteurs d'écran).
    Les identifiants correspondent à ceux générés dans _form_field.html
    (suppose l'auto_id par défaut "id_<nom>" et aucun préfixe de formulaire).
    """

    label_as_placeholder = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if self.label_as_placeholder:
                field.widget.attrs.setdefault("placeholder", field.label)
            if field.help_text:
                field.widget.attrs["aria-describedby"] = f"id_{name}_helptext"

    def full_clean(self):
        super().full_clean()
        for name in self._errors or {}:
            if name not in self.fields:
                continue  # erreurs globales (non_field_errors)
            attrs = self.fields[name].widget.attrs
            attrs["aria-invalid"] = "true"
            ids = attrs.get("aria-describedby", "").split()
            error_id = f"id_{name}_errors"
            if error_id not in ids:
                ids.insert(0, error_id)
            attrs["aria-describedby"] = " ".join(ids)


class SignupForm(AccessibleFormMixin, UserCreationForm):
    label_as_placeholder = True

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Libellé du wireframe (le placeholder du mixin est déjà posé : on le met à jour)
        password2 = self.fields["password2"]
        password2.label = "Confirmer le mot de passe"
        password2.widget.attrs["placeholder"] = password2.label


class LoginForm(AccessibleFormMixin, AuthenticationForm):
    label_as_placeholder = True
