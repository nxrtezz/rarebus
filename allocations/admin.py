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
