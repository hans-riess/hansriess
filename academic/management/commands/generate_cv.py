import os
import subprocess
import logging
import boto3
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from academic.models import Profile, Education, Experience, Grant, Talk, Service, Course, Reference

# Configure logging
logger = logging.getLogger(__name__)

def escape_latex(text):
    """
    Escapes special LaTeX characters in a given string.
    """
    if not text:
        return ""
    # In order of replacement to avoid re-escaping
    replacements = {
        '\\': '\\textbackslash{}',
        '&': '\\&',
        '%': '\\%',
        '$': '\\$',
        '#': '\\#',
        '_': '\\_',
        '{': '\\{',
        '}': '\\}',
        '~': '\\textasciitilde{}',
        '^': '\\textasciicircum{}',
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text

def capitalize_semester(text):
    """
    Capitalizes semester terms like 'fall 2024' to 'Fall 2024'.
    """
    if not text:
        return ""
    import re
    # Capitalize semester terms
    text = re.sub(r'\b(fall|spring|summer|winter)\s+(\d{4})\b', lambda m: m.group(1).capitalize() + ' ' + m.group(2), text, flags=re.IGNORECASE)
    return text

class Command(BaseCommand):
    help = 'Generates the CV as a PDF from the database content and uploads it to S3.'

    def handle(self, *args, **options):
        self.stdout.write("Starting CV generation...")

        # --- 1. FETCH DATA FROM DATABASE ---
        try:
            profile = Profile.objects.first()
            educations = Education.objects.order_by('-graduation_year')
            experiences = Experience.objects.order_by('-start_date')
            grants = Grant.objects.order_by('-start_date')
            talks = Talk.objects.order_by('-date')
            services = Service.objects.order_by('-year')
            courses = Course.objects.order_by('-year', '-semester')
            
            # Publications grouped by type
            pub_types = ['journal_article', 'conference_proceedings', 'preprint', 'book', 'book_chapter', 'thesis', 'other']
            publications = {pt: Reference.objects.filter(reference_type=pt).order_by('-year') for pt in pub_types}

        except Exception as e:
            self.stderr.write(f"Error fetching data from database: {e}")
            return

        if not profile:
            self.stderr.write("No profile found in the database. Aborting.")
            return

        # --- 2. BUILD THE LATEX STRING ---
        tex_content = []
        tex_content.append("\\documentclass{article}")
        tex_content.append("\\usepackage{academic-cv}")
        tex_content.append(f"\\cvname{{{escape_latex(profile.name)}}}")
        tex_content.append(f"\\cvoccupation{{{escape_latex(profile.occupation or profile.title or '')}}}")
        if profile.email:
            tex_content.append(f"\\cvemail{{{escape_latex(profile.email)}}}")
        if profile.website:
            tex_content.append(f"\\cvwebsite{{{escape_latex(profile.website)}}}")
        tex_content.append("\\begin{document}")
        tex_content.append("\\makecvheader")
        if experiences.exists():
            tex_content.append("\\section{Academic Appointments}")
            tex_content.append("\\begin{cventries}")
            for item in experiences:
                def format_month_year(date):
                    if not date: return ""
                    return f"{date.strftime('%b')} {date.year}"
                start_str = format_month_year(item.start_date)
                end_str = "Present" if not item.end_date else format_month_year(item.end_date)
                dates = f"{start_str} -- {end_str}"
                description_parts = [escape_latex(p) for p in [item.location, item.description] if p]
                description = " \\\\ ".join(description_parts)
                tex_content.append(f"\\cventry{{{escape_latex(item.title)}}}{{{escape_latex(item.institution)}}}{{{dates}}}{{{description}}}")
            tex_content.append("\\end{cventries}")
        if grants.exists():
            tex_content.append("\\section{Grants}")
            tex_content.append("\\begin{cventries}")
            for grant in grants:
                role_display = grant.get_role_display()
                title = f"{escape_latex(role_display)}: {escape_latex(grant.title)}"
                description_parts = []
                if grant.amount: description_parts.append(f"\\${grant.amount:,.0f}")
                if grant.grant_number: description_parts.append(escape_latex(grant.grant_number))
                description = " • ".join(description_parts)
                tex_content.append(f"\\cventry{{{title}}}{{{escape_latex(grant.funding_agency)}}}{{{grant.get_date_range()}}}{{{description}}}")
            tex_content.append("\\end{cventries}")
        if educations.exists():
            tex_content.append("\\section{Education}")
            tex_content.append("\\begin{cventries}")
            for item in educations:
                degree = item.get_degree_type_display()
                field = item.field_of_study
                description_parts = [escape_latex(field)]
                second_line_parts = []
                if item.thesis_title: second_line_parts.append(f"Thesis: {escape_latex(item.thesis_title)}")
                if item.advisor: second_line_parts.append(f"Advisor: {escape_latex(item.advisor)}")
                if second_line_parts: description_parts.append(' • '.join(second_line_parts))
                if item.honors: description_parts.append(escape_latex(item.honors))
                description = " \\\\ ".join(description_parts)
                tex_content.append(f"\\cventry{{{escape_latex(degree)}}}{{{escape_latex(item.institution)}}}{{{item.graduation_year}}}{{{description}}}")
            tex_content.append("\\end{cventries}")
        if courses.exists():
            tex_content.append("\\section{Teaching}")
            tex_content.append("\\begin{cventries}")
            for course in courses:
                title = f"{escape_latex(course.course_code)}: {escape_latex(course.title)}" if course.course_code else escape_latex(course.title)
                dates = capitalize_semester(f"{course.semester} {course.year}")
                tex_content.append(f"\\cventry{{{title}}}{{{escape_latex(course.institution)}}}{{{dates}}}{{{escape_latex(course.get_role_display())}}}")
            tex_content.append("\\end{cventries}")
        tex_content.append("\\section{Publications}")
        for pub_type, pub_list in publications.items():
            if pub_list.exists():
                tex_content.append(f"\\subsection*{{{escape_latex(pub_list.first().get_reference_type_display())}}}")
                tex_content.append("\\begin{publications}")
                for pub in pub_list:
                    authors = escape_latex(pub.authors)
                    title = escape_latex(pub.title)
                    details_parts = [escape_latex(p) for p in [pub.journal, f"Vol. {pub.volume}" if pub.volume else None, f"Issue {pub.issue}" if pub.issue else None, f"pp. {pub.pages}" if pub.pages else None, str(pub.year) if pub.year else None] if p]
                    details = ", ".join(details_parts)
                    links = []
                    if pub.pdf_file: links.append(f"\\href{{{pub.pdf_file.url}}}{{[PDF]}}")
                    if pub.doi: links.append(f"\\href{{https://doi.org/{pub.doi}}}{{[DOI]}}")
                    if pub.url: links.append(f"\\href{{{pub.url}}}{{[URL]}}")
                    link_str = " ".join(links)
                    indicators = []
                    if pub.alphabetical_order: indicators.append("(Authors listed alphabetically)")
                    if pub.shared_first_author: indicators.append("(Shared first authorship)")
                    indicator_str = " ".join(indicators)
                    tex_content.append(f"\\publication{{{authors}}}{{{title}}}{{{details}}}{{{link_str}}}{{{indicator_str}}}")
                tex_content.append("\\end{publications}")
        if talks.exists():
            tex_content.append("\\section{Selected Invited Talks}")
            tex_content.append("\\begin{publications}")
            for talk in talks:
                tex_content.append(f"\\cvtalk{{{escape_latex(talk.title)}}}{{{escape_latex(talk.venue)}}}{{{escape_latex(talk.location)}}}{{{talk.date.strftime('%B %Y')}}}")
            tex_content.append("\\end{publications}")
        if services.exists():
            tex_content.append("\\section{Selected Professional Service}")
            tex_content.append("\\begin{cventries}")
            def format_month_year(date):
                if not date: return ""
                return f"{date.strftime('%b')} {date.year}"
            for service in services:
                start_str = format_month_year(service.start_date)
                end_str = format_month_year(service.end_date)
                dates = f"{start_str} -- {end_str}" if end_str else start_str
                tex_content.append(f"\\cventry{{{escape_latex(service.get_role_display())}}}{{{escape_latex(service.organization)}}}{{{dates}}}{{{escape_latex(service.title)}}}")
            tex_content.append("\\end{cventries}")
        tex_content.append("\\end{document}")
        final_tex_string = "\n".join(tex_content)

        # --- 3. WRITE .TEX FILE AND COMPILE ---
        tex_dir = os.path.join(settings.BASE_DIR, 'academic', 'tex')
        output_dir = os.path.join(settings.BASE_DIR, 'static', 'files')
        os.makedirs(output_dir, exist_ok=True)
        
        shutil.copy2(os.path.join(tex_dir, 'academic-cv.sty'), os.path.join(output_dir, 'academic-cv.sty'))
        
        tex_file_path = os.path.join(output_dir, 'cv.tex')
        pdf_file_path = os.path.join(output_dir, 'cv.pdf')
        with open(tex_file_path, 'w', encoding='utf-8') as f:
            f.write(final_tex_string)
        
        self.stdout.write(f".tex file written to {tex_file_path}")

        for i in range(2):
            self.stdout.write(f"Running pdflatex compilation (Pass {i+1}/2)...")
            process = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', f'-output-directory={output_dir}', tex_file_path],
                capture_output=True, text=True, encoding='utf-8'
            )
            if process.returncode != 0:
                self.stderr.write(self.style.ERROR('PDFLaTeX compilation failed!'))
                log_file = os.path.join(output_dir, 'cv.log')
                try:
                    with open(log_file, 'r') as log:
                        self.stderr.write(log.read())
                except FileNotFoundError:
                    self.stderr.write("Could not find log file. Raw output:")
                    self.stderr.write(process.stdout)
                    self.stderr.write(process.stderr)
                return
        
        self.stdout.write(self.style.SUCCESS(f"Successfully generated cv.pdf in {output_dir}"))

        # --- 4. UPLOAD TO S3 ---
        bucket_name = os.environ.get('AWS_STORAGE_BUCKET_NAME')
        if bucket_name:
            self.stdout.write("AWS credentials found. Attempting to upload to S3...")
            try:
                s3 = boto3.client(
                    's3',
                    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
                )
                object_name = 'cv.pdf'
                s3.upload_file(pdf_file_path, bucket_name, object_name, ExtraArgs={'ContentType': 'application/pdf'})
                self.stdout.write(self.style.SUCCESS(f'Successfully uploaded {object_name} to S3 bucket {bucket_name}'))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Failed to upload to S3: {e}'))
        else:
            self.stdout.write(self.style.WARNING('AWS credentials not found. Skipping S3 upload.'))

        # --- 5. CLEAN UP AUXILIARY FILES ---
        for ext in ['aux', 'log', 'out', 'fls', 'fdb_latexmk', 'synctex.gz', 'sty', 'tex']:
            try:
                os.remove(os.path.join(output_dir, f'cv.{ext}'))
            except FileNotFoundError:
                pass
        self.stdout.write("Cleaned up auxiliary files.")
