from urllib.parse import urlencode
from datetime import datetime
import requests
from django.utils import timezone

from .models import Route, Vehicle, TypeRule, VehicleRule, Alert, PollState, VehicleWatch
from .models import OperatorFollow
from asgiref.sync import sync_to_async
import requests


class BustimesError(Exception):
    pass


def fetch_json(url):
    response = requests.get(url, headers={"accept": "application/json"}, timeout=30)
    if not response.ok:
        raise BustimesError(f"Bustimes request failed {response.status_code} {response.reason}")
    return response.json()


def with_params(base_url, params):
    filtered = {k: v for k, v in (params or {}).items() if v not in (None, "")}
    return f"{base_url}?{urlencode(filtered)}" if filtered else base_url


def fetch_operator_fleet(operator):
    endpoint = f"{operator.api_base_url.rstrip('/')}{operator.vehicles_path}"
    url = with_params(endpoint, {operator.operator_param_name: operator.code, "limit": 500})
    payload = fetch_json(url)

    results = payload.get("results", [])
    fleet = []

    for item in results:
        livery = item.get("livery") or {}

        fleet.append({
            "bustimes_vehicle_id": item.get("id"),
            "slug": item.get("slug", ""),
            "fleet_number": item.get("fleet_number"),
            "fleet_code": item.get("fleet_code", ""),
            "reg": item.get("reg", ""),
            "vehicle_type": (item.get("vehicle_type") or {}).get("name", ""),
            "operator_name": (item.get("operator") or {}).get("name", operator.name),
            "garage_name": (item.get("garage") or {}).get("name", ""),
            "withdrawn": bool(item.get("withdrawn")),
            "bustimes_name": item.get("name", ""),
            "bustimes_notes": item.get("notes", ""),
            "livery_css": livery.get("left", ""),
        })

    return fleet


def fetch_operator_routes(operator):
    endpoint = f"{operator.api_base_url.rstrip('/')}{operator.services_path}"
    url = with_params(endpoint, {operator.operator_param_name: operator.code, "limit": 500})
    payload = fetch_json(url)

    seen = set()
    routes = []

    for item in payload.get("results", []):
        line_name = item.get("line_name") or item.get("name")

        if not line_name:
            continue

        key = line_name.lower()

        if key in seen:
            continue

        seen.add(key)

        routes.append({
            "line_name": line_name,
            "description": item.get("description", ""),
            "slug": item.get("slug", ""),
            "mode": item.get("mode", "bus"),
        })

    routes.sort(key=lambda x: x["line_name"])

    return routes


def fetch_latest_vehicle_journey(operator, bustimes_vehicle_id):
    endpoint = f"{operator.api_base_url.rstrip('/')}{operator.vehicle_journeys_path}"
    url = with_params(endpoint, {"vehicle": bustimes_vehicle_id, "limit": 1})
    payload = fetch_json(url)

    item = (payload.get("results") or [None])[0]

    if not item:
        return None

    vehicle_data = item.get("vehicle") or {}

    return {
        "id": item.get("id"),
        "datetime": item.get("datetime"),
        "route_name": item.get("route_name", ""),
        "destination": item.get("destination", ""),
        "trip_id": item.get("trip_id"),
        "vehicle_bustimes_id": vehicle_data.get("id") or bustimes_vehicle_id,
        "fleet_code": vehicle_data.get("fleet_code", ""),
    }


def sync_operator_data(operator):

    fleet = fetch_operator_fleet(operator)
    routes = fetch_operator_routes(operator)

    # -------------------------
    # Sync routes WITHOUT deleting rules
    # -------------------------

    existing_routes = {
        r.line_name.lower(): r
        for r in Route.objects.filter(operator=operator)
    }

    seen = set()

    for item in routes:

        key = item["line_name"].lower()

        seen.add(key)

        route = existing_routes.get(key)

        if route:
            route.description = item.get("description", "")
            route.slug = item.get("slug", "")
            route.mode = item.get("mode", "bus")
            route.save()

        else:
            Route.objects.create(
                operator=operator,
                **item
            )

    # Optional: remove routes that no longer exist in Bustimes
    for key, route in existing_routes.items():
        if key not in seen:
            route.delete()

    # -------------------------
    # Sync vehicles
    # -------------------------

    existing = {
        str(v.bustimes_vehicle_id): v
        for v in Vehicle.objects.filter(operator=operator)
    }

    for item in fleet:

        key = str(item.get("bustimes_vehicle_id"))

        prev = existing.get(key)

        if prev:

            trainer = prev.trainer
            manual_state = prev.manual_state
            return_alert_armed = prev.return_alert_armed
            last_seen_journey_at = prev.last_seen_journey_at
            current_route = prev.current_route
            current_destination = prev.current_destination
            current_allocation_level = prev.current_allocation_level
            last_journey_id = prev.last_journey_id
            last_alert_key = prev.last_alert_key
            last_alert_date = prev.last_alert_date
            override_name = prev.override_name
            override_notes = prev.override_notes
            vehicle_type = prev.vehicle_type or item["vehicle_type"]

            for field, value in item.items():
                setattr(prev, field, value)

            prev.trainer = trainer
            prev.manual_state = manual_state
            prev.return_alert_armed = return_alert_armed
            prev.hidden_because_withdrawn = bool(item["withdrawn"])
            prev.last_seen_journey_at = last_seen_journey_at
            prev.current_route = current_route
            prev.current_destination = current_destination
            prev.current_allocation_level = current_allocation_level
            prev.last_journey_id = last_journey_id
            prev.last_alert_key = last_alert_key
            prev.last_alert_date = last_alert_date
            prev.override_name = override_name
            prev.override_notes = override_notes
            prev.vehicle_type = vehicle_type if vehicle_type else item["vehicle_type"]

            prev.save()

        else:

            Vehicle.objects.create(
                operator=operator,
                manual_state="ACTIVE",
                return_alert_armed=False,
                hidden_because_withdrawn=bool(item["withdrawn"]),
                override_name="",
                override_notes="",
                **item,
            )



def operator_route_by_line_name(operator, line_name):

    try:

        return Route.objects.get(
            operator=operator,
            line_name__iexact=str(line_name)
        )

    except Route.DoesNotExist:

        return None


def resolve_allocation_level(vehicle, route):

    if not vehicle or not route:
        return "COMMON"

    vehicle_rule = VehicleRule.objects.filter(
        vehicle=vehicle,
        route=route
    ).first()

    if vehicle_rule:
        return vehicle_rule.level

    type_rule = TypeRule.objects.filter(
        operator=vehicle.operator,
        vehicle_type=vehicle.vehicle_type,
        route=route
    ).first()

    if type_rule:
        return type_rule.level

    return "COMMON"


def level_color(level):

    if level == "RARE":
        return 0xE55353

    if level == "UNCOMMON":
        return 0xF0AD4E

    return 0x2DCE89


def post_discord_webhook(url, embed):

    if not url:
        return

    response = requests.post(url, json={"embeds": [embed]}, timeout=30)

    response.raise_for_status()


def emit_alert(operator, vehicle, level, type_name, message, route_name=None, destination=None):

    created_at = timezone.now()

    alert = Alert.objects.create(
        operator=operator,
        operator_name=operator.name,
        vehicle=vehicle,
        fleet_code=vehicle.fleet_code if vehicle else "",
        level=level,
        type=type_name,
        message=message,
        route_name=route_name,
        destination=destination,
        created_at=created_at,
    )

    if level == "RARE":

        poll_state = PollState.get_solo()

        poll_state.latest_banner_operator = operator
        poll_state.latest_banner_message = message
        poll_state.latest_banner_created_at = created_at

        poll_state.save()

    if operator.discord_webhook_url:

        embed = {
            "title": "Vehicle returned to service" if type_name == "VOR_RETURN" else "Allocation alert",
            "description": message,
            "color": level_color(level),
            "fields": [
                {"name": "Operator", "value": operator.name, "inline": True},
                {"name": "Fleet", "value": vehicle.fleet_code if vehicle else "N/A", "inline": True},
                {"name": "Type", "value": vehicle.vehicle_type if vehicle else "N/A", "inline": True},
                {"name": "Level", "value": level, "inline": True},
                {"name": "Route", "value": route_name or "Unknown", "inline": True},
                {"name": "Destination", "value": destination or "Unknown", "inline": True},
            ],
            "timestamp": created_at.isoformat(),
        }

        try:
            post_discord_webhook(operator.discord_webhook_url, embed)
        except Exception:
            pass

    send_discord_follow_alerts(
        operator,
        vehicle,
        level,
        message,
        route_name,
        destination
    )

    return alert

def parse_dt(value):

    if not value:
        return None

    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if timezone.is_naive(dt):
        return timezone.make_aware(dt)

    return dt


def maybe_emit_watch_alerts(operator, vehicle, route_name, destination, journey_id):

    watches = VehicleWatch.objects.filter(
        operator=operator,
        vehicle=vehicle,
        enabled=True
    )

    for watch in watches:

        route_ok = (
            not watch.route_name
            or (route_name and watch.route_name.lower() == route_name.lower())
        )

        if route_ok and watch.last_trigger_journey_id != journey_id:

            if watch.route_name:
                msg = f"{vehicle.fleet_code} has tracked on watched route {route_name}."
            else:
                msg = f"{vehicle.fleet_code} has tracked."

            emit_alert(
                operator,
                vehicle,
                "UNCOMMON",
                "WATCH",
                msg,
                route_name=route_name,
                destination=destination
            )

            watch.last_trigger_journey_id = journey_id

            watch.save(update_fields=["last_trigger_journey_id"])

def poll_operator(operator):

    vehicles = {
        v.bustimes_vehicle_id: v
        for v in Vehicle.objects.filter(operator=operator, withdrawn=False)
    }

    try:
        journeys = fetch_recent_journeys(operator)
    except Exception as error:
        print(f"Recent journey fetch failed for {operator.name}: {error}")
        return

    today = timezone.now().date()

    for vehicle_id, journey in journeys.items():

        vehicle = vehicles.get(vehicle_id)

        if not vehicle:
            continue

        route_name = journey.get("route_name") or ""
        destination = journey.get("destination") or ""

        dt = parse_dt(journey.get("datetime"))

        # -------------------------
        # Determine allocation level
        # -------------------------

        if (
            operator.rail_replacement_code
            and route_name.upper() == operator.rail_replacement_code.upper()
        ):
            level = "RAIL_REPLACEMENT"

        else:
            route = operator_route_by_line_name(operator, route_name)
            level = resolve_allocation_level(vehicle, route)

        # -------------------------
        # Prevent duplicate alerts
        # -------------------------

        alert_key = f"{vehicle.fleet_code}|{route_name}|{level}"

        should_alert = (
            level in ("RARE", "UNCOMMON", "RAIL_REPLACEMENT")
            and vehicle.last_alert_key != alert_key
        )

        if should_alert:

            emit_alert(
                operator,
                vehicle,
                level,
                "ALLOCATION",
                f"{vehicle.fleet_code} is on {route_name}. Marked {level.lower()} for {vehicle.vehicle_type or 'this vehicle'}.",
                route_name=route_name,
                destination=destination,
            )

            vehicle.last_alert_key = alert_key
            vehicle.last_alert_date = today

        # -------------------------
        # Long absence detection
        # -------------------------

        if vehicle.last_seen_journey_at:

            gap = timezone.now() - vehicle.last_seen_journey_at

            if gap.days >= 14 and vehicle.last_journey_id != journey["id"]:

                emit_alert(
                    operator,
                    vehicle,
                    "UNCOMMON",
                    "RETURN_AFTER_LONG_ABSENCE",
                    f"{vehicle.fleet_code} has tracked after {gap.days} days.",
                    route_name=route_name,
                    destination=destination
                )

        # -------------------------
        # Update vehicle state
        # -------------------------

        vehicle.last_seen_journey_at = dt
        vehicle.current_route = route_name
        vehicle.current_destination = destination
        vehicle.current_allocation_level = level
        vehicle.last_journey_id = journey["id"]

        vehicle.save(update_fields=[
            "last_seen_journey_at",
            "current_route",
            "current_destination",
            "current_allocation_level",
            "last_journey_id",
            "last_alert_key"
        ])


        # -------------------------
        # Watch alerts
        # -------------------------

        maybe_emit_watch_alerts(
            operator,
            vehicle,
            route_name,
            destination,
            journey["id"]
        )

    poll_state = PollState.get_solo()
    poll_state.last_poll_at = timezone.now()
    poll_state.save()


def poll_all_operators():

    from .models import Operator

    for operator in Operator.objects.all().order_by("name"):

        try:

            poll_operator(operator)

        except Exception as error:

            print(f"Operator poll failed {operator.name}: {error}")


def send_test_webhook(operator):

    emit_alert(
        operator,
        None,
        "UNCOMMON",
        "WEBHOOK_TEST",
        "Webhook test message from Bus Allocations.",
        route_name="TEST",
        destination="Webhook",
    )


def fetch_recent_journeys(operator):
    endpoint = f"{operator.api_base_url.rstrip('/')}{operator.vehicle_journeys_path}"

    url = with_params(endpoint, {
        operator.operator_param_name: operator.code,
        "limit": 500
    })

    payload = fetch_json(url)

    journeys = {}

    for item in payload.get("results", []):
        vehicle = item.get("vehicle") or {}
        vehicle_id = vehicle.get("id")

        if not vehicle_id:
            continue

        service = item.get("service") or {}

        route_name = (
            service.get("line_name")
            or item.get("line_name")
            or item.get("route_name")
            or ""
        )

        journeys[vehicle_id] = {
            "id": item.get("id"),
            "datetime": item.get("datetime"),
            "route_name": route_name,
            "destination": item.get("destination", ""),
        }


    return journeys

def send_discord_follow_alerts(operator, vehicle, level, message, route_name, destination):

    follows = OperatorFollow.objects.filter(
        operator=operator,
        guild_id__isnull=False,
        channel_id__isnull=False
    )

    for follow in follows:

        webhook = operator.discord_webhook_url

        if not webhook:
            continue

        embed = {
            "title": "RareBus Alert",
            "description": message,
            "color": level_color(level),
            "fields": [
                {"name": "Fleet", "value": vehicle.fleet_code if vehicle else "N/A", "inline": True},
                {"name": "Operator", "value": operator.name, "inline": True},
                {"name": "Route", "value": route_name or "Unknown", "inline": True},
                {"name": "Destination", "value": destination or "Unknown", "inline": True},
                {"name": "Level", "value": level, "inline": True}
            ]
        }

        payload = {
            "embeds": [embed]
        }

        try:
            requests.post(webhook, json=payload, timeout=10)
        except Exception:
            pass

    follows = OperatorFollow.objects.filter(
        operator=operator,
        guild_id__isnull=False
    )

    for follow in follows:

        url = f"https://discord.com/api/channels/{follow.channel_id}/messages"

        payload = {
            "content": f"<@&{follow.guild_id}>",
            "embeds": [{
                "title": "RareBus Alert",
                "description": message,
                "color": level_color(level),
                "fields": [
                    {"name": "Fleet", "value": vehicle.fleet_code},
                    {"name": "Operator", "value": operator.name},
                    {"name": "Route", "value": route_name or "Unknown"},
                    {"name": "Destination", "value": destination or "Unknown"},
                    {"name": "Level", "value": level}
                ]
            }]
        }

        try:
            requests.post(url, json=payload)
        except:
            pass
