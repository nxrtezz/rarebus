# 🚍 RareBus

![Python](https://img.shields.io/badge/python-3.10+-blue)
![Django](https://img.shields.io/badge/django-5.x-green)
![Status](https://img.shields.io/badge/status-public_beta-orange)
![Version](https://img.shields.io/badge/version-v0.6-blue)
![License](https://img.shields.io/badge/license-community--maintained-lightgrey)

**RareBus** is a community-driven platform for tracking real-time bus allocations and detecting rare or unusual vehicle usage.

It monitors live tracking data and automatically identifies **rare, uncommon, and special allocations**, displaying them on a web dashboard and sending alerts directly to Discord.

---

## 🌐 Links

- **Live site**  
  https://eeveeit.uk

- **GitHub repository**  
  https://github.com/nxrtezz/rarebus

- **Community Discord**  
  https://discord.gg/NFZ5a6dbea

---

# ✨ Features (v0.6)

## 🔔 Real-time fleet tracking

RareBus continuously tracks vehicles and displays:

- Fleet number  
- Vehicle type  
- Registration  
- Current route  
- Destination  
- Rarity level  
- Last seen tracking time  

Fleet lists are automatically sorted for clarity.

---

## 🎯 Allocation rarity detection

Routes can be configured with rarity rules:

| Level | Meaning |
|------|------|
| Common | Expected allocation |
| Uncommon | Slightly unusual allocation |
| Rare | Highly unusual allocation |
| Rail Replacement | Special rail replacement services |

RareBus applies these automatically using rule-based logic.

---

## 🚨 Smart alert system

Alerts are triggered when:

- Rare allocations appear  
- Uncommon allocations appear  
- Vehicles return after long inactivity  
- Vehicles operate rail replacement services  
- Watched vehicles begin tracking  

### 🧠 v0.6 Improvements

- Only alerts for **vehicles tracked today** (prevents stale alerts)  
- Reduced duplicate alerts  
- Improved timing and reliability  

---

## 💬 Discord integration

RareBus includes a full Discord alert system.

### 🔔 Follow operators

Users can subscribe to alerts:


/follow {operator}


Supports:

- 📢 Channel alerts  
- 💬 Direct message alerts  
- 👥 Multiple subscribers per operator  

---

### 🧾 Rich embeds

Alerts are delivered as structured embeds showing:

- Operator  
- Fleet  
- Route  
- Destination  
- Rarity level  

---

## 👥 Supervisor system

Operators can have assigned supervisors who can:

- Manage allocation rules  
- Adjust rarity classifications  
- Maintain data accuracy  

Permissions are limited to assigned operators.

---

## 🌍 Public fleet pages

Each operator has a public page:


/fleet/{operator_code}/


Example:


https://eeveeit.uk/fleet/FHAM/


Displays:

- Fleet list  
- Live allocations  
- Recent alerts  

---

# 🤖 Discord Bot

RareBus includes a Discord bot for querying live data.

## Commands

| Command | Description |
|------|------|
| `/fleet {operator} {fleet}` | Show vehicle details |
| `/route {operator} {route}` | Vehicles seen recently on a route |
| `/last-rare` | Latest rare allocation |
| `/last-uncommon` | Latest uncommon allocation |
| `/follow {operator}` | Subscribe to alerts |
| `/unfollow {operator}` | Unsubscribe from alerts |

---

# 📸 Screenshots

*(Add screenshots here later)*

---

# ⚙️ Installation

## Requirements

- Python 3.10+  
- pip  
- SQLite (default)  

---

## Setup

Clone the repository:

```bash
git clone https://github.com/nxrtezz/rarebus.git
cd rarebus

Create a virtual environment:

python -m venv venv

Activate it:

Linux:

source venv/bin/activate

Windows:

venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

Run migrations:

python manage.py migrate

Start server:

python manage.py runserver
🔐 Configuration

Create a .env file:

SECRET_KEY=
DISCORD_BOT_TOKEN=
NEW_USER_WEBHOOK=
📁 Project Structure
rarebus
│
├── allocations/       Core tracking + alert logic
├── config/            Django settings
├── discordbot/        Discord bot
├── templates/         HTML templates
├── static/            CSS / assets
└── manage.py
🗺️ Roadmap
v0.6 (Current)

Discord follow system (channels + DMs) ✅

Multi-subscriber alert system ✅

Rich Discord embeds ✅

Supervisor system ✅

Improved tracking logic ✅

v0.7 (Next)

Livery rules (alongside type rules)

/subscriptions command

Improved supervisor tools

Alert formatting improvements

Future Ideas

Historical tracking

Public API

Mobile-friendly UI

Expanded statistics

🤝 Contributing

RareBus is community maintained.

Contributions, bug reports, and ideas are welcome via GitHub issues.

📜 License

This project is provided for enthusiast and community use.
