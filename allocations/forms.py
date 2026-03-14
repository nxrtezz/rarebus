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
            "operator_param_name", "training_code", "dead_code"
        ]


class VehicleOverrideForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ["vehicle_type", "override_name", "override_notes", "trainer"]


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class VehicleWatchForm(forms.ModelForm):
    class Meta:
        model = VehicleWatch
        fields = ["route_name"]
