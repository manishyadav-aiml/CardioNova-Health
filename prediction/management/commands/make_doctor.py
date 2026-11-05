from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from prediction.models import Profile


class Command(BaseCommand):
    help = "Gives an existing user the Doctor role:  python manage.py make_doctor <username>"

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--patient", action="store_true", help="set the role back to patient")

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist:
            raise CommandError(f"User '{options['username']}' does not exist.")
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.role = Profile.ROLE_PATIENT if options["patient"] else Profile.ROLE_DOCTOR
        profile.save()
        self.stdout.write(self.style.SUCCESS(f"{user.username} is now a {profile.role}."))
