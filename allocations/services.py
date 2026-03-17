from urllib.parse import urlencode
from datetime import datetime
import requests
import os
from django.utils import timezone

from .models import Route, Vehicle, TypeRule, VehicleRule, Alert, PollState, VehicleWatch
from asgiref.sync import sync_to_async

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")


class BustimesError(Exception):
    pass

def send_discord_dm(message):

    if not DISCORD_TOKEN:
        return

    USER_ID = "760145884427059210"  # replace this

    try:

        # open DM channel
        r = requests.post(
            "https://discord.com/api/users/@me/channels",
            headers={
                "Authorization": f"Bot {DISCORD_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"recipient_id": USER_ID},
            timeout=10,
        )

        channel_id = r.json()["id"]

        # send message
        requests.post(
            f"https://discord.com/api/channels/{channel_id}/messages",
            headers={
                "Authorization": f"Bot {DISCORD_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"content": message},
            timeout=10,
        )

    except Exception:
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


def parse_dt(value):

    if not value:
        return None

    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if timezone.is_naive(dt):
        return timezone.make_aware(dt)

    return dt


def operator_route_by_line_name(operator, line_name):

    try:
        return Route.objects.get(operator=operator, line_name__iexact=str(line_name))

    except Route.DoesNotExist:
        return None


def resolve_allocation_level(vehicle, route):

    if not vehicle or not route:
        return "COMMON"

    vehicle_rule = VehicleRule.objects.filter(vehicle=vehicle, route=route).first()

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

    requests.post(url, json={"embeds": [embed]}, timeout=30)


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

    from allocations.models import DiscordSubscription

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

    # ✅ 1. OLD SYSTEM (keep this)
    if operator.discord_webhook_url:
        try:
            post_discord_webhook(operator.discord_webhook_url, embed)
        except Exception:
            pass


    # ✅ 2. NEW SYSTEM
    subs = DiscordSubscription.objects.filter(operator=operator)

    for sub in subs:

        # 📢 Channel (BOT SEND)
        if sub.channel_id:
            try:
                requests.post(
                    f"https://discord.com/api/channels/{sub.channel_id}/messages",
                    headers={
                        "Authorization": f"Bot {DISCORD_TOKEN}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "embeds": [embed]
                    },
                    timeout=10,
                )
            except Exception:
                pass

        # 💬 DM
        elif sub.user_id:
            try:
                send_discord_dm_to_user(
                    sub.user_id,
                    embed
                )
            except Exception:
                pass

    return alert

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

        # ensure journey belongs to this operator
        if (vehicle.get("operator") or {}).get("id") != operator.code:
            continue

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

def poll_operator(operator):

    vehicles = {
        v.bustimes_vehicle_id: v
        for v in Vehicle.objects.filter(operator=operator, withdrawn=False)
    }

    try:
        journeys = fetch_recent_journeys(operator)
    except Exception as error:
        msg = f"🚨 RareBus poll error\nOperator: {operator.code} | {operator.name}\nError: {error}"
        print(msg)
        send_discord_dm(msg)
        return

    today = timezone.now().date()

    for vehicle_id, journey in journeys.items():

        vehicle = vehicles.get(vehicle_id)

        if not vehicle:
            continue

        route_name = journey.get("route_name") or ""
        destination = journey.get("destination") or ""

        dt = parse_dt(journey.get("datetime"))

        if (
            operator.rail_replacement_code
            and route_name.upper() == operator.rail_replacement_code.upper()
        ):
            level = "RAIL REPLACEMENT"

        else:
            route = operator_route_by_line_name(operator, route_name)
            level = resolve_allocation_level(vehicle, route)

        alert_key = f"{vehicle.fleet_code}|{route_name}|{level}"

        is_today = (
            dt is not None and
            timezone.localtime(dt).date() == timezone.localtime().date()
        )

        should_alert = (
            is_today and
            level in ("RARE", "UNCOMMON", "RAIL REPLACEMENT")
            and (
                vehicle.last_alert_key != alert_key
                or vehicle.last_alert_date != today
            )
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
            "last_alert_key",
            "last_alert_date",
        ])

    poll_state = PollState.get_solo()
    poll_state.last_poll_at = timezone.now()
    poll_state.save()

def poll_all_operators():

    from .models import Operator

    for operator in Operator.objects.all().order_by("name"):

        updates = 0
        errors = 0

        try:

            # refresh fleet + routes
            sync_operator_data(operator)

            vehicles = Vehicle.objects.filter(
                operator=operator,
                withdrawn=False,
                bustimes_vehicle_id__isnull=False
            )

            today = timezone.now().date()

            for vehicle in vehicles:

                try:

                    url = (
                        f"{operator.api_base_url.rstrip('/')}"
                        f"{operator.vehicle_journeys_path}"
                        f"?vehicle={vehicle.bustimes_vehicle_id}&limit=1"
                    )

                    payload = fetch_json(url)

                except Exception as error:

                    errors += 1

                    msg = f"🚨 RareBus poll error\nOperator: {operator.code} | {operator.name}\nError: {error}"

                    print(msg)

                    send_discord_dm(msg)

                    continue

                results = payload.get("results") or []

                if not results:
                    continue

                journey = results[0]

                route_name = journey.get("route_name") or ""
                destination = journey.get("destination") or ""

                dt = parse_dt(journey.get("datetime"))

                vehicle.last_seen_journey_at = dt
                vehicle.current_route = route_name
                vehicle.current_destination = destination
                vehicle.last_journey_id = journey.get("id")

                vehicle.save(update_fields=[
                    "last_seen_journey_at",
                    "current_route",
                    "current_destination",
                    "last_journey_id"
                ])

                updates += 1

        except Exception as error:

            errors += 1

            msg = f"🚨 RareBus poll error\nOperator: {operator.code} | {operator.name}\nError: {error}"

            print(msg)

            send_discord_dm(msg)
        
        if errors > 0:
            print_error = "! |"
        else:
            print_error = ""

        print(
            f"{print_error}{operator.code} | Updates: {updates} Errors: {errors} | | {operator.name}"
        )

def sync_operator_data(operator):

    fleet = fetch_operator_fleet(operator)
    routes = fetch_operator_routes(operator)

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

    for key, route in existing_routes.items():

        if key not in seen:
            route.delete()

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

def send_discord_dm_to_user(user_id, embed):
    if not DISCORD_TOKEN:
        return

    try:
        r = requests.post(
            "https://discord.com/api/users/@me/channels",
            headers={
                "Authorization": f"Bot {DISCORD_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"recipient_id": user_id},
            timeout=10,
        )

        channel_id = r.json()["id"]

        requests.post(
            f"https://discord.com/api/channels/{channel_id}/messages",
            headers={
                "Authorization": f"Bot {DISCORD_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "embeds": [embed]
            },
            timeout=10,
            )

    except Exception as e:
        print("DM failed:", e)

def send_webhook(webhook_url, payload):
    try:
        requests.post(webhook_url, json=payload, timeout=10)
    except Exception as e:
        print("Webhook failed:", e)