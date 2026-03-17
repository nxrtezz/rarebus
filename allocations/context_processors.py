from django.conf import settings
import subprocess


def get_git_version():
    try:
        return subprocess.check_output(
            ["git", "describe", "--tags", "--always"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return getattr(settings, "APP_VERSION", "unknown")


def app_version(request):
    return {
        "APP_VERSION": get_git_version()
    }