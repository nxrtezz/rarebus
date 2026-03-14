from django.contrib import admin
from .models import Operator, Route, Vehicle, TypeRule, VehicleRule, Alert, PollState, VehicleWatch

admin.site.register(Operator)
admin.site.register(Route)
admin.site.register(Vehicle)
admin.site.register(TypeRule)
admin.site.register(VehicleRule)
admin.site.register(Alert)
admin.site.register(PollState)
admin.site.register(VehicleWatch)
