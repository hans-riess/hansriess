from django.db import models


class Profile(models.Model):
    name = models.CharField(max_length=100)
    occupation = models.CharField(max_length=200, blank=True, null=True)
    title = models.CharField(max_length=200, blank=True, null=True)
    long_title = models.CharField(max_length=200, blank=True, null=True)
    department = models.CharField(max_length=200, blank=True, null=True)
    sub_department = models.CharField(max_length=200, blank=True, null=True)
    school = models.CharField(max_length=200, blank=True, null=True)
    institution = models.CharField(max_length=200, blank=True, null=True)
    long_institution = models.CharField(max_length=200, blank=True, null=True)
    bio = models.TextField(max_length=5000, blank=True, null=True)
    short_bio = models.TextField(max_length=2000, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    room_number = models.CharField(max_length=200, blank=True, null=True)
    building = models.CharField(max_length=200, blank=True, null=True)
    street = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=200, blank=True, null=True)
    state = models.CharField(max_length=200, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=200, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    cv = models.FileField(upload_to='files/', blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)
    blue_sky = models.URLField(blank=True, null=True)
    youtube = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)
    github = models.URLField(blank=True, null=True)
    google_scholar = models.URLField(blank=True, null=True)
    orcid = models.URLField(blank=True, null=True)
    quote = models.TextField(max_length=2000, blank=True, null=True, help_text="A stylized quote to display in the footer")
    quote_author = models.CharField(max_length=200, blank=True, null=True, help_text="Author of the quote")
    under_construction = models.BooleanField(default=False, help_text="Show under construction notice on website")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Collaborator(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    institution = models.CharField(max_length=200, blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    headshot = models.ImageField(upload_to='collaborators/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class Reference(models.Model):
    """Database of papers and books"""
    REFERENCE_TYPES = [
        ('paper', 'Paper'),
        ('book', 'Book'),
        ('thesis', 'Thesis'),
        ('preprint', 'Preprint'),
        ('journal_article', 'Journal Article'),
        ('conference_proceedings', 'Conference Proceedings'),
        ('book_chapter', 'Book Chapter'),        
        ('other', 'Other'),
    ]
    
    title = models.CharField(max_length=500)
    authors = models.CharField(max_length=1000, default="Unknown Author")
    alphabetical_order = models.BooleanField(default=False, help_text="Check if authors are listed in alphabetical order")
    shared_first_author = models.BooleanField(default=False, help_text="Check if first authorship is shared")
    year = models.IntegerField()
    reference_type = models.CharField(max_length=40, choices=REFERENCE_TYPES)
    journal = models.CharField(max_length=200, blank=True)
    volume = models.CharField(max_length=50, blank=True)
    issue = models.CharField(max_length=50, blank=True)
    pages = models.CharField(max_length=50, blank=True)
    doi = models.CharField(max_length=100, blank=True)
    url = models.URLField(blank=True)
    pdf_file = models.FileField(upload_to='references/papers/', blank=True)
    reference_image = models.ImageField(upload_to='references/images/', blank=True, null=True, help_text="Optional image for the publication (e.g., graph, diagram)")
    abstract = models.TextField(blank=True)
    keywords = models.CharField(max_length=500, blank=True, help_text="Comma-separated list of keywords")
    code = models.URLField(blank=True, help_text="Link to the code repository")
    
    class Meta:
        ordering = ['-year', 'title']

    def get_short_title(self):
        """
        Returns the first 3 key words of the title excluding articles and prepositions
        """
        # Define a list of words to exclude
        exclude_words = ["the", "a", "an", "of", "and", "or", "on", "in", "to", "with", "as", "by", "for", "from", "into", "onto""over","under", "upon", "with", "towards"]
        
        # Split the title into words and filter out the excluded words
        words = [word for word in self.title.split(" ") if word.lower() not in exclude_words]
        
        return " ".join(words[:3])

    def __str__(self):
        return f"{self.title} ({self.year})"

class Course(models.Model):
    """Model for tracking teaching experiences"""
    SEMESTER_CHOICES = [
        ('spring', 'Spring'),
        ('summer', 'Summer'),
        ('fall', 'Fall'),
        ('winter', 'Winter')
    ]
    
    ROLE_CHOICES = [
        ('instructor', 'Instructor of Record'),
        ('teaching_assistant', 'Teaching Assistant'),
        ('guest_lecturer', 'Guest Lecturer'),
        ('other', 'Other'),
    ]
    
    course_code = models.CharField(max_length=20, help_text="Course code (e.g., CS101, MATH 201)")
    title = models.CharField(max_length=200, help_text="Full course title")
    institution = models.CharField(max_length=200, help_text="Institution where the course was taught")
    department = models.CharField(max_length=200, blank=True, null=True, help_text="Department offering the course")
    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES)
    year = models.IntegerField()
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='instructor')
    description = models.TextField(blank=True, help_text="Brief description of the course content")
    syllabus = models.FileField(upload_to='courses/syllabi/', blank=True, null=True, help_text="Course syllabus")
    is_graduate = models.BooleanField(default=False, help_text="Check if this is a graduate-level course")
    is_online = models.BooleanField(default=False, help_text="Check if this was an online course")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-year', '-semester', 'course_code']
        verbose_name = "Course"
        verbose_name_plural = "Courses"
    
    def __str__(self):
        return f"{self.course_code}: {self.title} ({self.semester.title()} {self.year})"
    
    def get_full_semester(self):
        """Returns the full semester name with year"""
        return f"{self.get_semester_display()} {self.year}"
    
    def get_role_display_name(self):
        """Returns a more readable role name"""
        return self.get_role_display().replace('_', ' ').title()


class Experience(models.Model):
    """Model for tracking academic and industry positions"""
    JOB_TYPE_CHOICES = [
        ('academic', 'Academic'),
        ('industry', 'Industry'),
        ('government', 'Government'),
        ('nonprofit', 'Non-Profit'),
        ('consulting', 'Consulting'),
        ('other', 'Other'),
    ]

    ACADEMIC_POSITION_TYPE_CHOICES = [
        ('academic_faculty', 'Academic Faculty'),
        ('research_faculty', 'Research Faculty'),
        ('teaching_faculty', 'Teaching Faculty'),
        ('lecturer', 'Lecturer'),
        ('visiting_faculty', 'Visiting Faculty'),
        ('adjunct_faculty', 'Adjunct Faculty'),
        ('postdoc', 'Postdoc'),
        ('research_assistant', 'Research Assistant'),
        ('teaching_assistant', 'Teaching Assistant'),
        ('internship', 'Internship'),
        ('REU', 'REU'),
        ('other', 'Other'),
    ]
    
    title = models.CharField(max_length=200, help_text="Job title or position")
    institution = models.CharField(max_length=200, help_text="Company, university, or organization")
    department = models.CharField(max_length=200, blank=True, null=True, help_text="Department or division")
    location = models.CharField(max_length=200, blank=True, null=True, help_text="City, State/Province, Country")
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES, default='academic')
    academic_position_type = models.CharField(max_length=20, choices=ACADEMIC_POSITION_TYPE_CHOICES, default='other')
    full_time = models.BooleanField(default=True, help_text="Check if this is a full-time position")
    tenure_track = models.BooleanField(default=False, help_text="Check if this is a tenure-track position")
    start_date = models.DateField(help_text="Start date of the position")
    end_date = models.DateField(blank=True, null=True, help_text="End date (leave blank if current)")
    is_current = models.BooleanField(default=False, help_text="Check if this is your current position")
    supervisor = models.CharField(max_length=200, blank=True, null=True, help_text="Direct supervisor or manager")
    description = models.TextField(blank=True, help_text="Brief description of responsibilities and achievements")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date', 'title']
        verbose_name = "Experience"
        verbose_name_plural = "Experiences"
    
    def __str__(self):
        end_str = f" - {self.end_date.strftime('%Y')}" if self.end_date else " - Present" if self.is_current else ""
        return f"{self.title} at {self.institution} ({self.start_date.strftime('%Y')}{end_str})"
    
    def get_duration(self):
        """Returns the duration of the position"""
        from datetime import date
        
        if self.end_date:
            end = self.end_date
        elif self.is_current:
            end = date.today()
        else:
            return "Unknown duration"
        
        delta = end - self.start_date
        years = delta.days // 365
        months = (delta.days % 365) // 30
        
        if years > 0 and months > 0:
            return f"{years} year{'s' if years != 1 else ''}, {months} month{'s' if months != 1 else ''}"
        elif years > 0:
            return f"{years} year{'s' if years != 1 else ''}"
        elif months > 0:
            return f"{months} month{'s' if months != 1 else ''}"
        else:
            return f"{delta.days} day{'s' if delta.days != 1 else ''}"
    
    def get_job_type_display_name(self):
        """Returns a more readable job type name"""
        return self.get_job_type_display()
    
class Talk(models.Model):
    """Model for tracking presentations, seminars, and speaking engagements"""
    TALK_TYPE_CHOICES = [
        ('conference', 'Conference Presentation'),
        ('seminar', 'Seminar'),
        ('workshop', 'Workshop'),
        ('tutorial', 'Tutorial'),
        ('keynote', 'Keynote'),
        ('poster', 'Poster Presentation'),
        ('panel', 'Panel Discussion'),
        ('colloquium', 'Colloquium'),
        ('guest_lecture', 'Guest Lecture'),
        ('webinar', 'Webinar'),
        ('podcast', 'Podcast'),
        ('interview', 'Interview'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=300, help_text="Title of the talk or presentation")
    abstract = models.TextField(blank=True, help_text="Abstract or description of the talk")
    venue = models.CharField(max_length=200, help_text="Conference, institution, or event name")
    location = models.CharField(max_length=200, blank=True, null=True, help_text="City, State/Province, Country")
    talk_type = models.CharField(max_length=20, choices=TALK_TYPE_CHOICES, default='other')
    is_invited = models.BooleanField(default=False, help_text="Check if this is an invited talk") 
    date = models.DateField(help_text="Date of the talk")
    slides = models.FileField(upload_to='talks/slides/', blank=True, null=True, help_text="Upload slides file")
    event_url = models.URLField(blank=True, null=True, help_text="URL to the event website")
    related_publications = models.ManyToManyField('Reference', blank=True, help_text="Related publications or papers")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', 'title']
        verbose_name = "Talk"
        verbose_name_plural = "Talks"
    
    def __str__(self):
        return f"{self.title} at {self.venue} ({self.date.strftime('%Y-%m-%d')})"
    
    def get_talk_type_display_name(self):
        """Returns a more readable talk type name"""
        return self.get_talk_type_display()
    
    def get_formatted_date(self):
        """Returns a formatted date string"""
        return self.date.strftime('%B %d, %Y')
    
class Grant(models.Model):
    """Minimal model for research funding, grants, and awards (CV style)"""

    ROLE_CHOICES = [
        ('pi', 'Principal Investigator'),
        ('co_pi', 'Co-Principal Investigator'),
        ('senior_personnel', 'Senior Personnel'),
        ('key_personnel', 'Key Personnel'),
        ('unnamed_personnel', 'Unnamed Personnel'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=300, help_text="Title of the grant or award")
    funding_agency = models.CharField(max_length=200, help_text="Funding agency or organization")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='pi')
    amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, help_text="Total grant amount")
    currency = models.CharField(max_length=3, default='USD', help_text="Currency code (USD, EUR, etc.)")
    start_year = models.PositiveIntegerField(help_text="Start year of the grant")
    end_year = models.PositiveIntegerField(blank=True, null=True, help_text="End year of the grant (if applicable)")
    co_pis = models.CharField(max_length=300, blank=True, help_text="Co-PIs (optional, comma-separated)")
    grant_number = models.CharField(max_length=100, blank=True, null=True, help_text="Grant/award number (optional)")
    related_publications = models.ManyToManyField('Reference', blank=True, help_text="Related publications or papers")

    class Meta:
        ordering = ['-start_year', 'title']
        verbose_name = "Grant"
        verbose_name_plural = "Grants"

    def __str__(self):
        years = f"{self.start_year}"
        if self.end_year:
            years += f"–{self.end_year}"
        return f"{self.title} ({self.funding_agency}, {years})"

    def get_formatted_amount(self):
        if self.amount:
            return f"{self.amount:,.0f} {self.currency}"
        return ""

    def get_role_display_name(self):
        return self.get_role_display()


class Education(models.Model):
    """Minimal model for academic degrees (CV style)"""
    degree_type = models.CharField(max_length=20, help_text="Type of degree")
    field_of_study = models.CharField(max_length=200, help_text="Field of study or major")
    institution = models.CharField(max_length=200, help_text="University or institution name")
    location = models.CharField(max_length=200, blank=True, help_text="City, State/Province, Country")
    graduation_year = models.PositiveIntegerField(help_text="Year of graduation")
    gpa = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True, help_text="GPA (optional)")
    thesis_title = models.CharField(max_length=300, blank=True, help_text="Thesis title (for graduate degrees)")
    advisor = models.CharField(max_length=200, blank=True, help_text="Thesis advisor (for graduate degrees)")
    honors = models.CharField(max_length=200, blank=True, help_text="Honors or distinctions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-graduation_year', 'degree_type']
        verbose_name = "Education"
        verbose_name_plural = "Education"
    
    def __str__(self):
        return f"{self.get_degree_type_display()} in {self.field_of_study}, {self.institution} ({self.graduation_year})"
    
    def get_degree_type_display(self):
        return self.degree_type
    
    def get_cv_format(self):
        """Returns CV-friendly format"""
        degree = self.get_degree_type_display()
        location_str = f", {self.location}" if self.location else ""
        gpa_str = f", GPA: {self.gpa}" if self.gpa else ""
        thesis_str = f", Thesis: {self.thesis_title}" if self.thesis_title else ""
        advisor_str = f", Advisor: {self.advisor}" if self.advisor else ""
        honors_str = f", {self.honors}" if self.honors else ""
        
        return f"{degree} in {self.field_of_study}, {self.institution}{location_str} ({self.graduation_year}){gpa_str}{thesis_str}{advisor_str}{honors_str}"


class Service(models.Model):
    """Minimal model for professional service activities (CV style)"""
    SERVICE_TYPE_CHOICES = [
        ('conference', 'Conference'),
        ('journal', 'Journal'),
        ('seminar', 'Seminar'),
        ('committee', 'Committee'),
        ('volunteer', 'Volunteer'),
        ('other', 'Other'),
    ]
    
    ROLE_CHOICES = [
        ('chair', 'Chair'),
        ('co_chair', 'Co-Chair'),
        ('organizer', 'Organizer'),
        ('reviewer', 'Reviewer'),
        ('member', 'Member'),
        ('volunteer', 'Volunteer'),
        ('other', 'Other'),
    ]
    
    title = models.CharField(max_length=200, blank=True, help_text="Title or description of the service")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    organization = models.CharField(max_length=200, help_text="Organization, conference, journal, or institution")
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPE_CHOICES, default='other')
    year = models.PositiveIntegerField(help_text="Year of service")
    location = models.CharField(max_length=200, blank=True, help_text="Location if relevant")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-year', 'title']
        verbose_name = "Service"
        verbose_name_plural = "Service"
    
    def __str__(self):
        return f"{self.title} at {self.organization} ({self.year})"
    
    def get_cv_format(self):
        """Returns CV-friendly format"""
        role_display = self.get_role_display()
        location_str = f", {self.location}" if self.location else ""
        return f"{role_display}, {self.title}, {self.organization}{location_str} ({self.year})"