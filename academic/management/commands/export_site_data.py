import json

from django.core.management.base import BaseCommand, CommandError

from academic.models import Profile
from academic.site_data import build_site_data


class Command(BaseCommand):
    help = ('Writes the structured CV data served at /sitedata/data.json to a file, '
            'for use as context in applications and AI tools.')

    def add_arguments(self, parser):
        parser.add_argument(
            '-o', '--output', default='data.json',
            help="File to write, or '-' for standard output. Defaults to data.json.",
        )

    def handle(self, *args, **options):
        profile = Profile.objects.first()
        if not profile:
            raise CommandError("No profile found in the database.")

        text = json.dumps(build_site_data(profile), indent=2, ensure_ascii=False) + "\n"
        if options['output'] == '-':
            self.stdout.write(text, ending='')
            return
        with open(options['output'], 'w', encoding='utf-8') as out:
            out.write(text)
        self.stdout.write(self.style.SUCCESS(f"Wrote {options['output']}"))
