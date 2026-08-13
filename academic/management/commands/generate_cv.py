import logging
import os
import shutil
import subprocess

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from academic.cv_builder import build_document
from academic.models import Profile

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = ('Generates the CV as a PDF in the official Georgia Tech format from '
            'database content and handles storage for development and production.')

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-tex', action='store_true',
            help='Leave the generated cv.tex and cv.log in temp_cv/ for inspection.',
        )
        parser.add_argument(
            '--no-save', action='store_true',
            help='Compile the PDF but do not attach it to the profile.',
        )

    def handle(self, *args, **options):
        self.stdout.write("Starting CV generation...")

        profile = Profile.objects.first()
        if not profile:
            self.stderr.write("No profile found in the database. Aborting.")
            return

        try:
            tex_source = build_document(profile)
        except Exception as e:
            logger.exception("Failed to build the CV LaTeX source")
            self.stderr.write(self.style.ERROR(f"Error building the CV source: {e}"))
            return

        temp_dir = os.path.join(settings.BASE_DIR, 'temp_cv')
        os.makedirs(temp_dir, exist_ok=True)

        style_src = os.path.join(settings.BASE_DIR, 'academic', 'tex', 'academic-cv.sty')
        if os.path.exists(style_src):
            shutil.copy2(style_src, os.path.join(temp_dir, 'academic-cv.sty'))
        else:
            self.stderr.write(self.style.ERROR(f"Style file not found at {style_src}. Aborting."))
            shutil.rmtree(temp_dir, ignore_errors=True)
            return

        tex_path = os.path.join(temp_dir, 'cv.tex')
        pdf_path = os.path.join(temp_dir, 'cv.pdf')
        try:
            with open(tex_path, 'w', encoding='utf-8') as f:
                f.write(tex_source)
        except OSError as e:
            self.stderr.write(self.style.ERROR(f"Error writing .tex file: {e}"))
            shutil.rmtree(temp_dir, ignore_errors=True)
            return

        if not self._compile(tex_path, temp_dir):
            self._keep_or_clean(temp_dir, options['keep_tex'])
            return

        if not os.path.exists(pdf_path):
            self.stderr.write(self.style.ERROR(f"PDF was not generated at {pdf_path}. Check cv.log."))
            self._keep_or_clean(temp_dir, options['keep_tex'])
            return

        self.stdout.write(self.style.SUCCESS(f"Successfully generated cv.pdf in {temp_dir}"))

        if options['no_save']:
            self.stdout.write("--no-save given; leaving the profile untouched.")
            self._keep_or_clean(temp_dir, options['keep_tex'])
            return

        try:
            with open(pdf_path, 'rb') as pdf:
                # Delete the old file first so the stored name stays cv.pdf.
                if profile.cv:
                    profile.cv.delete(save=False)
                profile.cv.save('cv.pdf', File(pdf), save=True)
        except Exception as e:
            logger.exception("Failed to save the generated CV")
            self.stderr.write(self.style.ERROR(f"Failed to save or upload CV: {e}"))
            self._keep_or_clean(temp_dir, options['keep_tex'])
            return

        if settings.PRODUCTION:
            self.stdout.write(self.style.SUCCESS(f"Uploaded {profile.cv.name} to the profile."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Saved new CV to {profile.cv.path}"))

        self._keep_or_clean(temp_dir, options['keep_tex'])

    def _compile(self, tex_path, temp_dir):
        """Run pdflatex twice. The first pass populates cross-references, so it is
        allowed to fail; the second pass is authoritative."""
        for attempt in (1, 2):
            self.stdout.write(f"Running pdflatex (pass {attempt}/2)...")
            try:
                process = subprocess.run(
                    ['pdflatex', '-interaction=nonstopmode',
                     f'-output-directory={temp_dir}', tex_path],
                    capture_output=True, text=True, encoding='utf-8', errors='replace',
                )
            except FileNotFoundError:
                self.stderr.write(self.style.ERROR(
                    'pdflatex not found. Make sure LaTeX is installed and on PATH.'))
                return False

            if process.returncode != 0 and attempt == 2:
                self.stderr.write(self.style.ERROR(
                    f'pdflatex failed on the final pass (return code {process.returncode}).'))
                self._report_log(temp_dir, process)
                return False
        return True

    def _report_log(self, temp_dir, process):
        log_path = os.path.join(temp_dir, 'cv.log')
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as log:
                content = log.read()
        except OSError:
            self.stderr.write("Could not read cv.log. Raw pdflatex output:")
            self.stderr.write(process.stdout or "None")
            return

        errors = [line for line in content.splitlines()
                  if line.startswith('!') or 'Error' in line]
        if errors:
            self.stderr.write("Relevant log lines:\n" + "\n".join(errors[:20]))
        else:
            self.stderr.write(f"See {log_path} for details.")

    def _keep_or_clean(self, temp_dir, keep):
        if keep:
            self.stdout.write(f"Leaving build files in {temp_dir}.")
            return
        try:
            shutil.rmtree(temp_dir)
            self.stdout.write("Cleaned up temporary directory.")
        except OSError as e:
            self.stderr.write(f"Error removing temporary directory {temp_dir}: {e}")
