import os
import sys

# ----------------------------
# ADD PROJECT ROOT
# ----------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# ----------------------------
# DJANGO SETUP
# ----------------------------

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# ----------------------------
# IMPORTS
# ----------------------------

from asgiref.sync import sync_to_async
import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
from django.utils import timezone

from allocations.models import Alert, Vehicle, Operator, OperatorFollow, PollState

ADMIN_ID = int(os.getenv("DISCORD_ADMIN_USER_ID"))

async def admin_check(interaction):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message(
            "Not authorised.",
            ephemeral=True
        )
        return False
    return True

# ----------------------------
# BOT TOKEN
# ----------------------------

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# ----------------------------
# BOT SETUP
# ----------------------------

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


# ----------------------------
# BOT READY
# ----------------------------

@bot.event
async def on_ready():
    print(f"RareBus bot online as {bot.user}")

    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} commands")


# ----------------------------
# /last-rare
# ----------------------------

@bot.tree.command(name="last-rare", description="Show the latest rare allocation")
async def last_rare(interaction: discord.Interaction):

    alert = await sync_to_async(
        lambda: Alert.objects.filter(level="RARE").order_by("-created_at").first()
    )()

    if not alert:
        await interaction.response.send_message("No rare allocations recorded.")
        return

    embed = discord.Embed(
        title="Latest Rare Allocation",
        color=0xE55353
    )

    embed.add_field(name="Fleet", value=alert.fleet_code)
    embed.add_field(name="Operator", value=alert.operator_name)
    embed.add_field(name="Route", value=alert.route_name or "Unknown")
    embed.add_field(name="Destination", value=alert.destination or "Unknown")

    embed.timestamp = alert.created_at

    await interaction.response.send_message(embed=embed)


# ----------------------------
# /last-uncommon
# ----------------------------

@bot.tree.command(name="last-uncommon", description="Show latest uncommon allocation")
async def last_uncommon(interaction: discord.Interaction):

    alert = await sync_to_async(
        lambda: Alert.objects.filter(level="UNCOMMON").order_by("-created_at").first()
    )()

    if not alert:
        await interaction.response.send_message("No uncommon allocations recorded.")
        return

    embed = discord.Embed(
        title="Latest Uncommon Allocation",
        color=0xF0AD4E
    )

    embed.add_field(name="Fleet", value=alert.fleet_code)
    embed.add_field(name="Operator", value=alert.operator_name)
    embed.add_field(name="Route", value=alert.route_name or "Unknown")
    embed.add_field(name="Destination", value=alert.destination or "Unknown")

    embed.timestamp = alert.created_at

    await interaction.response.send_message(embed=embed)


# ----------------------------
# /fleet
# ----------------------------

@bot.tree.command(name="fleet", description="Show information about a vehicle")
async def fleet(interaction: discord.Interaction, operator_code: str, fleet_code: str):

    operator = await sync_to_async(
        lambda: Operator.objects.filter(code__iexact=operator_code).first()
    )()

    if not operator:
        await interaction.response.send_message("Operator not found.")
        return

    vehicle = await sync_to_async(
        lambda: Vehicle.objects.filter(
            operator=operator,
            fleet_code__iexact=fleet_code
        ).first()
    )()

    if not vehicle:
        await interaction.response.send_message("Vehicle not found.")
        return

    embed = discord.Embed(
        title=f"{vehicle.fleet_code} • {operator.name}",
        color=0x2DCE89
    )

    embed.add_field(name="Vehicle Type", value=vehicle.vehicle_type or "Unknown", inline=False)
    embed.add_field(name="Registration", value=vehicle.reg or "Unknown", inline=True)
    embed.add_field(name="Current Route", value=vehicle.current_route or "Not tracking", inline=True)
    embed.add_field(name="Destination", value=vehicle.current_destination or "Unknown", inline=True)

    if vehicle.last_seen_journey_at:
        embed.add_field(
            name="Last Seen",
            value=vehicle.last_seen_journey_at.strftime("%d %b %Y %H:%M"),
            inline=False
        )

    await interaction.response.send_message(embed=embed)


# ----------------------------
# /route
# ----------------------------

@bot.tree.command(name="route", description="Show vehicles seen on a route in the last 20 minutes")
async def route(interaction: discord.Interaction, operator_code: str, route_name: str):

    operator = await sync_to_async(
        lambda: Operator.objects.filter(code__iexact=operator_code).first()
    )()

    if not operator:
        await interaction.response.send_message("Operator not found.")
        return

    cutoff = timezone.now() - timedelta(minutes=20)

    vehicles = await sync_to_async(
        lambda: list(
            Vehicle.objects.filter(
                operator=operator,
                current_route__iexact=route_name,
                last_seen_journey_at__gte=cutoff
            ).order_by("fleet_number")
        )
    )()

    if not vehicles:
        await interaction.response.send_message(
            f"No vehicles seen on **{route_name}** in the last 20 minutes."
        )
        return

    embed = discord.Embed(
        title=f"{operator.name} • Route {route_name}",
        description="Vehicles seen in the last 20 minutes",
        color=0x3498DB
    )

    vehicle_list = "\n".join(
        f"{v.fleet_code} → {v.current_destination or 'Unknown'}"
        for v in vehicles
    )

    embed.add_field(name="Vehicles", value=vehicle_list, inline=False)

    await interaction.response.send_message(embed=embed)


# ----------------------------
# /follow
# ----------------------------

@bot.tree.command(name="follow", description="Follow an operator for alerts")
async def follow(interaction: discord.Interaction, operator_code: str):

    operator = await sync_to_async(
        lambda: Operator.objects.filter(code__iexact=operator_code).first()
    )()

    if not operator:
        await interaction.response.send_message("Operator not found.")
        return

    await sync_to_async(OperatorFollow.objects.update_or_create)(
        guild_id=interaction.guild_id,
        operator=operator,
        defaults={"channel_id": interaction.channel_id}
    )

    await interaction.response.send_message(
        f"Now sending **{operator.name}** alerts to this channel."
    )


# ----------------------------
# /unfollow
# ----------------------------

@bot.tree.command(name="unfollow", description="Stop alerts for an operator")
async def unfollow(interaction: discord.Interaction, operator_code: str):

    operator = await sync_to_async(
        lambda: Operator.objects.filter(code__iexact=operator_code).first()
    )()

    if not operator:
        await interaction.response.send_message("Operator not found.")
        return

    await sync_to_async(
        OperatorFollow.objects.filter(
            guild_id=interaction.guild_id,
            operator=operator
        ).delete
    )()

    await interaction.response.send_message(
        f"Stopped alerts for **{operator.name}**."
    )

# ----------------------------
# /status
# ----------------------------

@bot.tree.command(name="status", description="RareBus system status")
async def status(interaction: discord.Interaction):

    if not await admin_check(interaction):
        return

    poll = await sync_to_async(PollState.get_solo)()

    operators = await sync_to_async(lambda: Operator.objects.count())()

    tracked = await sync_to_async(
        lambda: Vehicle.objects.filter(last_seen_journey_at__isnull=False).count()
    )()

    if poll.last_poll_at:

        delta = timezone.now() - poll.last_poll_at
        minutes = int(delta.total_seconds() / 60)

        if minutes < 10:
            health = "🟢 Healthy"
            colour = 0x2ECC71
        elif minutes < 20:
            health = "🟡 Delayed"
            colour = 0xF1C40F
        else:
            health = "🔴 Poll stalled"
            colour = 0xE74C3C

        last_poll = poll.last_poll_at.strftime("%d %b %Y %H:%M")

    else:
        health = "🔴 No poll recorded"
        last_poll = "Never"
        colour = 0xE74C3C

    embed = discord.Embed(
        title="RareBus System Status",
        colour=colour
    )

    embed.add_field(name="System Health", value=health)
    embed.add_field(name="Last Poll", value=last_poll)
    embed.add_field(name="Operators", value=str(operators))
    embed.add_field(name="Vehicles Tracking", value=str(tracked))

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ----------------------------
# /pollhealth
# ----------------------------

@bot.tree.command(name="pollhealth", description="Operator polling health")
async def pollhealth(interaction: discord.Interaction):

    if not await admin_check(interaction):
        return

    operators = await sync_to_async(
        lambda: list(Operator.objects.all().order_by("name"))
    )()

    cutoff = timezone.now() - timedelta(minutes=20)

    lines = []

    for op in operators:

        count = await sync_to_async(
            lambda: Vehicle.objects.filter(
                operator=op,
                last_seen_journey_at__gte=cutoff
            ).count()
        )()

        if count > 0:
            status = "🟢 OK"
        else:
            status = "🔴 No vehicles"

        lines.append(f"{op.code} | {status}")

    embed = discord.Embed(
        title="Operator Poll Health",
        colour=0x3498DB
    )

    embed.description = "\n".join(lines)

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ----------------------------
# /lastpoll
# ----------------------------

@bot.tree.command(name="lastpoll", description="Show last poll time")
async def lastpoll(interaction: discord.Interaction):

    if not await admin_check(interaction):
        return

    poll = await sync_to_async(PollState.get_solo)()

    if poll.last_poll_at:
        value = poll.last_poll_at.strftime("%d %b %Y %H:%M")
    else:
        value = "Never"

    await interaction.response.send_message(
        f"Last poll ran at: **{value}**",
        ephemeral=True
    )

# ----------------------------
# /vehiclecount
# ----------------------------

@bot.tree.command(name="vehiclecount", description="Show tracked vehicle count")
async def vehiclecount(interaction: discord.Interaction):

    if not await admin_check(interaction):
        return

    total = await sync_to_async(lambda: Vehicle.objects.count())()

    tracking = await sync_to_async(
        lambda: Vehicle.objects.filter(last_seen_journey_at__isnull=False).count()
    )()

    await interaction.response.send_message(
        f"Vehicles in DB: **{total}**\nCurrently tracking: **{tracking}**",
        ephemeral=True
    )

# ----------------------------
# START BOT
# ----------------------------

bot.run(TOKEN)
