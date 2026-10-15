from itertools import chain

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import CharField, Value
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .forms import FollowForm, ReviewForm, TicketForm
from .models import Review, Ticket, UserFollows


def form_data(request):
    """Données à passer aux formulaires : liés en POST (même vide), vierges sinon."""
    if request.method == "POST":
        return request.POST, request.FILES
    return None, None


@login_required
def flux(request):
    return render(request, "reviews/flux.html")


@login_required
def posts(request):
    """Billets et critiques de l'utilisateur courant, du plus récent au plus ancien."""
    tickets = (
        Ticket.objects.filter(user=request.user)
        .select_related("user")
        .prefetch_related("reviews")
        .annotate(content_type=Value("TICKET", output_field=CharField()))
    )
    reviews = (
        Review.objects.filter(user=request.user)
        .select_related("user", "ticket__user")
        .annotate(content_type=Value("REVIEW", output_field=CharField()))
    )
    user_posts = sorted(
        chain(tickets, reviews), key=lambda post: post.time_created, reverse=True
    )
    return render(request, "reviews/posts.html", {"posts": user_posts})


@login_required
def ticket_edit(request, ticket_id=None):
    """Crée un billet, ou modifie un billet de l'utilisateur courant."""
    ticket = None
    if ticket_id is not None:
        # Un billet d'un autre utilisateur renvoie une 404
        ticket = get_object_or_404(Ticket, pk=ticket_id, user=request.user)

    data, files = form_data(request)
    form = TicketForm(data, files, instance=ticket)
    if request.method == "POST" and form.is_valid():
        new_ticket = form.save(commit=False)
        new_ticket.user = request.user
        new_ticket.save()
        if ticket is None:
            messages.success(request, "Votre ticket a été publié.")
        else:
            messages.success(request, "Votre ticket a été modifié.")
        return redirect("posts")

    return render(request, "reviews/ticket_form.html", {"form": form, "ticket": ticket})


@login_required
@require_http_methods(["GET", "POST"])
def ticket_delete(request, ticket_id):
    """GET : page de confirmation ; POST : suppression."""
    ticket = get_object_or_404(Ticket, pk=ticket_id, user=request.user)
    if request.method == "POST":
        image = ticket.image
        ticket.delete()
        image.delete(save=False)  # supprime aussi le fichier envoyé
        messages.success(request, "Votre ticket a été supprimé.")
        return redirect("posts")

    return render(
        request,
        "reviews/confirm_delete.html",
        {"post": ticket, "post_template": "reviews/_ticket.html", "kind": "ticket"},
    )


@login_required
def review_create(request):
    """Crée un billet et sa critique en une seule fois (critique sans ticket)."""
    data, files = form_data(request)
    ticket_form = TicketForm(data, files)
    review_form = ReviewForm(data)
    # all() sur une liste : les deux formulaires sont validés pour afficher toutes les erreurs
    if request.method == "POST" and all([ticket_form.is_valid(), review_form.is_valid()]):
        with transaction.atomic():
            ticket = ticket_form.save(commit=False)
            ticket.user = request.user
            ticket.save()
            review = review_form.save(commit=False)
            review.ticket = ticket
            review.user = request.user
            review.save()
        messages.success(request, "Votre critique a été publiée.")
        return redirect("posts")

    return render(
        request,
        "reviews/review_create.html",
        {"ticket_form": ticket_form, "review_form": review_form},
    )


@login_required
def review_edit(request, ticket_id=None, review_id=None):
    """Crée une critique en réponse à un billet, ou modifie une critique de l'utilisateur."""
    if review_id is not None:
        review = get_object_or_404(
            Review.objects.select_related("ticket__user"), pk=review_id, user=request.user
        )
        ticket = review.ticket
    else:
        review = None
        ticket = get_object_or_404(Ticket.objects.select_related("user"), pk=ticket_id)
        if ticket.reviews.exists():
            messages.error(request, "Ce ticket a déjà reçu une critique.")
            return redirect("posts")

    data, _ = form_data(request)
    form = ReviewForm(data, instance=review)
    if request.method == "POST" and form.is_valid():
        new_review = form.save(commit=False)
        new_review.ticket = ticket
        new_review.user = request.user
        new_review.save()
        if review is None:
            messages.success(request, "Votre critique a été publiée.")
        else:
            messages.success(request, "Votre critique a été modifiée.")
        return redirect("posts")

    return render(
        request,
        "reviews/review_form.html",
        {"form": form, "ticket": ticket, "review": review},
    )


@login_required
@require_http_methods(["GET", "POST"])
def review_delete(request, review_id):
    """GET : page de confirmation ; POST : suppression."""
    review = get_object_or_404(
        Review.objects.select_related("ticket__user"), pk=review_id, user=request.user
    )
    if request.method == "POST":
        review.delete()
        messages.success(request, "Votre critique a été supprimée.")
        return redirect("posts")

    return render(
        request,
        "reviews/confirm_delete.html",
        {"post": review, "post_template": "reviews/_review.html", "kind": "critique"},
    )


@login_required
def subscriptions(request):
    """Liste des abonnements et des abonnés, avec le formulaire pour suivre quelqu'un."""
    data, _ = form_data(request)
    form = FollowForm(data, user=request.user)
    if request.method == "POST" and form.is_valid():
        UserFollows.objects.create(user=request.user, followed_user=form.followed_user)
        messages.success(request, f"Vous êtes maintenant abonné à {form.followed_user.username}.")
        return redirect("subscriptions")

    context = {
        "form": form,
        "following": request.user.following.select_related("followed_user").order_by(
            "followed_user__username"
        ),
        "followers": request.user.followed_by.select_related("user").order_by("user__username"),
    }
    return render(request, "reviews/subscriptions.html", context)


@login_required
@require_POST
def unfollow(request, follow_id):
    """Supprime un abonnement de l'utilisateur courant (POST uniquement)."""
    follow = get_object_or_404(
        UserFollows.objects.select_related("followed_user"), pk=follow_id, user=request.user
    )
    follow.delete()
    messages.success(request, f"Vous êtes désabonné de {follow.followed_user.username}.")
    return redirect("subscriptions")
