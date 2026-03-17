from django.core.management.base import BaseCommand
from allocations.services import poll_all_operators, poll_operator
from allocations.models import Operator


class Command(BaseCommand):
    help = "Poll Bustimes vehicle journeys"

    def add_arguments(self, parser):
        parser.add_argument(
            "operator",
            nargs="?",
            help="Operator code to poll (optional)"
        )

    def handle(self, *args, **options):

        operator_code = options.get("operator")

        if operator_code:

            try:
                operator = Operator.objects.get(code=operator_code)
            except Operator.DoesNotExist:
                self.stdout.write(self.style.ERROR("Operator not found"))
                return

            self.stdout.write(f"Polling {operator.code} | {operator.name}")

            poll_operator(operator)

        else:

            poll_all_operators()

        self.stdout.write(self.style.SUCCESS("Poll complete"))