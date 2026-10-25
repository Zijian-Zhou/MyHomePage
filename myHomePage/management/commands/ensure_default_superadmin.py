import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = 'Create the default Docker superadmin when it does not exist.'

    def handle(self, *args, **options):
        username = os.getenv('DEFAULT_SUPERADMIN_USERNAME', 'superadmin').strip()
        email = os.getenv('DEFAULT_SUPERADMIN_EMAIL', 'admin@example.com').strip()
        credential_file = os.getenv('SUPERADMIN_CREDENTIAL_FILE', '').strip()

        if not username:
            raise CommandError('DEFAULT_SUPERADMIN_USERNAME cannot be empty.')

        user_model = get_user_model()
        existing = user_model.objects.filter(username=username).first()
        if existing:
            if not existing.is_superuser or not existing.is_staff:
                raise CommandError(
                    'User "{}" already exists but is not a superuser.'.format(username)
                )
            self._remove_credential_file(credential_file)
            self.stdout.write(
                self.style.WARNING(
                    'Default superadmin "{}" already exists; password was not changed.'.format(username)
                )
            )
            return

        timestamp = timezone.localtime().strftime('%Y%m%d%H%M')
        password = 'MyPageAdmin@{}'.format(timestamp)
        user_model.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )

        credentials = (
            'Default superadmin created\n'
            'Username: {}\n'
            'Password: {}\n'.format(username, password)
        )
        if credential_file:
            directory = os.path.dirname(credential_file)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(credential_file, 'w', encoding='utf-8') as output:
                output.write(credentials)
            try:
                os.chmod(credential_file, 0o600)
            except OSError:
                pass

        self.stdout.write(self.style.SUCCESS(credentials.rstrip()))

    @staticmethod
    def _remove_credential_file(path):
        if path and os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass
