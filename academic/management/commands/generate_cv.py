# academic/management/commands/generate_cv.py

import os
import subprocess
import logging
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
    return text.replace('&', '\\&').replace('%', '\\%').replace('$', '\\$') \
               .replace('#', '\\#').replace('_', '\\_').replace('{', '\\{') \
               .replace('}', '\\}').replace('~', '\\textasciitilde{}') \
               .replace('^', '\\textasciicircum{}').replace('\\', '\\textbackslash{}')

class Command(BaseCommand):
    help = 'Generates the CV as a PDF from the database content.'

    def handle(self, *args, **options):
        self.stdout.write("Starting CV generation...")

        # --- 1. FETCH DATA FROM DATABASE ---
        try:
            profile = Profile.objects.first()
            educations = Education.objects.order_by('-start_date')
            experiences = Experience.objects.order_by('-start_date')
            grants = Grant.objects.order_by('-start_date')
            talks = Talk.objects.order_by('-date')
            services = Service.objects.order_by('-start_date')
            courses = Course.objects.order_by('-year', '-semester')
            
            # Publications grouped by type
            pub_types = ['journal', 'conference', 'preprint', 'book', 'book_chapter', 'thesis', 'report']
            publications = {pt: Reference.objects.filter(publication_type=pt).order_by('-year') for pt in pub_types}

        except Exception as e:
            self.stderr.write(f"Error fetching data from database: {e}")
            return

        if not profile:
            self.stderr.write("No profile found in the database. Aborting.")
            return

        # --- 2. BUILD THE LATEX STRING ---
        tex_content = []

        # Preamble
        tex_content.append("\\documentclass{article}")
        tex_content.append("\\usepackage{academic-cv}")

        # Header Info
        tex_content.append(f"\\cvname{{{escape_latex(profile.name)}}}")
        tex_content.append(f"\\cvoccupation{{{escape_latex(profile.long_title)}}}")
        if profile.email:
            tex_content.append(f"\\cvemail{{{escape_latex(profile.email)}}}")
        if profile.website:
            tex_content.append(f"\\cvwebsite{{{escape_latex(profile.website)}}}")
        if profile.linkedin:
            tex_content.append(f"\\cvlinkedin{{{escape_latex(profile.linkedin)}}}")
        if profile.github:
            tex_content.append(f"\\cvgithub{{{escape_latex(profile.github)}}}")
        if profile.orcid:
            tex_content.append(f"\\cvorcid{{{escape_latex(profile.orcid)}}}")
        
        address_parts = [profile.building, profile.street, profile.city, profile.state, profile.zip_code, profile.country]
        full_address = ", ".join(filter(None, address_parts))
        if full_address:
             tex_content.append(f"\\cvaddress{{{escape_latex(full_address)}}}")

        tex_content.append("\\begin{document}")
        tex_content.append("\\makecvheader")

        # Education
        if educations.exists():
            tex_content.append("\\section{Education}")
            tex_content.append("\\begin{cventries}")
            for item in educations:
                dates = f"{item.start_date.year} -- {item.end_date.year if item.end_date else 'Present'}"
                tex_content.append(f"\\cventry{{{escape_latex(item.degree)}}}{{{escape_latex(item.institution)}}}{{{dates}}}{{{escape_latex(item.description)}}}")
            tex_content.append("\\end{cventries}")
        
        # Experience
        if experiences.exists():
            tex_content.append("\\section{Experience}")
            tex_content.append("\\begin{cventries}")
            for item in experiences:
                dates = f"{item.start_date.year} -- {item.end_date.year if item.end_date else 'Present'}"
                tex_content.append(f"\\cventry{{{escape_latex(item.title)}}}{{{escape_latex(item.institution)}}}{{{dates}}}{{{escape_latex(item.description)}}}")
            tex_content.append("\\end{cventries}")
            
        # Publications
        tex_content.append("\\section{Publications}")
        for pub_type, pub_list in publications.items():
            if pub_list.exists():
                tex_content.append(f"\\subsection*{{{escape_latex(pub_list.first().get_publication_type_display())}s}}")
                tex_content.append("\\begin{publications}")
                for pub in pub_list:
                    # Format authors
                    authors = []
                    for author_through in pub.referenceauthor_set.order_by('order'):
                        author_name = escape_latex(f"{author_through.collaborator.first_name} {author_through.collaborator.last_name}")
                        if author_through.collaborator.is_me:
                            author_name = f"\\textbf{{{author_name}}}"
                        authors.append(author_name)
                    author_str = ", ".join(authors)

                    title = escape_latex(pub.title)
                    
                    details_parts = []
                    if pub.journal: details_parts.append(escape_latex(pub.journal))
                    if pub.book_title: details_parts.append(f"In \\textit{{{escape_latex(pub.book_title)}}}")
                    if pub.year: details_parts.append(str(pub.year))
                    details = ", ".join(filter(None, details_parts))

                    links = []
                    if pub.pdf_file:
                        links.append(f"\\href{{{pub.pdf_file.url}}}{{[PDF]}}")
                    if pub.doi:
                        links.append(f"\\href{{https://doi.org/{pub.doi}}}{{[DOI]}}")
                    link_str = " ".join(links)

                    tex_content.append(f"\\publication{{{author_str}}}{{{title}}}{{{details}}}{{{link_str}}}")
                tex_content.append("\\end{publications}")

        # Talks
        if talks.exists():
            tex_content.append("\\section{Presentations}")
            tex_content.append("\\begin{publications}") # Reusing publication style for talks
            for talk in talks:
                tex_content.append(f"\\cvtalk{{{escape_latex(talk.title)}}}{{{escape_latex(talk.event)}}}{{{escape_latex(talk.location)}}}{{{talk.date.strftime('%B %Y')}}}")
            tex_content.append("\\end{publications}")

        # Grants
        if grants.exists():
            tex_content.append("\\section{Funding}")
            tex_content.append("\\begin{cventries}")
            for grant in grants:
                dates = f"{grant.start_date.year} -- {grant.end_date.year if grant.end_date else 'Present'}"
                title = f"{escape_latex(grant.title)} (\${grant.amount:,})"
                tex_content.append(f"\\cventry{{{title}}}{{{escape_latex(grant.agency)}}}{{{dates}}}{{Role: {escape_latex(grant.role)}}}")
            tex_content.append("\\end{cventries}")
            
        # Teaching
        if courses.exists():
            tex_content.append("\\section{Teaching Experience}")
            tex_content.append("\\begin{cventries}")
            for course in courses:
                title = f"{escape_latex(course.code)}: {escape_latex(course.title)}"
                dates = f"{course.semester} {course.year}"
                tex_content.append(f"\\cventry{{{title}}}{{{escape_latex(course.institution)}}}{{{dates}}}{{}}")
            tex_content.append("\\end{cventries}")

        # Service
        if services.exists():
            tex_content.append("\\section{Professional Service}")
            tex_content.append("\\begin{cventries}")
            for service in services:
                dates = f"{service.start_date.year} -- {service.end_date.year if service.end_date else 'Present'}"
                tex_content.append(f"\\cventry{{{escape_latex(service.role)}}}{{{escape_latex(service.organization)}}}{{{dates}}}{{}}")
            tex_content.append("\\end{cventries}")


        tex_content.append("\\end{document}")

        final_tex_string = "\n".join(tex_content)

        # --- 3. WRITE .TEX FILE AND COMPILE ---
        tex_dir = os.path.join(settings.BASE_DIR, 'academic', 'tex')
        output_dir = os.path.join(settings.BASE_DIR, 'static', 'files')
        os.makedirs(tex_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        tex_file_path = os.path.join(tex_dir, 'cv.tex')
        with open(tex_file_path, 'w', encoding='utf-8') as f:
            f.write(final_tex_string)
        
        self.stdout.write(f".tex file written to {tex_file_path}")

        # Compile with pdflatex
        for i in range(2): # Run twice to ensure cross-references are correct
            self.stdout.write(f"Running pdflatex compilation (Pass {i+1}/2)...")
            process = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', f'-output-directory={output_dir}', tex_file_path],
                capture_output=True, text=True
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

        # Clean up auxiliary files
        for ext in ['aux', 'log', 'out']:
            try:
                os.remove(os.path.join(output_dir, f'cv.{ext}'))
            except FileNotFoundError:
                pass

        self.stdout.write(self.style.SUCCESS(f"Successfully generated cv.pdf in {output_dir}"))
