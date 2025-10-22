import os
import subprocess
import logging
import boto3
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files import File
from academic.models import (Profile, Education, Experience, Grant, Talk, Service,
                             Course, Reference, Student, ReferencePerson)

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
    help = 'Generates the CV as a PDF from database content and handles storage for development and production.'

    def handle(self, *args, **options):
        self.stdout.write("Starting CV generation...")

        # --- 1. FETCH DATA FROM DATABASE ---
        try:
            profile = Profile.objects.first()
            if not profile:
                self.stderr.write("No profile found in the database. Aborting.")
                return

            educations = Education.objects.order_by('-graduation_year')
            experiences = Experience.objects.order_by('-start_date')
            grants = Grant.objects.order_by('-start_date')
            talks = Talk.objects.filter(is_invited=True).order_by('-date')
            services = Service.objects.order_by('-year')
            courses = Course.objects.order_by('-year', '-semester')
            pub_types = ['journal_article', 'conference_proceedings', 'preprint', 'book', 'book_chapter', 'thesis', 'other']
            publications = {pt: Reference.objects.filter(reference_type=pt).order_by('-year') for pt in pub_types}
            students = Student.objects.order_by('-start_date')
            professional_references = ReferencePerson.objects.order_by('name')

        except Exception as e:
            self.stderr.write(f"Error fetching data from database: {e}")
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

        # Academic Appointments
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
                description_parts = [escape_latex(p) for p in [item.department, item.location, item.description] if p]
                description = " \\\\ ".join(description_parts)
                tex_content.append(f"\\cventry{{{escape_latex(item.title)}}}{{{escape_latex(item.institution)}}}{{{dates}}}{{{description}}}")
            tex_content.append("\\end{cventries}")

        # Grants
        if grants.exists():
            tex_content.append("\\section{Grants}")
            tex_content.append("\\begin{cventries}")
            for grant in grants:
                role_display = grant.get_role_display_name().replace("_", " ").title()
                title = f"{escape_latex(role_display)}: {escape_latex(grant.title)}"
                description_parts = []
                if grant.amount: description_parts.append(f"{escape_latex(grant.get_formatted_amount())}")
                if grant.grant_number: description_parts.append(escape_latex(grant.grant_number))
                description = " • ".join(description_parts)
                tex_content.append(f"\\cventry{{{title}}}{{{escape_latex(grant.funding_agency)}}}{{{grant.get_date_range()}}}{{{description}}}")
            tex_content.append("\\end{cventries}")

        # Education
        if educations.exists():
            tex_content.append("\\section{Education}")
            tex_content.append("\\begin{cventries}")
            for item in educations:
                degree = escape_latex(item.degree_type_short or item.degree_type)
                field = item.field_of_study
                description_parts = [escape_latex(field)]
                second_line_parts = []
                if item.thesis_title: second_line_parts.append(f"Thesis: {escape_latex(item.thesis_title)}")
                if item.advisor: second_line_parts.append(f"Advisor: {escape_latex(item.advisor)}")
                if second_line_parts: description_parts.append(' • '.join(second_line_parts))
                if item.honors: description_parts.append(escape_latex(item.honors))
                description = " \\\\ ".join(description_parts)
                tex_content.append(f"\\cventry{{{degree}}}{{{escape_latex(item.institution)}}}{{{item.graduation_year}}}{{{description}}}")
            tex_content.append("\\end{cventries}")

        # Teaching
        if courses.exists():
            tex_content.append("\\section{Teaching}")
            tex_content.append("\\begin{cventries}")
            for course in courses:
                title = f"{escape_latex(course.course_code)}: {escape_latex(course.title)}" if course.course_code else escape_latex(course.title)
                dates = capitalize_semester(f"{course.semester} {course.year}")
                tex_content.append(f"\\cventry{{{title}}}{{{escape_latex(course.institution)}}}{{{dates}}}{{{escape_latex(course.get_role_display_name())}}}")
            tex_content.append("\\end{cventries}")

        # Publications
        has_publications = any(pub_list.exists() for pub_list in publications.values())
        if has_publications:
            tex_content.append("\\section{Publications}")
            for pub_type, pub_list in publications.items():
                if pub_list.exists():
                    type_display = dict(Reference.REFERENCE_TYPES).get(pub_type, pub_type.replace('_', ' ').title())
                    tex_content.append(f"\\subsection*{{{escape_latex(type_display)}}}")
                    tex_content.append("\\begin{publications}")
                    for pub in pub_list:
                        authors = escape_latex(pub.authors)
                        title = escape_latex(pub.title)
                        details_parts = []
                        if pub.journal: details_parts.append(escape_latex(pub.journal))
                        if pub.volume: details_parts.append(f"Vol. {escape_latex(pub.volume)}")
                        if pub.issue: details_parts.append(f"Issue {escape_latex(pub.issue)}")
                        if pub.pages: details_parts.append(f"pp. {escape_latex(pub.pages)}")
                        if pub.year: details_parts.append(str(pub.year))
                        details = ", ".join(filter(None, details_parts))
                        links = []
                        if pub.pdf_file: links.append(f"\\href{{{pub.pdf_file.url}}}{{[PDF]}}")
                        if pub.doi: links.append(f"\\href{{https://doi.org/{pub.doi}}}{{[DOI]}}")
                        if pub.url: links.append(f"\\href{{{pub.url}}}{{[URL]}}")
                        if pub.code: links.append(f"\\href{{{pub.code}}}{{[Code]}}")
                        link_str = " ".join(links)
                        indicators = []
                        if pub.alphabetical_order: indicators.append("(Authors listed alphabetically)")
                        if pub.shared_first_author: indicators.append("(Shared first authorship)")
                        indicator_str = " ".join(indicators)
                        tex_content.append(f"\\publication{{{authors}}}{{{title}}}{{{details}}}{{{link_str}}}{{{indicator_str}}}")
                    tex_content.append("\\end{publications}")

        # Invited Talks
        if talks.exists():
            tex_content.append("\\section{Selected Invited Talks}")
            tex_content.append("\\begin{publications}")
            for talk in talks:
                poster_link = f" \\href{{{talk.poster.url}}}{{[Poster]}}" if talk.poster else ""
                location_with_poster = f"{escape_latex(talk.location)}{poster_link}"
                tex_content.append(f"\\cvtalk{{{escape_latex(talk.title)}}}{{{escape_latex(talk.venue)}}}{{{location_with_poster}}}{{{talk.date.strftime('%B %Y')}}}")
            tex_content.append("\\end{publications}")

        # --- UPDATED Mentorship SECTION ---
        if students.exists():
            tex_content.append("\\section{Mentorship}")
            tex_content.append("\\begin{cventries}")
            for student in students:
                # Combine level, degree (if present), and institution
                level_degree_inst_parts = [escape_latex(student.get_level_display())]
                level_degree_inst_parts.append(escape_latex(student.institution))
                level_degree_inst = ", ".join(level_degree_inst_parts)

                dates = student.get_date_range()
                description_parts = []
                # Add mentorship role if it's not 'Informal Mentorship' (blank value)
                if student.mentorship_role:
                    description_parts.append(f"Role: {escape_latex(student.get_mentorship_role_display())}")
                if student.project_title: description_parts.append(f"Project: {escape_latex(student.project_title)}")
                if student.current_position: description_parts.append(f"Current Position: {escape_latex(student.current_position)}")
                description = " \\\\ ".join(description_parts)
                tex_content.append(f"\\cventry{{{escape_latex(student.name)}}}{{{level_degree_inst}}}{{{dates}}}{{{description}}}")
            tex_content.append("\\end{cventries}")

        # Professional Service
        if services.exists():
            tex_content.append("\\section{Selected Professional Service}")
            tex_content.append("\\begin{cventries}")
            def format_month_year_service(date): # Renamed function
                if not date: return ""
                return f"{date.strftime('%b %Y')}"
            for service in services:
                start_str = format_month_year_service(service.start_date)
                end_str = format_month_year_service(service.end_date)
                if start_str and end_str:
                     dates = f"{start_str} -- {end_str}"
                elif start_str:
                     dates = start_str
                elif service.year: # Fallback to year if dates are missing
                    dates = str(service.year)
                    if service.end_year and service.end_year != service.year:
                        dates += f" -- {service.end_year}"
                else:
                    dates = "" # No date info
                # Use role display name directly if title is missing, otherwise put role in description
                role_display_text = escape_latex(service.get_role_display()) # Corrected method name
                title = escape_latex(service.title) if service.title else role_display_text
                org = escape_latex(service.organization)
                # If title was used, put role in description, otherwise leave description empty
                desc = role_display_text if service.title else "" # Use the fetched display text
                tex_content.append(f"\\cventry{{{title}}}{{{org}}}{{{dates}}}{{{desc}}}")
            tex_content.append("\\end{cventries}")

        # Professional References
        if professional_references.exists():
            tex_content.append("\\section{Professional References}")
            tex_content.append("\\begin{cventries}")
            for ref in professional_references:
                title_inst = f"{escape_latex(ref.title)}, {escape_latex(ref.institution)}"
                description_parts = []
                if ref.email: description_parts.append(f"Email: \\href{{mailto:{escape_latex(ref.email)}}}{{{escape_latex(ref.email)}}}")
                if ref.phone: description_parts.append(f"Phone: {escape_latex(ref.phone)}")
                if ref.relationship: description_parts.append(f"Relationship: {escape_latex(ref.relationship)}")
                description = " \\\\ ".join(description_parts)
                tex_content.append(f"\\cventry{{{escape_latex(ref.name)}}}{{{title_inst}}}{{}}{{{description}}}")
            tex_content.append("\\end{cventries}")

        tex_content.append("\\end{document}")
        final_tex_string = "\n".join(tex_content)

        # --- 3. WRITE .TEX FILE AND COMPILE ---
        # ... (rest of the compilation, saving, and cleanup logic remains the same) ...
        # A temporary directory for LaTeX compilation
        temp_dir = os.path.join(settings.BASE_DIR, 'temp_cv')
        os.makedirs(temp_dir, exist_ok=True)

        # Copy the style file to the temp directory
        style_file_src = os.path.join(settings.BASE_DIR, 'academic', 'tex', 'academic-cv.sty')
        style_file_dest = os.path.join(temp_dir, 'academic-cv.sty')
        if os.path.exists(style_file_src):
             shutil.copy2(style_file_src, style_file_dest)
             self.stdout.write(f"Copied style file to {temp_dir}")
        else:
             self.stderr.write(f"Warning: Style file not found at {style_file_src}")


        tex_file_path = os.path.join(temp_dir, 'cv.tex')
        pdf_file_path = os.path.join(temp_dir, 'cv.pdf')
        try:
            with open(tex_file_path, 'w', encoding='utf-8') as f:
                f.write(final_tex_string)
        except Exception as e:
            self.stderr.write(f"Error writing .tex file: {e}")
            shutil.rmtree(temp_dir) # Clean up temp dir on error
            return

        for i in range(2): # Run twice for cross-referencing
            self.stdout.write(f"Running pdflatex compilation (Pass {i+1}/2)...")
            try:
                process = subprocess.run(
                    ['pdflatex', '-interaction=nonstopmode', f'-output-directory={temp_dir}', tex_file_path],
                    capture_output=True, text=True, encoding='utf-8', check=True # Added check=True
                )
            except FileNotFoundError:
                 self.stderr.write(self.style.ERROR('pdflatex command not found. Make sure LaTeX is installed and in your PATH.'))
                 shutil.rmtree(temp_dir)
                 return
            except subprocess.CalledProcessError as e:
                self.stderr.write(self.style.ERROR(f'PDFLaTeX compilation failed! Return code: {e.returncode}'))
                log_file = os.path.join(temp_dir, 'cv.log')
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as log: # Added encoding and error handling
                        # Try to find common errors
                        log_content = log.read()
                        if "Undefined control sequence" in log_content:
                            self.stderr.write("Potential Error: Undefined control sequence detected. Check for typos or missing packages in academic-cv.sty.")
                        elif "! LaTeX Error:" in log_content:
                             self.stderr.write("Potential Error: General LaTeX error detected. Review the log file.")
                        # Print relevant part of the log or full log if short
                        log_lines = log_content.splitlines()
                        error_lines = [line for line in log_lines if line.startswith('!') or 'Error' in line]
                        if error_lines:
                             self.stderr.write("Relevant log lines:\n" + "\n".join(error_lines[:15])) # Show first 15 error lines
                        elif len(log_lines) < 100 :
                             self.stderr.write("Full log file content:\n" + log_content)
                        else:
                             self.stderr.write(f"Log file '{log_file}' contains more details.")

                except FileNotFoundError:
                    self.stderr.write("Could not find log file. Raw pdflatex stdout:")
                    self.stderr.write(e.stdout or "None")
                    self.stderr.write("Raw pdflatex stderr:")
                    self.stderr.write(e.stderr or "None")
                # Removed 'return' to allow second pass attempt even if first fails
            except Exception as e:
                 self.stderr.write(self.style.ERROR(f'An unexpected error occurred during pdflatex execution: {e}'))
                 shutil.rmtree(temp_dir)
                 return

        if not os.path.exists(pdf_file_path):
             self.stderr.write(self.style.ERROR(f"PDF file was not generated at {pdf_file_path}. Check logs."))
             shutil.rmtree(temp_dir)
             return

        self.stdout.write(self.style.SUCCESS(f"Successfully generated cv.pdf in {temp_dir}"))

        # --- 4. UPLOAD TO S3 OR SAVE LOCALLY ---
        # (Assuming profile object is fetched earlier)
        if not profile:
             self.stderr.write("Profile not loaded, cannot save CV.")
             shutil.rmtree(temp_dir)
             return

        try:
             with open(pdf_file_path, 'rb') as pdf_file_content:
                  # Delete old file before saving new one to ensure consistent filename
                  if profile.cv:
                       profile.cv.delete(save=False)
                  profile.cv.save('cv.pdf', File(pdf_file_content), save=True) # Save directly to model field

             if settings.PRODUCTION:
                  self.stdout.write(self.style.SUCCESS(f'Production mode: Successfully uploaded and linked {profile.cv.name} to profile.'))
             else:
                  self.stdout.write(self.style.SUCCESS(f'Development mode: Successfully saved new CV to {profile.cv.path}'))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Failed to save or upload CV: {e}'))
            # Optionally: Add more specific error handling for S3 vs local storage

        # --- 5. CLEAN UP AUXILIARY FILES ---
        try:
            shutil.rmtree(temp_dir)
            self.stdout.write("Cleaned up temporary directory.")
        except OSError as e:
            self.stderr.write(f"Error removing temporary directory {temp_dir}: {e}")