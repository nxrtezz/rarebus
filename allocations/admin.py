from django.contrib import admin
from .models import Operator, Route, Vehicle, TypeRule, VehicleRule, Alert, PollState, VehicleWatch, Supervisor

admin.site.register(Operator)
admin.site.register(Route)
admin.site.register(Vehicle)
admin.site.register(TypeRule)
admin.site.register(VehicleRule)
admin.site.register(Alert)
admin.site.register(PollState)
admin.site.register(VehicleWatch)

@admin.register(Supervisor)
class SupervisorAdmin(admin.ModelAdmin):
    list_display = ["discord_username", "operator"]

from .models import InviteCode


@admin.register(InviteCode)
class InviteCodeAdmin(admin.ModelAdmin):

    list_display = [
        "code",
        "active",
        "infinite_uses",
        "uses_remaining",
        "created_at"
    ]

    readonly_fields = ["code", "created_at"]

from .models import OperatorCustomCode

admin.site.register(OperatorCustomCode)

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

admin.site.unregister(User)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "last_login", "is_staff")

from django.contrib import admin
from .models import Operator, Supervisor

admin.site.unregister(Operator)

class SupervisorInline(admin.TabularInline):
    model = Supervisor
    extra = 1

@admin.register(Operator)
class OperatorAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    inlines = [SupervisorInline]

# allocations/admin.py

from django.contrib import admin
from .models import SupervisorRequest, Supervisor


@admin.register(SupervisorRequest)
class SupervisorRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "operator", "approved", "created_at")
    list_filter = ("approved", "operator")
    search_fields = ("user__username", "discord_username")

    def save_model(self, request, obj, form, change):
        if obj.approved:
            Supervisor.objects.get_or_create(
                operator=obj.operator,
                user=obj.user,
                defaults={"discord_username": obj.discord_username},
            )

        super().save_model(request, obj, form, change)

from django.contrib import admin
from .models import ChangeLog


@admin.register(ChangeLog)
class ChangeLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "operator", "action")
    list_filter = ("user", "operator", "created_at")
    search_fields = ("action", "details", "user__username")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    readonly_fields = ("details",)
    def short_details(self, obj):
        return obj.details[:50]

    short_details.short_description = "Details"
    list_display = ("created_at", "user", "operator", "action", "short_details")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

from .models import DiscordSubscription

@admin.register(DiscordSubscription)
class DiscordSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("operator", "channel_id", "user_id", "guild_id")
    search_fields = ("webhook_url", "user_id")
    list_filter = ("operator",)