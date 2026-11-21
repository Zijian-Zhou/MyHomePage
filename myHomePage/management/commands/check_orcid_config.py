from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from myHomePage.models import Profile
from myHomePage.services import ORCIDService


class Command(BaseCommand):
    help = 'Check or set the ORCID access token of a profile (stored on the Profile, next to its ORCID ID).'

    def add_arguments(self, parser):
        parser.add_argument('--profile', type=int, help='Profile id (default: the first active profile)')
        parser.add_argument('--token', type=str, help='ORCID access token to store on the profile')
        parser.add_argument('--check', action='store_true', help='Only check the current configuration')

    def handle(self, *args, **options):
        profile = self._profile(options.get('profile'))
        if options['token']:
            profile.orcid_access_token = options['token'].strip()
            profile.orcid_authorized_at = timezone.now()
            profile.save(update_fields=['orcid_access_token', 'orcid_authorized_at'])
            self.stdout.write(self.style.SUCCESS('Stored the ORCID access token on profile #{}'.format(profile.pk)))
        elif not options['check']:
            raise CommandError('Use --check or --token')
        self._check(profile)

    def _profile(self, profile_id):
        queryset = Profile.objects.all()
        profile = (queryset.filter(pk=profile_id).first() if profile_id
                   else queryset.filter(is_active=True).order_by('order', 'id').first() or queryset.first())
        if profile is None:
            raise CommandError('Profile not found')
        return profile

    def _check(self, profile):
        if not profile.orcid_access_token:
            self.stdout.write(self.style.ERROR('Profile #{} has no ORCID access token'.format(profile.pk)))
            return
        if not profile.orcid_id:
            self.stdout.write(self.style.WARNING('Profile #{} has no ORCID ID to test with'.format(profile.pk)))
            return
        self.stdout.write('Checking ORCID access for profile #{} ({})...'.format(profile.pk, profile.orcid_id))
        try:
            works = ORCIDService(profile.orcid_id, profile.orcid_access_token).get_works() or {}
            self.stdout.write(self.style.SUCCESS('ORCID access works: {} work groups'.format(len(works.get('group', [])))))
        except Exception as exc:
            self.stdout.write(self.style.ERROR('ORCID access failed: {}'.format(exc)))
