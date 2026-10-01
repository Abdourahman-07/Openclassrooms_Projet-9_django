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
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
