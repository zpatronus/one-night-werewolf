from django.contrib import admin
from django.db.models import Count

from .models import Room


class RoomAdmin(admin.ModelAdmin):
    list_display = ("roomid", "phase", "player_count", "created_at")
    list_filter = ("phase",)

    def get_queryset(self, request):
        # Annotate player count in a single query instead of N queries per row.
        qs = super().get_queryset(request)
        return qs.annotate(_player_count=Count("players"))

    @admin.display(description="Players")
    def player_count(self, obj):
        return obj._player_count

admin.site.register(Room, RoomAdmin)