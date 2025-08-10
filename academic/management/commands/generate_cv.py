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
    help = 'Generates the CV as a PDF from the database content.'

    def handle(self, *args, **options):
        self.stdout.write("Starting CV generation...")

        # --- 1. FETCH DATA FROM DATABASE ---
        try:
            profile = Profile.objects.first()
            educations = Education.objects.order_by('-graduation_year')
            experiences = Experience.objects.order_by('-start_date')
            grants = Grant.objects.order_by('-start_year')
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

        # Preamble
        tex_content.append("\\documentclass{article}")
        tex_content.append("\\usepackage{academic-cv}")

        # Header Info
        tex_content.append(f"\\cvname{{{escape_latex(profile.name)}}}")
        tex_content.append(f"\\cvoccupation{{{escape_latex(profile.occupation or profile.title or '')}}}")
        if profile.email:
            tex_content.append(f"\\cvemail{{{escape_latex(profile.email)}}}")
        if profile.website:
            tex_content.append(f"\\cvwebsite{{{escape_latex(profile.website)}}}")
        
        # Format address with street, city, state, zip, and country on one line
        address_parts = []
        if profile.street:
            address_parts.append(profile.street)
            
        city_state_zip = []
        if profile.city:
            city_state_zip.append(profile.city)
        if profile.state:
            city_state_zip.append(profile.state)
        if profile.zip_code:
            city_state_zip.append(profile.zip_code)
        if city_state_zip:
            address_parts.append(", ".join(city_state_zip))
            
        if profile.country:
            address_parts.append(profile.country)
            
        if address_parts:
            # Join all parts with commas for one line
            full_address = " ".join([escape_latex(part) for part in address_parts])
            tex_content.append(f"\\cvaddress{{{full_address}}}")

        tex_content.append("\\begin{document}")
        tex_content.append("\\makecvheader")

        # Academic Appointments
        if experiences.exists():
            tex_content.append("\\section{Academic Appointments}")
            tex_content.append("\\begin{cventries}")
            for item in experiences:
                if item.end_date and item.start_date.year == item.end_date.year:
                    dates = str(item.start_date.year)
                else:
                    dates = f"{item.start_date.year} -- {item.end_date.year if item.end_date else 'Present'}"
                
                # Build description with location and original description
                description_parts = []
                if item.location:
                    description_parts.append(escape_latex(item.location))
                if item.description:
                    description_parts.append(escape_latex(item.description))
                
                description = " \\\\ ".join(description_parts) if description_parts else ""
                
                tex_content.append(f"\\cventry{{{escape_latex(item.title)}}}{{{escape_latex(item.institution)}}}{{{dates}}}{{{description}}}")
            tex_content.append("\\end{cventries}")

        # Education
        if educations.exists():
            tex_content.append("\\section{Education}")
            tex_content.append("\\begin{cventries}")
            for item in educations:
                degree = item.get_degree_type_display()
                field = item.field_of_study
                
                # First line: field of study
                description = escape_latex(field)
                
                # Second line: thesis and advisor (if they exist)
                second_line_parts = []
                if item.thesis_title:
                    second_line_parts.append(f"Thesis: {escape_latex(item.thesis_title)}")
                if item.advisor:
                    second_line_parts.append(f"Advisor: {escape_latex(item.advisor)}")
                
                if second_line_parts:
                    description += f" \\\\ {' • '.join(second_line_parts)}"
                
                # Add honors if they exist
                if item.honors:
                    if second_line_parts:
                        description += f" \\\\ {escape_latex(item.honors)}"
                
                tex_content.append(f"\\cventry{{{escape_latex(degree)}}}{{{escape_latex(item.institution)}}}{{{item.graduation_year}}}{{{description}}}")
            tex_content.append("\\end{cventries}")
            
        # Publications
        tex_content.append("\\section{Publications}")
        for pub_type, pub_list in publications.items():
            if pub_list.exists():
                tex_content.append(f"\\subsection*{{{escape_latex(pub_list.first().get_reference_type_display())}}}")
                tex_content.append("\\begin{publications}")
                for pub in pub_list:
                    # Format authors
                    authors = escape_latex(pub.authors)
                    title = escape_latex(pub.title)
                    
                    details_parts = []
                    if pub.journal: details_parts.append(escape_latex(pub.journal))
                    if pub.volume: details_parts.append(f"Vol. {pub.volume}")
                    if pub.issue: details_parts.append(f"Issue {pub.issue}")
                    if pub.pages: details_parts.append(f"pp. {pub.pages}")
                    if pub.year: details_parts.append(str(pub.year))
                    details = ", ".join(filter(None, details_parts))

                    links = []
                    if pub.pdf_file:
                        links.append(f"\\href{{{pub.pdf_file.url}}}{{[PDF]}}")
                    if pub.doi:
                        links.append(f"\\href{{https://doi.org/{pub.doi}}}{{[DOI]}}")
                    if pub.url:
                        links.append(f"\\href{{{pub.url}}}{{[URL]}}")
                    link_str = " ".join(links)

                    # Add special indicators
                    indicators = []
                    if pub.alphabetical_order:
                        indicators.append("(Authors listed alphabetically)")
                    if pub.shared_first_author:
                        indicators.append("(Shared first authorship)")
                    indicator_str = " ".join(indicators)

                    tex_content.append(f"\\publication{{{authors}}}{{{title}}}{{{details}}}{{{link_str}}}{{{indicator_str}}}")
                tex_content.append("\\end{publications}")

        # Talks
        if talks.exists():
            tex_content.append("\\section{Talks}")
            tex_content.append("\\begin{publications}") # Reusing publication style for talks
            for talk in talks:
                tex_content.append(f"\\cvtalk{{{escape_latex(talk.title)}}}{{{escape_latex(talk.venue)}}}{{{escape_latex(talk.location)}}}{{{talk.date.strftime('%B %Y')}}}")
            tex_content.append("\\end{publications}")

        # Grants (renamed from Funding)
        if grants.exists():
            tex_content.append("\\section{Grants}")
            tex_content.append("\\begin{cventries}")
            for grant in grants:
                years = f"{grant.start_year}"
                if grant.end_year:
                    years += f" -- {grant.end_year}"
                
                # Include role prominently in the title
                role_display = grant.get_role_display()
                title = f"{escape_latex(role_display)}: {escape_latex(grant.title)}"
                
                # Create description with amount and grant number
                description_parts = []
                if grant.amount:
                    description_parts.append(f"\${grant.amount:,.0f}")
                if grant.grant_number:
                    description_parts.append(escape_latex(grant.grant_number))
                
                description = " • ".join(description_parts) if description_parts else ""
                
                tex_content.append(f"\\cventry{{{title}}}{{{escape_latex(grant.funding_agency)}}}{{{years}}}{{{description}}}")
            tex_content.append("\\end{cventries}")
            
        # Teaching
        if courses.exists():
            tex_content.append("\\section{Teaching Experience}")
            tex_content.append("\\begin{cventries}")
            for course in courses:
                title = f"{escape_latex(course.course_code)}: {escape_latex(course.title)}"
                dates = capitalize_semester(f"{course.semester} {course.year}")
                tex_content.append(f"\\cventry{{{title}}}{{{escape_latex(course.institution)}}}{{{dates}}}{{}}")
            tex_content.append("\\end{cventries}")

        # Service
        if services.exists():
            tex_content.append("\\section{Professional Service}")
            tex_content.append("\\begin{cventries}")
            for service in services:
                tex_content.append(f"\\cventry{{{escape_latex(service.get_role_display())}}}{{{escape_latex(service.organization)}}}{{{service.year}}}{{{escape_latex(service.title)}}}")
            tex_content.append("\\end{cventries}")


        tex_content.append("\\end{document}")

        final_tex_string = "\n".join(tex_content)

        # --- 3. WRITE .TEX FILE AND COMPILE ---
        tex_dir = os.path.join(settings.BASE_DIR, 'academic', 'tex')
        output_dir = os.path.join(settings.BASE_DIR, 'static', 'files')
        os.makedirs(output_dir, exist_ok=True)
        
        # Copy the style file to the output directory
        style_file_src = os.path.join(tex_dir, 'academic-cv.sty')
        style_file_dst = os.path.join(output_dir, 'academic-cv.sty')
        import shutil
        shutil.copy2(style_file_src, style_file_dst)
        
        tex_file_path = os.path.join(output_dir, 'cv.tex')
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
