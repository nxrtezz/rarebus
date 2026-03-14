from django.core.management.base import BaseCommand
from allocations.services import poll_all_operators

class Command(BaseCommand):
    help = "Poll all operators now"

    def handle(self, *args, **kwargs):
        poll_all_operators()
        self.stdout.write(self.style.SUCCESS("Poll complete"))
