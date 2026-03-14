from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import os

class Command(BaseCommand):
    help = "Create the default admin user from environment variables"

    def handle(self, *args, **kwargs):
        username = os.getenv("ADMIN_USERNAME", "admin")
        password = os.getenv("ADMIN_PASSWORD", "admin123")
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, password=password, email="")
            self.stdout.write(self.style.SUCCESS(f"Created admin user {username}"))
        else:
            self.stdout.write(self.style.WARNING(f"Admin user {username} already exists"))
