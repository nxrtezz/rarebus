# RareBus

![Python](https://img.shields.io/badge/python-3.10+-blue)
![Django](https://img.shields.io/badge/django-5.x-green)
![Status](https://img.shields.io/badge/status-public_beta-orange)
![License](https://img.shields.io/badge/license-community--maintained-lightgrey)

**RareBus** is a community-maintained platform that tracks real-time bus allocations and alerts enthusiasts when rare or unusual vehicles appear on routes.

The system monitors live vehicle tracking data and automatically detects **rare, uncommon, and special allocations**, displaying them in a live dashboard and optionally sending alerts to Discord.

🌐 **Live site**  
https://eeveeit.uk

💻 **GitHub repository**  
https://github.com/nxrtezz/rarebus

💬 **Community Discord**  
https://discord.gg/NFZ5a6dbea

---

# Features

## Real-time fleet tracking

RareBus continuously monitors vehicle journey data and displays:

- fleet number
- vehicle type
- registration
- current route
- destination
- rarity level
- last seen tracking time

Fleet lists are automatically sorted by fleet number for clarity.

---

## Allocation rarity detection

Routes can be configured to flag allocations as:

| Level | Meaning |
|------|------|
| Common | Expected allocation |
| Uncommon | Slightly unusual allocation |
| Rare | Highly unusual allocation |
| Rail Replacement | Vehicle operating rail replacement services |

RareBus automatically applies these levels based on configured rules.

---

## Alert system

Alerts are generated automatically when:

- a **rare allocation** appears
- an **uncommon allocation** appears
- a vehicle returns after **long inactivity**
- a vehicle tracks on **rail replacement services**
- watched vehicles begin tracking

Alerts are visible in the dashboard and can be sent to Discord.

---

## Public fleet pages

Each operator has a public fleet page.

```
/fleet/{operator_code}/
```

Example:

```
https://eeveeit.uk/fleet/FHAM/
```

Public pages display:

- fleet list
- current allocations
- recent alerts

---

# Discord Bot

RareBus includes a Discord bot that allows servers to query fleet data directly.

## Commands

| Command | Description |
|------|------|
| `/fleet {operator} {fleet}` | Show information about a vehicle |
| `/route {operator} {route}` | Vehicles seen on a route in the last 20 minutes |
| `/last-rare` | Latest rare allocation |
| `/last-uncommon` | Latest uncommon allocation |
| `/follow {operator}` | Send alerts for an operator to this channel |
| `/unfollow {operator}` | Stop alerts for an operator |

This allows Discord servers to receive live allocation updates automatically.

---

# Screenshots

### Dashboard
*(screenshot placeholder)*

### Fleet view
*(screenshot placeholder)*

### Alerts
*(screenshot placeholder)*

---

# Installation

RareBus is built with **Python and Django**.

## Requirements

- Python 3.10+
- pip
- SQLite (default database)

---

## Setup

Clone the repository:

```bash
git clone https://github.com/nxrtezz/rarebus.git
cd rarebus
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it.

Linux:

```bash
source venv/bin/activate
```

Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run migrations:

```bash
python manage.py migrate
```

Start the server:

```bash
python manage.py runserver
```

---

# Configuration

Create a `.env` file and configure required values.

Example:

```
SECRET_KEY=
DISCORD_BOT_TOKEN=
NEW_USER_WEBHOOK=
```

---

# Project Structure

```
rarebus
│
├── allocations/       Django app for fleet tracking logic
├── config/            Django project configuration
├── discordbot/        Discord bot
├── templates/         HTML templates
├── static/            CSS and assets
└── manage.py
```

---

# Roadmap

## v0.5

- Discord bot integration
- rail replacement detection
- long absence alerts
- improved polling system
- operator follow system
- operator settings page

## Planned features

- user webhooks
- expanded statistics
- improved Discord integrations
- additional route monitoring tools

---

# Contributing

RareBus is **community maintained**.

Bug reports, feature ideas, and improvements are welcome through GitHub issues.

---

# License

This project is provided for enthusiast and community use.

