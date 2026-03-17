from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Operator, Vehicle, VehicleWatch


class OperatorForm(forms.ModelForm):
    class Meta:
        model = Operator
        fields = [
            "name", "code", "theme_color", "accent_color", "discord_webhook_url",
            "api_base_url", "vehicles_path", "services_path", "vehicle_journeys_path",
            "operator_param_name", "training_code", "dead_code", "rail_replacement_code"
        ]


class VehicleOverrideForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ["vehicle_type", "override_name", "override_notes", "trainer"]


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    invite_code = forms.CharField(max_length=50, required=False)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "password1",
            "password2",
            "invite_code",
        ]


class VehicleWatchForm(forms.ModelForm):
    class Meta:
        model = VehicleWatch
        fields = ["route_name"]

from django import forms
from .models import SupervisorRequest

class SupervisorRequestForm(forms.ModelForm):
    class Meta:
        model = SupervisorRequest
        fields = ["operator", "discord_username", "reason"]