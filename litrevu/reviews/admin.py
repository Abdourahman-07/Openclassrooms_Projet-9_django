from django.contrib import admin

from .models import Review, Ticket, UserFollows


class ReviewInline(admin.StackedInline):
    model = Review
    extra = 0


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "time_created")
    list_filter = ("time_created",)
    search_fields = ("title", "description", "user__username")
    inlines = [ReviewInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("headline", "ticket", "rating", "user", "time_created")
    list_filter = ("rating", "time_created")
    search_fields = ("headline", "body", "user__username", "ticket__title")


@admin.register(UserFollows)
class UserFollowsAdmin(admin.ModelAdmin):
    list_display = ("user", "followed_user")
    search_fields = ("user__username", "followed_user__username")
