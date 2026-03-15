from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponseForbidden, HttpResponseServerError
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.utils import timezone
import requests

from django.db.models import Count
from django.db.models.functions import TruncDate
from datetime import timedelta

from .models import Operator, Vehicle, Route, TypeRule, VehicleRule, Alert, PollState, VehicleWatch, Supervisor
from .forms import OperatorForm, VehicleOverrideForm, RegisterForm, VehicleWatchForm
from .services import sync_operator_data, poll_all_operators, poll_operator, send_test_webhook

def base_context(request):
    operators = list(Operator.objects.all())
    active_operator_id = request.GET.get("operator") or request.session.get("active_operator_id") or (operators[0].id if operators else None)
    if active_operator_id:
        request.session["active_operator_id"] = active_operator_id
    active_operator = Operator.objects.filter(id=active_operator_id).first() if active_operator_id else None
    poll_state = PollState.get_solo()
    banner = None
    if active_operator and poll_state.latest_banner_operator_id == active_operator.id and poll_state.latest_banner_message:
        banner = {"message": poll_state.latest_banner_message, "created_at": poll_state.latest_banner_created_at}
    return {
        "operators": operators,
        "active_operator_id": active_operator_id,
        "active_operator": active_operator,
        "poll_state": poll_state,
        "banner": banner,
        "github_url": settings.GITHUB_URL,
        "app_version": settings.APP_VERSION,
    }


def redirect_with_operator(request, pathname, operator_id=None):
    op = operator_id or request.POST.get("operator_id") or request.GET.get("operator") or request.session.get("active_operator_id")
    if op:
        return redirect(f"{pathname}?operator={op}")
    return redirect(pathname)


def login_view(request):
    if request.user.is_authenticated:
        return redirect("/")
    error = None
    if request.method == "POST":
        user = authenticate(request, username=request.POST.get("username"), password=request.POST.get("password"))
        if user:
            login(request, user)
            return redirect("/")
        error = "Invalid username or password"
    return render(request, "login.html", {**base_context(request), "title": "Login", "error": error})

def logout_view(request):
    if request.method == "POST":
        logout(request)
    return redirect("/login/")

@login_required
def home(request):

    ctx = base_context(request)

    alerts = list(
        Alert.objects.order_by("-created_at")[:30]
    )

    recent_ids = request.session.get("recent_operators", [])

    recent_operators = Operator.objects.filter(id__in=recent_ids)

    fleet_total = Vehicle.objects.filter(withdrawn=False).count()

    alerts_today = Alert.objects.filter(
        created_at__date=timezone.now().date()
    ).count()


    return render(
        request,
        "home.html",
        {
            **ctx,
            "title": "Home",
            "alerts": alerts,
            "recent_operators": recent_operators,
            "fleet_total": fleet_total,
            "alerts_today": alerts_today,
        },
    )


@login_required
def dashboard(request):
    ctx = base_context(request)
    operator = ctx["active_operator"]
    supervisors = []
    fleet = []
    alerts = []
    if operator:
        fleet = list(Vehicle.objects.filter(operator=operator, withdrawn=False))
        fleet.sort(key=lambda v: (v.fleet_number if v.fleet_number is not None else 10**12, v.fleet_code or ""))
        alerts = list(Alert.objects.filter(operator=operator).order_by("-created_at")[:20])
        supervisors = Supervisor.objects.filter(operator=operator)
    return render(request, "dashboard.html", {**ctx, "title": "Dashboard", "operator": operator, "fleet": fleet, "alerts": alerts, "supervisors": supervisors,})


def public_fleet_view(request, code):
    operator = Operator.objects.filter(code__iexact=code).first()
    if not operator:
        return render(request, "public_fleet.html", {**base_context(request), "title": "Fleet not found", "operator": None, "fleet": [], "alerts": []}, status=404)
    fleet = list(Vehicle.objects.filter(operator=operator, withdrawn=False))
    fleet.sort(key=lambda v: (v.fleet_number if v.fleet_number is not None else 10**12, v.fleet_code or ""))
    alerts = list(Alert.objects.filter(operator=operator).order_by("-created_at")[:20])
    return render(request, "public_fleet.html", {**base_context(request), "title": f"{operator.name} fleet", "operator": operator, "fleet": fleet, "alerts": alerts})


@login_required
def operators_view(request):
    ctx = base_context(request)
    if request.method == "POST":
        if not request.user.is_staff:
            return HttpResponseForbidden("Staff only")
        operator_id = request.POST.get("id")
        instance = Operator.objects.filter(id=operator_id).first() if operator_id else None
        form = OperatorForm(request.POST, instance=instance)
        if form.is_valid():
            operator = form.save(commit=False)
            operator.code = (operator.code or "").strip().upper()
            operator.save()
            return redirect_with_operator(request, "/dashboard/operators/", operator.id)
    else:
        form = OperatorForm()
    return render(request, "operators.html", {**ctx, "title": "Operators", "form": form, "editing": None})


@staff_member_required
def delete_operator_view(request, pk):
    operator = get_object_or_404(Operator, pk=pk)
    operator.delete()
    return redirect("/dashboard/operators/")


@staff_member_required
def sync_view(request):
    operator_id = request.GET.get("operator") or request.session.get("active_operator_id")
    operator = Operator.objects.filter(id=operator_id).first()
    if not operator:
        return redirect("/dashboard/operators/")
    try:
        sync_operator_data(operator)
        return redirect_with_operator(request, "/dashboard/", operator.id)
    except Exception as error:
        return HttpResponseServerError(f"Sync failed: {error}")


@staff_member_required
def poll_view(request):
    operator_id = request.POST.get("operator_id") or request.GET.get("operator") or request.session.get("active_operator_id")
    if operator_id:
        operator = Operator.objects.filter(id=operator_id).first()
        if operator:
            poll_operator(operator)
    else:
        poll_all_operators()
    return redirect_with_operator(request, "/dashboard/", operator_id)


@staff_member_required
def test_webhook_view(request, pk):
    operator = get_object_or_404(Operator, pk=pk)
    send_test_webhook(operator)
    return redirect_with_operator(request, "/dashboard/operators/", operator.id)


@login_required
def withdrawn_view(request):
    ctx = base_context(request)
    operator = ctx["active_operator"]
    withdrawn_fleet = []
    if operator:
        withdrawn_fleet = list(Vehicle.objects.filter(operator=operator, withdrawn=True))
        withdrawn_fleet.sort(key=lambda v: (v.fleet_number if v.fleet_number is not None else 10**12, v.fleet_code or ""))
    return render(request, "withdrawn.html", {**ctx, "title": "Withdrawn vehicles", "operator": operator, "withdrawn_fleet": withdrawn_fleet})


@staff_member_required
def restore_vehicle_view(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    vehicle.withdrawn = False
    vehicle.hidden_because_withdrawn = False
    vehicle.manual_state = "ACTIVE"
    vehicle.save()
    return redirect_with_operator(request, "/dashboard/fleet/withdrawn/", vehicle.operator_id)


@login_required
def vehicle_view(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if vehicle.withdrawn:
        return redirect("/")
    operator = vehicle.operator
    routes = list(Route.objects.filter(operator=operator))
    routes.sort(key=lambda r: r.line_name)
    type_rules = list(TypeRule.objects.filter(operator=operator, vehicle_type=vehicle.vehicle_type))
    vehicle_rules = list(VehicleRule.objects.filter(vehicle=vehicle))
    watches = list(VehicleWatch.objects.filter(vehicle=vehicle, created_by=request.user)) if request.user.is_authenticated else []
    watch_form = VehicleWatchForm()
    ctx = base_context(request)
    return render(request, "vehicle.html", {
        **ctx,
        "title": f"Vehicle {vehicle.fleet_code}",
        "operator": operator,
        "vehicle": vehicle,
        "routes": routes,
        "type_rules": type_rules,
        "vehicle_rules": vehicle_rules,
        "watches": watches,
        "watch_form": watch_form,
    })


@staff_member_required
def vehicle_state_view(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    manual_state = request.POST.get("manual_state", "ACTIVE")
    vehicle.manual_state = manual_state
    if manual_state == "VOR":
        vehicle.return_alert_armed = True
        vehicle.current_allocation_level = ""
    vehicle.save()
    return redirect_with_operator(request, f"/dashboard/fleet/{pk}/", vehicle.operator_id)


@staff_member_required
def vehicle_override_view(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    form = VehicleOverrideForm(request.POST, instance=vehicle)
    if form.is_valid():
        form.save()
    return redirect_with_operator(request, f"/dashboard/fleet/{pk}/", vehicle.operator_id)


@login_required
def watch_create_view(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    form = VehicleWatchForm(request.POST)
    if form.is_valid():
        watch = form.save(commit=False)
        watch.operator = vehicle.operator
        watch.vehicle = vehicle
        watch.created_by = request.user
        watch.route_name = (watch.route_name or "").strip()
        watch.save()
    return redirect_with_operator(request, f"/dashboard/fleet/{pk}/", vehicle.operator_id)


@login_required
def watch_delete_view(request, pk, watch_id):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    watch = get_object_or_404(VehicleWatch, pk=watch_id, vehicle=vehicle)
    if watch.created_by_id != request.user.id and not request.user.is_staff:
        return HttpResponseForbidden("Not allowed")
    watch.delete()
    return redirect_with_operator(request, f"/dashboard/fleet/{pk}/", vehicle.operator_id)


@login_required
def type_rules_view(request):
    ctx = base_context(request)
    operator = ctx["active_operator"]
    vehicle_types = []
    selected_type = request.GET.get("vehicleType") or ""
    routes = []
    rules = []
    if operator:
        vehicle_types = sorted({v.vehicle_type for v in Vehicle.objects.filter(operator=operator, withdrawn=False) if v.vehicle_type}, key=lambda x: x.lower())
        if not selected_type and vehicle_types:
            selected_type = vehicle_types[0]
        routes = list(Route.objects.filter(operator=operator))
        routes.sort(key=lambda r: r.line_name)
        if selected_type:
            rules = list(TypeRule.objects.filter(operator=operator, vehicle_type=selected_type))
    return render(request, "type_rules.html", {**ctx, "title": "Type rules", "operator": operator, "vehicle_types": vehicle_types, "selected_type": selected_type, "routes": routes, "rules": rules})


@staff_member_required
def type_rules_save_view(request):
    operator = get_object_or_404(Operator, pk=request.POST.get("operator_id"))
    vehicle_type = request.POST.get("vehicle_type", "")
    route_ids = request.POST.getlist("levels_route_id")
    levels = request.POST.getlist("levels_level")
    for route_id, level in zip(route_ids, levels):
        route = get_object_or_404(Route, pk=route_id)
        TypeRule.objects.update_or_create(
            operator=operator,
            vehicle_type=vehicle_type,
            route=route,
            defaults={"level": level},
        )
    return redirect(f"/dashboard/rules/types/?operator={operator.id}&vehicleType={vehicle_type}")


@staff_member_required
def vehicle_rule_save_view(request):
    operator = get_object_or_404(Operator, pk=request.POST.get("operator_id"))
    vehicle = get_object_or_404(Vehicle, pk=request.POST.get("vehicle_id"))
    route = get_object_or_404(Route, pk=request.POST.get("route_id"))
    VehicleRule.objects.update_or_create(
        operator=operator,
        vehicle=vehicle,
        route=route,
        defaults={"level": request.POST.get("level", "RARE")},
    )
    return redirect(f"/dashboard/fleet/{vehicle.id}/?operator={operator.id}")


@login_required
def alerts_view(request):
    ctx = base_context(request)
    operator = ctx["active_operator"]
    alerts = list(Alert.objects.filter(operator=operator).order_by("-created_at")[:200]) if operator else list(Alert.objects.order_by("-created_at")[:200])
    return render(request, "alerts.html", {**ctx, "title": "Alerts", "operator": operator, "alerts": alerts})


@staff_member_required
def delete_alert(request, alert_id):
    alert = get_object_or_404(Alert, id=alert_id)
    operator_id = alert.operator.id
    message = alert.message
    alert.delete()
    state = PollState.get_solo()
    if state.latest_banner_message == message:
        state.latest_banner_message = ""
        state.latest_banner_created_at = None
        state.latest_banner_operator = None
        state.save()
    return redirect(f"/dashboard/alerts/?operator={operator_id}")

@login_required
def stats_view(request):
    ctx = base_context(request)
    operator = ctx["active_operator"]

    total = 0
    rare = 0
    uncommon = 0
    watches = 0

    level_stats = []
    route_stats = []
    type_stats = []
    alert_trend = []

    if operator:

        total = Vehicle.objects.filter(
            operator=operator,
            withdrawn=False
        ).count()

        rare = Alert.objects.filter(
            operator=operator,
            level="RARE"
        ).count()

        uncommon = Alert.objects.filter(
            operator=operator,
            level="UNCOMMON"
        ).count()

        watches = VehicleWatch.objects.filter(
            operator=operator
        ).count()

        level_stats = list(
            Alert.objects
            .filter(operator=operator)
            .values("level")
            .annotate(count=Count("id"))
        )

        route_stats = list(
            Alert.objects
            .filter(operator=operator)
            .exclude(route_name__isnull=True)
            .exclude(route_name="")
            .values("route_name")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        type_stats = list(
            Vehicle.objects
            .filter(operator=operator, withdrawn=False)
            .values("vehicle_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        last_week = timezone.now() - timedelta(days=7)

        alert_trend = list(
            Alert.objects
            .filter(operator=operator, created_at__gte=last_week)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

    return render(request, "stats.html", {
        **ctx,
        "title": "Statistics",
        "operator": operator,

        "total": total,
        "rare": rare,
        "uncommon": uncommon,
        "watches": watches,

        "level_stats": level_stats,
        "route_stats": route_stats,
        "type_stats": type_stats,
        "alert_trend": alert_trend,
    })

from .models import InviteCode
from .forms import RegisterForm

def register_view(request):

    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():

            user = form.save(commit=False)   # ← THIS WAS MISSING

            invite_code_value = form.cleaned_data.get("invite_code")

            valid_code = None

            if invite_code_value:
                valid_code = InviteCode.objects.filter(
                    code=invite_code_value,
                    active=True
                ).first()

            if valid_code:

                user.is_active = True

                if not valid_code.infinite_uses:
                    valid_code.uses_remaining -= 1

                    if valid_code.uses_remaining <= 0:
                        valid_code.active = False

                    valid_code.save()

            else:
                user.is_active = True # Allow registration without invite code, but require admin approval

            user.save()

            try:
                send_new_user_webhook(user)
            except Exception:
                pass

            messages.success(
                request,
                "Account created. If you used a valid invite code your account is active. Otherwise it requires admin approval."
            )

            return redirect("/login/")

    else:
        form = RegisterForm()

    return render(request, "register.html", {
        "title": "Register",
        "form": form
    })


@login_required
def clear_alerts(request):

    operator_id = request.POST.get("operator") or request.GET.get("operator")

    if operator_id:
        Alert.objects.filter(operator_id=operator_id).delete()
    else:
        Alert.objects.all().delete()

    state = PollState.get_solo()
    state.latest_banner_message = ""
    state.latest_banner_created_at = None
    state.latest_banner_operator = None
    state.save()

    return redirect("/dashboard/alerts/")



@login_required
def operator_request_view(request):

    if request.method != "POST":
        return redirect("/dashboard/operators/")

    name = request.POST.get("name")
    code = request.POST.get("code")
    notes = request.POST.get("notes")

    webhook = settings.OPERATOR_REQUEST_WEBHOOK

    embed = {
        "title": "Operator request",
        "color": 0xF0AD4E,
        "fields": [
            {"name": "Requested by", "value": request.user.username, "inline": True},
            {"name": "Operator name", "value": name, "inline": True},
            {"name": "Bustimes code", "value": code, "inline": True},
            {"name": "Notes", "value": notes or "None", "inline": False},
        ],
    }

    try:
        requests.post(webhook, json={"embeds": [embed]}, timeout=10)
    except Exception:
        pass

    return redirect("/dashboard/operators/")

import requests
from django.conf import settings


def send_new_user_webhook(user):

    if not settings.NEW_USER_WEBHOOK:
        return

    approve_url = f"https://eeveeit.uk/admin/approve-user/{user.id}/"
    reject_url = f"https://eeveeit.uk/admin/reject-user/{user.id}/"

    embed = {
        "title": "New RareBus user registered",
        "color": 0xF0AD4E,
        "fields": [
            {"name": "Username", "value": user.username, "inline": True},
            {"name": "Email", "value": user.email or "None", "inline": True},
            {"name": "Name", "value": f"{user.first_name} {user.last_name}", "inline": False},
            {"name": "Approve", "value": f"[Approve User]({approve_url})", "inline": True},
            {"name": "Reject", "value": f"[Reject User]({reject_url})", "inline": True},
        ],
    }

    payload = {
        "content": "<@760145884427059210>",
        "embeds": [embed],
        "allowed_mentions": {"users": ["760145884427059210"]},
    }

    requests.post(settings.NEW_USER_WEBHOOK, json=payload)

from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required


@staff_member_required
def approve_user(request, user_id):

    user = get_object_or_404(User, id=user_id)

    user.is_active = True
    user.save()

    return render(request, "simple_message.html", {
        "title": "User approved",
        "message": f"{user.username} has been activated."
    })


@staff_member_required
def reject_user(request, user_id):

    user = get_object_or_404(User, id=user_id)

    username = user.username
    user.delete()

    return render(request, "simple_message.html", {
        "title": "User rejected",
        "message": f"{username} has been deleted."
    })


from .models import OperatorCustomCode


@staff_member_required
def operator_settings_view(request):

    ctx = base_context(request)

    operator = ctx["active_operator"]

    custom_codes = []
    if operator:
        custom_codes = OperatorCustomCode.objects.filter(operator=operator)

    if request.method == "POST":

        action = request.POST.get("action")

        if action == "update_operator":

            operator.training_code = request.POST.get("training_code")
            operator.dead_code = request.POST.get("dead_code")
            operator.rail_replacement_code = request.POST.get("rail_replacement_code")

            operator.discord_webhook_url = request.POST.get("discord_webhook_url")

            operator.save()

        elif action == "add_code":

            OperatorCustomCode.objects.create(
                operator=operator,
                code=request.POST.get("code").upper(),
                display_name=request.POST.get("display_name")
            )

        return redirect(f"/dashboard/operators/settings/?operator={operator.id}")

    return render(
        request,
        "operator_settings.html",
        {
            **ctx,
            "title": "Operator Settings",
            "operator": operator,
            "custom_codes": custom_codes
        }
    )
