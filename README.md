# Bus Allocations V0.4

Django version of the V0.3 project, preserving the V0.3 feature set and layout while adding:

- fixed Bustimes livery pills
- trainer route handling for training codes
- registration form
- public fleet URLs by operator code
- staff-only editing
- webhook test button
- statistics page
- vehicle watch alerts
- full footer and production-ready config examples

## First run

Create a virtual environment, install requirements, then run:

```bash
python manage.py makemigrations allocations
python manage.py migrate
python manage.py bootstrap_app
python manage.py runserver
```

## Accounts

- Admin user is created from `.env`
- New users can register at `/register/`
- Only staff users can edit operators, rules, vehicles, polling, restores, and alert deletion
- Any user can log in and view fleets
- Public fleet pages are available at `/fleet/<OPERATOR_CODE>/` like `/fleet/FHAM/`

## Notes

- Sync an operator first to load fleet and routes from Bustimes
- The dashboard fleet table stays: Fleet, Reg, Type, Livery, Route, Rarity, Last seen
- Dead runs are ignored
- Trainer buses on the training code display the route and are treated as common
- Non-trainer buses on the training code display the route and trigger an uncommon alert
