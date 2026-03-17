from django.db import models
from django.contrib.auth.models import User


class Operator(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50)
    theme_color = models.CharField(max_length=7, default="#00539f")
    accent_color = models.CharField(max_length=7, default="#f0ad4e")
    discord_webhook_url = models.TextField(blank=True)
    api_base_url = models.CharField(max_length=255, default="https://bustimes.org/api")
    vehicles_path = models.CharField(max_length=100, default="/vehicles/")
    services_path = models.CharField(max_length=100, default="/services/")
    vehicle_journeys_path = models.CharField(max_length=100, default="/vehiclejourneys/")
    operator_param_name = models.CharField(max_length=50, default="operator")
    training_code = models.CharField(max_length=50, blank=True)
    dead_code = models.CharField(max_length=50, blank=True)
    rail_replacement_code = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class OperatorCustomCode(models.Model):

    operator = models.ForeignKey(Operator, on_delete=models.CASCADE)

    code = models.CharField(max_length=50)

    display_name = models.CharField(max_length=100)

    class Meta:
        unique_together = ("operator", "code")

    def __str__(self):
        return f"{self.operator.code} {self.code}"


class Route(models.Model):
    operator = models.ForeignKey(Operator, on_delete=models.CASCADE)
    line_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    slug = models.CharField(max_length=200, blank=True)
    mode = models.CharField(max_length=50, default="bus")

    class Meta:
        ordering = ["line_name"]

    def __str__(self):
        return f"{self.operator.name} {self.line_name}"


class Vehicle(models.Model):
    ACTIVE = "ACTIVE"
    VOR = "VOR"
    MANUAL_STATE_CHOICES = [(ACTIVE, "Active"), (VOR, "VOR")]

    operator = models.ForeignKey(Operator, on_delete=models.CASCADE)
    bustimes_vehicle_id = models.BigIntegerField(null=True, blank=True)
    slug = models.CharField(max_length=200, blank=True)
    fleet_number = models.IntegerField(null=True, blank=True)
    fleet_code = models.CharField(max_length=50, blank=True)
    reg = models.CharField(max_length=50, blank=True)
    vehicle_type = models.CharField(max_length=200, blank=True)
    operator_name = models.CharField(max_length=200, blank=True)
    garage_name = models.CharField(max_length=200, blank=True)
    withdrawn = models.BooleanField(default=False)
    hidden_because_withdrawn = models.BooleanField(default=False)
    bustimes_name = models.CharField(max_length=200, blank=True)
    bustimes_notes = models.TextField(blank=True)
    livery_css = models.CharField(max_length=100, blank=True)
    trainer = models.BooleanField(default=False)
    manual_state = models.CharField(max_length=10, choices=MANUAL_STATE_CHOICES, default=ACTIVE)
    return_alert_armed = models.BooleanField(default=False)
    last_seen_journey_at = models.DateTimeField(null=True, blank=True)
    current_route = models.CharField(max_length=100, blank=True)
    current_destination = models.CharField(max_length=200, blank=True)
    current_allocation_level = models.CharField(max_length=20, blank=True)
    last_journey_id = models.BigIntegerField(null=True, blank=True)
    last_alert_key = models.CharField(max_length=255, blank=True)
    override_name = models.CharField(max_length=200, blank=True)
    override_notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    last_alert_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["fleet_number", "fleet_code"]
        indexes = [
            models.Index(fields=["operator"]),
            models.Index(fields=["bustimes_vehicle_id"]),
            models.Index(fields=["current_route"]),
        ]


    def __str__(self):
        return self.fleet_code or str(self.pk)


class TypeRule(models.Model):
    COMMON = "COMMON"
    UNCOMMON = "UNCOMMON"
    RARE = "RARE"
    RAIL_REPLACEMENT = "RAIL_REPLACEMENT"
    LEVEL_CHOICES = [(COMMON, "Common"), (UNCOMMON, "Uncommon"), (RARE, "Rare"), (RAIL_REPLACEMENT, "Rail Replacement")]

    operator = models.ForeignKey(Operator, on_delete=models.CASCADE)
    vehicle_type = models.CharField(max_length=200)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)

    class Meta:
        unique_together = [("operator", "vehicle_type", "route")]


class VehicleRule(models.Model):
    operator = models.ForeignKey(Operator, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    level = models.CharField(max_length=20, choices=TypeRule.LEVEL_CHOICES)

    class Meta:
        unique_together = [("operator", "vehicle", "route")]


class Alert(models.Model):
    operator = models.ForeignKey(Operator, on_delete=models.CASCADE)
    operator_name = models.CharField(max_length=200)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True)
    fleet_code = models.CharField(max_length=50)
    level = models.CharField(max_length=20)
    type = models.CharField(max_length=50)
    message = models.TextField()
    route_name = models.CharField(max_length=100, blank=True, null=True)
    destination = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]


class PollState(models.Model):
    latest_banner_operator = models.ForeignKey(Operator, on_delete=models.SET_NULL, null=True, blank=True)
    latest_banner_message = models.TextField(blank=True)
    latest_banner_created_at = models.DateTimeField(null=True, blank=True)
    last_poll_at = models.DateTimeField(null=True, blank=True)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class VehicleWatch(models.Model):
    operator = models.ForeignKey(Operator, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    route_name = models.CharField(max_length=100, blank=True)
    enabled = models.BooleanField(default=True)
    last_trigger_journey_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["vehicle__fleet_number", "vehicle__fleet_code", "route_name"]

    def __str__(self):
        return f"{self.created_by.username}: {self.vehicle.fleet_code} {self.route_name or 'ANY'}"

from django.contrib.auth.models import User

class Supervisor(models.Model):
    operator = models.ForeignKey(Operator, on_delete=models.CASCADE)
    discord_username = models.CharField(max_length=100)

    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    def __str__(self):
        return f"{self.discord_username} ({self.operator.code})"

import random
import string


def generate_invite_code():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=10))


class InviteCode(models.Model):

    code = models.CharField(
        max_length=10,
        unique=True,
        default=generate_invite_code,
        editable=False
    )

    active = models.BooleanField(default=True)

    infinite_uses = models.BooleanField(default=False)

    uses_remaining = models.IntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code

from django.contrib.auth.models import User

class OperatorFollow(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    guild_id = models.BigIntegerField(
        null=True,
        blank=True
    )

    channel_id = models.BigIntegerField(
        null=True,
        blank=True
    )

    operator = models.ForeignKey(
        Operator,
        on_delete=models.CASCADE
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            "user",
            "guild_id",
            "operator"
        )


from django.contrib.auth.models import User

class SupervisorRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    operator = models.ForeignKey("Operator", on_delete=models.CASCADE)
    discord_username = models.CharField(max_length=100)
    reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user} → {self.operator.code}"
    

from django.contrib.auth.models import User
from django.db import models


class ChangeLog(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    operator = models.ForeignKey("Operator", on_delete=models.CASCADE)

    action = models.CharField(max_length=100)
    details = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} by {self.user}"

class DiscordSubscription(models.Model):
    operator = models.ForeignKey(Operator, on_delete=models.CASCADE)

    channel_id = models.CharField(max_length=50, null=True, blank=True)
    user_id = models.CharField(max_length=50, null=True, blank=True)
    guild_id = models.CharField(max_length=50, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)