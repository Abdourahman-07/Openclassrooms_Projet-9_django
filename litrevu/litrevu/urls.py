from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import path

import authentication.views
import reviews.views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", authentication.views.LoginPageView.as_view(), name="login"),
    path("signup/", authentication.views.signup_page, name="signup"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("flux/", reviews.views.flux, name="flux"),
    path("posts/", reviews.views.posts, name="posts"),
    path("tickets/create/", reviews.views.ticket_edit, name="ticket_create"),
    path("tickets/<int:ticket_id>/edit/", reviews.views.ticket_edit, name="ticket_update"),
    path("tickets/<int:ticket_id>/delete/", reviews.views.ticket_delete, name="ticket_delete"),
    path(
        "tickets/<int:ticket_id>/review/",
        reviews.views.review_edit,
        name="review_create_for_ticket",
    ),
    path("reviews/create/", reviews.views.review_create, name="review_create"),
    path("reviews/<int:review_id>/edit/", reviews.views.review_edit, name="review_update"),
    path("reviews/<int:review_id>/delete/", reviews.views.review_delete, name="review_delete"),
    path("subscriptions/", reviews.views.subscriptions, name="subscriptions"),
    path("subscriptions/<int:follow_id>/unfollow/", reviews.views.unfollow, name="unfollow"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
