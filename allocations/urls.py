from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),

    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("dashboard/operators/", views.operators_view, name="operators"),
    path("dashboard/operators/<int:pk>/delete/", views.delete_operator_view, name="operator-delete"),
    path("dashboard/operators/<int:pk>/test-webhook/", views.test_webhook_view, name="operator-test-webhook"),

    path("dashboard/operators/request/", views.operator_request_view, name="operator-request"),

    path("dashboard/sync/", views.sync_view, name="sync"),
    path("dashboard/poll/", views.poll_view, name="poll"),

    path("dashboard/fleet/withdrawn/", views.withdrawn_view, name="withdrawn"),
    path("dashboard/fleet/<int:pk>/restore/", views.restore_vehicle_view, name="vehicle-restore"),
    path("dashboard/fleet/<int:pk>/state/", views.vehicle_state_view, name="vehicle-state"),
    path("dashboard/fleet/<int:pk>/override/", views.vehicle_override_view, name="vehicle-override"),

    path("dashboard/fleet/<int:pk>/watch/create/", views.watch_create_view, name="watch-create"),
    path("dashboard/fleet/<int:pk>/watch/<int:watch_id>/delete/", views.watch_delete_view, name="watch-delete"),

    path("dashboard/fleet/<int:pk>/", views.vehicle_view, name="vehicle"),
    path("fleet/<str:code>/", views.public_fleet_view, name="public-fleet"),

    path("dashboard/rules/types/", views.type_rules_view, name="type-rules"),
    path("dashboard/rules/types/save/", views.type_rules_save_view, name="type-rules-save"),
    path("dashboard/rules/vehicle/save/", views.vehicle_rule_save_view, name="vehicle-rule-save"),

    path("alerts/", views.alerts_view, name="alerts"),
    path("alerts/delete/<int:alert_id>/", views.delete_alert, name="delete-alert"),

    path("stats/", views.stats_view, name="stats"),
    path("alerts/clear/", views.clear_alerts, name="clear-alerts"),

    path("admin/approve-user/<int:user_id>/", views.approve_user),
    path("admin/reject-user/<int:user_id>/", views.reject_user),

    path("dashboard/operators/settings/", views.operator_settings_view, name="operator-settings"),

    path("dashboard/request-supervisor/", views.request_supervisor, name="request_supervisor"), 

    path("discord/follow/", views.discord_follow),
    path("discord/unfollow/", views.discord_unfollow),
]
