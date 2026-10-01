from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def flux(request):
    return render(request, "reviews/flux.html")
