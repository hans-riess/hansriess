from django.db import models


# Subsections of Section I.B ("Publications, Presentations, Posters") of the
# official Georgia Tech research-faculty CV. Both Reference and Talk feed these,
# so the choices live at module level and are shared by the two models.
GT_PUB_CATEGORIES = [
    ('journal', 'Published Journal Papers'),
    ('invited_conf', 'Invited Conference Presentations'),
    ('proc_refereed', 'Conference Presentations with Proceedings (refereed)'),
    ('proc_nonrefereed', 'Conference Presentations with Proceedings (non-refereed)'),
    ('no_proc', 'Conference Presentations without Proceedings'),
    ('submitted', 'Submitted Journal Papers in Review'),
]

GT_PUB_CATEGORY_ORDER = [key for key, _ in GT_PUB_CATEGORIES]

PRE_GT_HELP = (
    "Marks the entry with * (completed before the Georgia Tech hire date). "
    "Leave unset to derive it from the date and the profile's GT hire date."
)

CREDIT_HELP = (
    "CRediT roles, comma separated, e.g. 'conceptualization, methodology, review, "
    "and editing'. Rendered as 'Contributed ....'"
)

CV_REF_HELP = (
    "Cross-reference handle. Write [[ref:this-slug]] in any CV prose field to "
    "produce a live reference such as I.B.3.4."
)


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
    cv = models.FileField(upload_to='profile/', blank=True, null=True)
    cv_button = models.BooleanField(blank=True, null=True)
    show_publications = models.BooleanField(
        default=True,
        help_text="Show the publications list on the home page.",
    )
    headshot = models.ImageField(upload_to='profile/', blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)
    blue_sky = models.URLField(blank=True, null=True)
    youtube = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)
    github = models.URLField(blank=True, null=True)
    google_scholar = models.URLField(blank=True, null=True)
    orcid = models.URLField(blank=True, null=True)
    under_construction = models.BooleanField(default=False, help_text="Show under construction notice on website")
    # --- Georgia Tech CV ---
    fields_of_interest = models.TextField(
        blank=True,
        help_text="Semicolon-separated research interests, printed under CURRENT FIELDS OF INTEREST.",
    )
    gt_hire_date = models.DateField(
        blank=True, null=True,
        help_text="Georgia Tech hire date. Work completed before this date is marked with *.",
    )
    research_program = models.TextField(
        blank=True,
        help_text="Section IV.A narrative. Blank lines separate paragraphs. Supports [[ref:slug]].",
    )
    cv_show_all_references = models.BooleanField(
        default=False,
        help_text="List every publication regardless of status. When off, only accepted "
                  "and published work appears, plus journal articles and preprints in review.",
    )
    cv_show_preamble_sections = models.BooleanField(
        default=True,
        help_text="Print EDUCATION and PROFESSIONAL APPOINTMENTS before Section I. "
                  "The strict GT format omits both.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def gt_key_note(self):
        """The '*' line of the CV's KEY block, with the hire date filled in."""
        if self.gt_hire_date:
            when = self.gt_hire_date.strftime('%B %-d, %Y')
            return f"Completed prior to the candidate's Georgia Tech hire date ({when})."
        return "Completed prior to the candidate's Georgia Tech hire date."

    # Post-nominals that are part of the display name but never part of the
    # name as it appears in an author list.
    NAME_SUFFIXES = {'ph.d.', 'ph.d', 'phd', 'm.d.', 'md', 'd.sc.', 'sc.d.',
                     'jr.', 'jr', 'sr.', 'sr', 'ii', 'iii', 'iv', 'esq.'}

    def name_parts(self):
        """The name split into words, with post-nominal suffixes removed."""
        parts = [p for p in self.name.replace(',', ' ').split() if p]
        trimmed = [p for p in parts if p.lower() not in self.NAME_SUFFIXES]
        return trimmed or parts

    def plain_name(self):
        """The name without post-nominals, e.g. 'Hans Riess'."""
        return " ".join(self.name_parts())

    def surname(self):
        """Last word of the name, used to bold the candidate in author lists."""
        parts = self.name_parts()
        return parts[-1] if parts else ""

    @property
    def display_website(self):
        """
        Returns the website URL for display, stripped of the 'https://' or 'http://' prefix.
        """
        if self.website:
            return self.website.replace("https://", "").replace("http://", "")
        return ""

    def generate_cv_url(self):
        """
        Returns the URL to generate the CV.
        """
        return f"{self.website}/generate_cv/"

    def __str__(self):
        return self.name

class Quote(models.Model):
    author = models.CharField(max_length=200, blank=True, null=True, help_text="Author of the quote")
    quote = models.TextField(max_length=2000, blank=True, null=True, help_text="A stylized quote to display in the footer")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.author}"

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

class Figure(models.Model):
    name = models.CharField (max_length=100)
    image = models.ImageField(upload_to='figures/', blank=True, null=True)
    caption = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Reference(models.Model):
    """Database of papers and books"""
    MEDIUM_CHOICES = [
        ('journal_article', 'Journal Article'),
        ('conference_proceedings', 'Conference Proceedings'),
        ('preprint', 'Preprint'),
        ('book', 'Book'),
        ('book_chapter', 'Book Chapter'),
        ('technical_report', 'Technical Report'),
        ('thesis', 'Thesis'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('in_review', 'In review'),
        ('accepted', 'Accepted'),
        ('published', 'Published'),
        ('rejected', 'Rejected'),
    ]

    title = models.CharField(max_length=500)
    authors = models.CharField(max_length=1000, default="Unknown Author")
    alphabetical_order = models.BooleanField(default=False, help_text="Check if authors are listed in alphabetical order")
    shared_first_author = models.BooleanField(default=False, help_text="Check if first authorship is shared")
    year = models.IntegerField()
    publication_date = models.DateField(
        blank=True, null=True,
        help_text="Full date, used to order entries correctly within a year. "
                  "Falls back to the year alone when blank.",
    )
    medium = models.CharField(max_length=40, choices=MEDIUM_CHOICES)
    refereed = models.BooleanField(default=False, help_text="Check if the venue is refereed")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='published')
    journal = models.CharField(max_length=200, blank=True)
    volume = models.CharField(max_length=50, blank=True)
    issue = models.CharField(max_length=50, blank=True)
    pages = models.CharField(max_length=50, blank=True)
    doi = models.CharField(max_length=100, blank=True)
    url = models.URLField(blank=True)
    pdf_file = models.FileField(upload_to='references/papers/', blank=True)
    slug = models.SlugField(max_length=300, unique=True, blank=True, null=True, help_text="Short URL slug for sharing")
    reference_image = models.ImageField(upload_to='references/images/', blank=True, null=True, help_text="Optional image for the publication (e.g., graph, diagram)")
    abstract = models.TextField(blank=True)
    keywords = models.CharField(max_length=500, blank=True, help_text="Comma-separated list of keywords")
    code = models.URLField(blank=True, help_text="Link to the code repository")
    credit_roles = models.CharField(max_length=500, blank=True, help_text=CREDIT_HELP)
    pre_gt_hire = models.BooleanField(null=True, blank=True, help_text=PRE_GT_HELP)
    arxiv_id = models.CharField(max_length=50, blank=True, help_text="arXiv identifier, e.g. 2501.03890")
    cv_ref_slug = models.SlugField(max_length=100, blank=True, null=True, unique=True, help_text=CV_REF_HELP)

    class Meta:
        ordering = ['-year', 'title']

    def get_short_title(self):
        """
        Returns the first 3 key words of the title excluding articles and prepositions,
        with the first word capitalized.
        """
        # Define a list of words to exclude
        exclude_words = ["the", "a", "an", "of", "and", "or", "on", "in", "to", "with", "as", "by", "for", "from", "into", "onto", "over", "under", "upon", "with", "towards"]
        
        # Split the title into words and filter out the excluded words
        words = [word for word in self.title.split(" ") if word.lower() not in exclude_words]
        
        short_title_words = words[:3]
        if short_title_words:
            short_title_words[0] = short_title_words[0].capitalize()
        return " ".join(short_title_words)

    def get_gt_category(self):
        """Which Section I.B subsection this belongs in, from medium/refereed/status.

        Returns "" for anything the Georgia Tech format has no subsection for —
        theses (printed in Section I.A), technical reports (Section II.A), books,
        book chapters, and rejected work.
        """
        if self.status == 'rejected':
            return ""
        if self.medium == 'journal_article':
            return 'submitted' if self.status == 'in_review' else 'journal'
        if self.medium == 'conference_proceedings':
            return 'proc_refereed' if self.refereed else 'proc_nonrefereed'
        if self.medium == 'preprint':
            # A preprint is only a CV entry while it is under review; once it is
            # accepted or published it is listed under its final venue instead.
            return 'submitted' if self.status == 'in_review' else ""
        return ""

    def show_on_cv(self, show_all=False):
        """Whether this belongs on the CV under the default status filter.

        Accepted and published work always appears. Work in review appears only
        for journal articles and preprints — a conference submission is not
        listed until it is accepted. Rejected work never appears. Ticking
        'show all references' on the profile overrides all of this.
        """
        if show_all:
            return self.status != 'rejected'
        if self.status in ('accepted', 'published'):
            return True
        if self.status == 'in_review':
            return self.medium in ('journal_article', 'preprint')
        return False

    def get_status_note(self):
        """The status phrase that closes the citation, e.g. 'to appear'."""
        if self.status == 'accepted':
            return "to appear"
        if self.status == 'in_review' and self.journal:
            return "Submitted to %s" % self.journal
        return ""

    def cv_sort_key(self):
        """Sort key for Section I.B: full date when known, else the year."""
        if self.publication_date:
            return (self.publication_date.year, self.publication_date.month,
                    self.publication_date.day, self.title)
        return (self.year or 0, 12, 31, self.title)

    def cv_date(self):
        """The date used for the pre-hire marker and for ordering."""
        import datetime
        if self.publication_date:
            return self.publication_date
        return datetime.date(self.year, 12, 31) if self.year else None

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
    
    course_code = models.CharField(max_length=20,blank=True, null=True, help_text="Course code (e.g., CS101, MATH 201)")
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
    # --- Georgia Tech CV (Section I.E, Knowledge Sharing) ---
    organization = models.CharField(
        max_length=200, blank=True,
        help_text="Institution/Organization column. Defaults to the institution above.",
    )
    when_taught = models.CharField(
        max_length=100, blank=True,
        help_text="'When Taught' column, e.g. 'May 2026'. Defaults to the semester and year.",
    )
    curriculum_role = models.TextField(
        blank=True, help_text="'Role in Curriculum Development' column.",
    )
    attendee_count = models.CharField(
        max_length=50, blank=True,
        help_text="'Approx. Number of Students/Attendees' column, e.g. '~30'.",
    )
    pre_gt_hire = models.BooleanField(null=True, blank=True, help_text=PRE_GT_HELP)
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

    def get_cv_organization(self):
        return self.organization or self.institution

    def get_cv_when_taught(self):
        return self.when_taught or self.get_full_semester()

    def get_cv_title(self):
        """Course title with the code in parentheses, as the GT table prints it."""
        if self.course_code:
            return f"{self.title} ({self.course_code})"
        return self.title

    def get_cv_role(self):
        return self.curriculum_role or self.get_role_display()


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
    invited = models.BooleanField(default=False, help_text="Check if this is an invited talk")
    proceedings = models.BooleanField(
        default=False, help_text="Check if the presentation appeared in conference proceedings",
    )
    date = models.DateField(help_text="Date of the talk")
    slides = models.FileField(upload_to='talks/slides/', blank=True, null=True, help_text="Upload slides file")
    poster = models.FileField(upload_to='talks/posters/', blank=True, null=True, help_text="Upload poster file")
    slug = models.SlugField(max_length=300, unique=True, blank=True, null=True, help_text="Short URL slug for sharing")

    event_url = models.URLField(blank=True, null=True, help_text="URL to the event website")
    related_publications = models.ManyToManyField('Reference', blank=True, help_text="Related publications or papers")
    reference = models.ForeignKey(
        'Reference', on_delete=models.SET_NULL, blank=True, null=True,
        related_name='presentations',
        help_text="The paper this presentation is of. Linked papers are cited once, "
                  "under the paper's own entry.",
    )
    credit_roles = models.CharField(max_length=500, blank=True, help_text=CREDIT_HELP)
    pre_gt_hire = models.BooleanField(null=True, blank=True, help_text=PRE_GT_HELP)
    note = models.TextField(
        blank=True,
        help_text="Bracketed note after the entry, e.g. 'Invited speaker among 10 others.'",
    )
    curriculum_role = models.TextField(
        blank=True,
        help_text="'Role in Curriculum Development' column, for tutorials and workshops "
                  "listed under Knowledge Sharing.",
    )
    attendee_count = models.CharField(
        max_length=50, blank=True,
        help_text="Approximate attendance, e.g. '~30'. Used in the Knowledge Sharing table.",
    )
    cv_ref_slug = models.SlugField(max_length=100, blank=True, null=True, unique=True, help_text=CV_REF_HELP)
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

    # Presentations that teach rather than report go to Section I.E rather than I.B.
    KNOWLEDGE_SHARING_TYPES = ('tutorial', 'workshop')
    CONFERENCE_TYPES = ('conference', 'keynote', 'panel', 'poster')

    def is_knowledge_sharing(self):
        """Whether this belongs in Section I.E rather than Section I.B."""
        return self.talk_type in self.KNOWLEDGE_SHARING_TYPES

    def get_gt_category(self):
        """Which Section I.B subsection this belongs in.

        Tutorials and workshops are knowledge sharing and are excluded here.
        Anything that is not a conference presentation lands in 'without
        proceedings'; a conference presentation is placed by whether it had
        proceedings and, if so, whether the linked paper was refereed.
        """
        if self.is_knowledge_sharing():
            return ""
        if self.talk_type not in self.CONFERENCE_TYPES:
            return 'no_proc'
        if self.proceedings:
            refereed = self.reference.refereed if self.reference else False
            return 'proc_refereed' if refereed else 'proc_nonrefereed'
        return 'invited_conf' if self.invited else 'no_proc'

    def cv_sort_key(self):
        if self.date:
            return (self.date.year, self.date.month, self.date.day, self.title)
        return (0, 12, 31, self.title)
    
    def get_formatted_date(self):
        """Returns a formatted date string"""
        return self.date.strftime('%B %d, %Y')

    def get_short_title(self):
        """Returns the first 3 key words of the title excluding articles and prepositions"""
        # Define a list of words to exclude
        exclude_words = ["the", "a", "an", "of", "and", "or", "on", "in", "to", "with", "as", "by", "for", "from", "into", "onto""over","under", "upon", "with", "towards"]
        
        # Split the title into words and filter out the excluded words
        words = [word for word in self.title.split(" ") if word.lower() not in exclude_words]

        return " ".join(words[:3])
    
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
    short_title = models.CharField(max_length=100, blank=True, null=True, help_text="A shorter title for display purposes")
    slug = models.SlugField(max_length=300, unique=True, blank=True, null=True, help_text="URL-friendly version of the title")
    description = models.TextField(blank=True, help_text="A description of the grant or project")
    image = models.ImageField(upload_to='grants/', blank=True, null=True, help_text="Image for the grant")
    funding_agency = models.CharField(max_length=200, help_text="Funding agency or organization")
    program_manager = models.CharField(max_length=200, blank=True, null=True, help_text="Program manager at the funding agency")
    sponsor_logo = models.ImageField(upload_to='grants/sponsor_logos/', blank=True, null=True, help_text="Logo of the sponsoring organization")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='pi')
    amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, help_text="Total grant amount")
    currency = models.CharField(max_length=3, default='USD', help_text="Currency code (USD, EUR, etc.)")
    start_date = models.DateField(blank=True,null=True,help_text="Start date of the grant")
    end_date = models.DateField(blank=True,null=True,help_text="End date of the grant")
    co_pis = models.CharField(max_length=300, blank=True, help_text="Co-PIs (optional, comma-separated)")
    grant_number = models.CharField(max_length=100, blank=True, null=True, help_text="Grant/award number (optional)")
    related_publications = models.ManyToManyField('Reference', blank=True, help_text="Related publications or papers")
    password_protected = models.BooleanField(default=False, help_text="Enable password protection for this grant's page")
    password = models.CharField(max_length=128, blank=True, help_text="Password for this grant's page (if password protected)")
    pi_name = models.CharField(
        max_length=300, blank=True,
        help_text="P.I. of record. Defaults to the profile name. One per line for multiple PIs.",
    )
    candidate_role_text = models.CharField(
        max_length=200, blank=True,
        help_text="Candidate's Role, e.g. 'Task Leader (Key Personnel)'. Overrides the role above.",
    )
    task_title = models.CharField(max_length=300, blank=True, help_text="Task Title, for Center-style awards.")
    contributions = models.TextField(
        blank=True, help_text="'Contributions' row of the Section III.A table. Supports [[ref:slug]].",
    )
    report_series_note = models.TextField(
        blank=True,
        help_text="Preamble for this award's report series in Section II.A (authorship, sponsor notes).",
    )
    cv_ref_slug = models.SlugField(max_length=100, blank=True, null=True, unique=True, help_text=CV_REF_HELP)

    class Meta:
        ordering = ['-start_date', 'title']
        verbose_name = "Grant"
        verbose_name_plural = "Grants"

    def __str__(self):
        return f"{self.title} ({self.funding_agency})"

    def get_formatted_amount(self):
        if self.amount:
            return f"{self.amount:,.0f} {self.currency}"
        return ""

    def get_cv_amount(self):
        """Amount as the CV tables print it: '$180,687'."""
        return self._cv_currency(self.amount)

    def _cv_currency(self, value):
        if value is None:
            return ""
        if self.currency == 'USD':
            return f"${value:,.0f}"
        return f"{value:,.0f} {self.currency}"
    
    def get_date_range(self):
        """
        Returns a date range string in the format 'Feb 2020 - June 2021' or 'Feb 2020 - Present'
        """
        if self.start_date:
            start_str = self.start_date.strftime('%b %Y')
        else:
            start_str = ""
        if self.end_date:
            end_str = self.end_date.strftime('%b %Y')
        else:
            end_str = "Present"
        return f"{start_str} - {end_str}"

    def get_role_display_name(self):
        return self.get_role_display()

    def get_cv_role(self):
        return self.candidate_role_text or self.get_role_display()

    def get_period_of_performance(self):
        """Date range with an en dash, as the GT tables print it."""
        if not self.start_date and not self.end_date:
            return ""
        start = self.start_date.strftime('%b %Y') if self.start_date else ""
        end = self.end_date.strftime('%b %Y') if self.end_date else "Present"
        return f"{start} – {end}"


class Milestone(models.Model):
    """Model for grant milestones"""
    grant = models.ForeignKey(Grant, on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=300, help_text="Title of the milestone")
    slug = models.SlugField(max_length=300, unique=True, blank=True, null=True, help_text="URL-friendly version of the title")
    date = models.DateField(help_text="Date of the milestone")
    description = models.TextField(blank=True, help_text="A description of the milestone")
    report = models.FileField(upload_to='milestones/reports/', blank=True, null=True, help_text="Upload report file")
    slides = models.FileField(upload_to='milestones/slides/', blank=True, null=True, help_text="Upload slides file")

    class Meta:
        ordering = ['-date', 'title']
        verbose_name = "Milestone"
        verbose_name_plural = "Milestones"

    def __str__(self):
        return f"{self.title} ({self.grant.title})"


class Education(models.Model):
    """Minimal model for academic degrees (CV style)"""
    degree_type = models.CharField(max_length=20, help_text="Type of degree")
    degree_type_short = models.CharField(max_length=20, blank=True, null=True, help_text="Short form of degree type")
    field_of_study = models.CharField(max_length=200, help_text="Field of study or major")
    institution = models.CharField(max_length=200, help_text="University or institution name")
    location = models.CharField(max_length=200, blank=True, help_text="City, State/Province, Country")
    graduation_year = models.PositiveIntegerField(help_text="Year of graduation")
    gpa = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True, help_text="GPA (optional)")
    thesis_title = models.CharField(max_length=300, blank=True, help_text="Thesis title (for graduate degrees)")
    advisor = models.CharField(max_length=200, blank=True, help_text="Thesis advisor (for graduate degrees)")
    honors = models.CharField(max_length=200, blank=True, help_text="Honors or distinctions")
    related_publications = models.ManyToManyField('Reference', blank=True, help_text="Related publications or papers")
    # --- Georgia Tech CV ---
    thesis_url = models.URLField(blank=True, help_text="Link to the thesis or dissertation record.")
    is_dissertation = models.BooleanField(
        default=False,
        help_text="Print this degree's thesis in Section I.A (Thesis/Dissertation).",
    )
    pre_gt_hire = models.BooleanField(null=True, blank=True, help_text=PRE_GT_HELP)
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
    start_date = models.DateField(null=True,blank=True )
    end_date = models.DateField(null=True,blank=True)
    year = models.PositiveIntegerField(help_text="Year of service")
    end_year = models.PositiveBigIntegerField(blank=True,null=True,help_text="End year (if applicable)")
    location = models.CharField(max_length=200, blank=True, help_text="Location if relevant")
    # --- Georgia Tech CV (Section V, Outreach and Service) ---
    GT_SERVICE_CATEGORIES = [
        ('journal_review', 'A. Reviewer Work for Technical Journals'),
        ('conference_review', 'B. Reviewer Work for Conferences'),
        ('session_chair', 'C. Conference Session Chairs'),
        ('special_activity', 'D. Special Activities'),
        ('outside_professional', 'E. Outside Professional Activities/Consulting'),
        ('civic', 'F. Civic Activities'),
    ]

    gt_category = models.CharField(
        max_length=30, choices=GT_SERVICE_CATEGORIES, blank=True,
        help_text="Section V subsection. Leave blank to derive it from the service type and role.",
    )
    manuscript_count = models.PositiveIntegerField(
        blank=True, null=True, help_text="Number of manuscripts reviewed, e.g. '(1 manuscript)'.",
    )
    detail = models.TextField(blank=True, help_text="Additional prose printed after the entry. Supports [[ref:slug]].")
    pre_gt_hire = models.BooleanField(null=True, blank=True, help_text=PRE_GT_HELP)
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

    def get_gt_category(self):
        """Section V subsection, falling back to a guess from the service type and role."""
        if self.gt_category:
            return self.gt_category
        if self.role == 'reviewer':
            return 'conference_review' if self.service_type == 'conference' else 'journal_review'
        if self.role in ('chair', 'co_chair'):
            return 'session_chair'
        if self.service_type == 'volunteer' or self.role == 'volunteer':
            return 'civic'
        return 'special_activity'

class Student(models.Model):
    """Model for tracking student mentorship"""
    LEVEL_CHOICES = [
        ('undergrad', 'Undergraduate'),
        ('masters', 'Masters'),
        ('phd', 'PhD'),
        ('postdoc', 'Postdoc'),
        ('highschool', 'High School'),
        ('other', 'Other'),
    ]
    # New Mentorship Role Choices
    MENTORSHIP_ROLE_CHOICES = [
        ('advisor', 'Thesis Advisor'),
        ('co_advisor', 'Thesis Co-Advisor'),
        ('committee', 'Committee Member'),
        ('', 'Informal Mentorship'), # Blank value for informal
    ]

    name = models.CharField(max_length=200)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, help_text="Level of the student")
    degree = models.CharField(max_length=100, blank=True, help_text="Degree pursued (e.g., B.S. in Math, PhD in ESE)") # New field
    mentorship_role = models.CharField(max_length=20, choices=MENTORSHIP_ROLE_CHOICES, blank=True, help_text="Your role in mentoring this student") # New field
    institution = models.CharField(max_length=200, help_text="Institution student is enrolled at")
    project_title = models.CharField(max_length=300, blank=True, help_text="Title of the research project (optional)")
    start_date = models.DateField(help_text="Start date of mentorship")
    end_date = models.DateField(blank=True, null=True, help_text="End date (leave blank if ongoing)")
    current_position = models.CharField(max_length=300, blank=True, help_text="Current position or status (optional)")
    # --- Georgia Tech CV (Section III.B) ---
    research_topic = models.CharField(
        max_length=300, blank=True,
        help_text="'Research topic: ...'. Defaults to the project title above.",
    )
    advisor_of_record = models.CharField(
        max_length=300, blank=True, help_text="Advisor of record for the student's degree program.",
    )
    host_lab = models.CharField(max_length=300, blank=True, help_text="Host lab, with its director if relevant.")
    appointment_note = models.CharField(
        max_length=200, blank=True, help_text="Nature of the appointment, e.g. 'Summer intern'.",
    )
    resulting_publications = models.ManyToManyField(
        'Reference', blank=True, related_name='mentored_students',
        help_text="Publications resulting from this mentorship, cited as 'see I.B.3.2'.",
    )
    pre_gt_hire = models.BooleanField(null=True, blank=True, help_text=PRE_GT_HELP)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date', 'name']
        verbose_name = "Mentorship"
        verbose_name_plural = "Mentorships"

    def __str__(self):
        role_str = f", {self.get_mentorship_role_display()}" if self.mentorship_role else ""
        return f"{self.name} ({self.get_level_display()}{role_str})"

    def get_date_range(self):
        """Returns a date range string"""
        if self.start_date:
            start_str = self.start_date.strftime('%b %Y')
        else:
            start_str = ""
        if self.end_date:
            end_str = self.end_date.strftime('%b %Y')
        else:
            end_str = "Present"
        # Handle cases where only one date might be present, though start_date is required
        if start_str and end_str:
            return f"{start_str} -- {end_str}"
        elif start_str:
            return f"{start_str} -- Present" # Assume present if no end date
        else:
            return "" # Should not happen if start_date is required

class Award(models.Model):
    """Section I.D of the Georgia Tech CV: professional research recognition awards."""
    title = models.CharField(max_length=300, help_text="Name of the award, fellowship, or nomination")
    organization = models.CharField(max_length=300, blank=True, help_text="Awarding body, conference, or institution")
    year = models.PositiveIntegerField(blank=True, null=True)
    date_range = models.CharField(
        max_length=100, blank=True,
        help_text="Period the award covers, e.g. 'August 2017 – September 2022'. Used instead of the year.",
    )
    detail = models.TextField(blank=True, help_text="Parenthetical or explanatory prose. Supports [[ref:slug]].")
    pre_gt_hire = models.BooleanField(null=True, blank=True, help_text=PRE_GT_HELP)
    cv_ref_slug = models.SlugField(max_length=100, blank=True, null=True, unique=True, help_text=CV_REF_HELP)
    order = models.PositiveIntegerField(default=0, help_text="Manual ordering; lower numbers print first.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-year', 'title']
        verbose_name = "Award"
        verbose_name_plural = "Awards"

    def __str__(self):
        return f"{self.title} ({self.year})" if self.year else self.title

    def get_cv_date(self):
        return self.date_range or (str(self.year) if self.year else "")


class DeliveredProduct(models.Model):
    """Section I.C of the Georgia Tech CV: key delivered products."""
    name = models.CharField(max_length=200, help_text="Short name of the product, e.g. 'Lawvere'")
    summary = models.CharField(
        max_length=500, blank=True,
        help_text="One-line description printed after the name in the heading.",
    )
    sponsor = models.CharField(max_length=300, blank=True, help_text="Sponsor or party the product was delivered to")
    date_range = models.CharField(
        max_length=200, blank=True,
        help_text="Date range for work performed by the candidate, e.g. 'May 2026 – present'.",
    )
    description = models.TextField(blank=True, help_text="Product description. Supports [[ref:slug]].")
    maturity = models.TextField(blank=True, help_text="Current maturity of the product.")
    technical_contribution = models.TextField(
        blank=True, help_text="Candidate's technical contribution. Supports [[ref:slug]].",
    )
    cv_ref_slug = models.SlugField(max_length=100, blank=True, null=True, unique=True, help_text=CV_REF_HELP)
    order = models.PositiveIntegerField(default=0, help_text="Manual ordering; lower numbers print first.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Delivered Product"
        verbose_name_plural = "Delivered Products"

    def __str__(self):
        return self.name

    def get_cv_heading(self):
        return f"{self.name} — {self.summary}" if self.summary else self.name


class Proposal(models.Model):
    """Section IV.B of the Georgia Tech CV: research proposals to sponsors."""
    RESULT_CHOICES = [
        ('pending', 'Pending'),
        ('funded', 'Funded'),
        ('recommended', 'Full proposal recommended'),
        ('not_selected', 'Not selected'),
        ('in_preparation', 'In preparation'),
    ]

    title = models.CharField(max_length=300)
    short_title = models.CharField(max_length=100, blank=True)
    slug = models.SlugField(max_length=300, unique=True, blank=True, null=True)
    sponsor = models.CharField(max_length=200, help_text="Funding agency or organization")
    solicitation = models.CharField(max_length=100, blank=True, help_text="Solicitation number")
    pi_name = models.CharField(
        max_length=300, blank=True,
        help_text="PI of record. Defaults to the profile name. One per line for multiple PIs.",
    )
    candidate_role = models.CharField(
        max_length=200, blank=True, default="Principal Investigator",
        help_text="Candidate's Role, e.g. 'Co-PI'.",
    )
    date_abstract_submitted = models.DateField(blank=True, null=True)
    date_full_submitted = models.DateField(blank=True, null=True)
    full_proposal_note = models.CharField(
        max_length=200, blank=True,
        help_text="Used instead of the full-proposal date, e.g. 'TBD (due August 25, 2026)' or 'N/A'.",
    )
    amount_requested = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=3, default='USD')
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, default='pending')
    result_note = models.CharField(
        max_length=300, blank=True,
        help_text="Free-text 'Result', used instead of the choice above when set.",
    )
    start_date = models.DateField(blank=True, null=True, help_text="Proposed period of performance")
    end_date = models.DateField(blank=True, null=True)
    contribution = models.TextField(
        blank=True, help_text="'Contribution to Proposal' row. Supports [[ref:slug]].",
    )
    grant = models.ForeignKey(
        'Grant', on_delete=models.SET_NULL, blank=True, null=True, related_name='proposals',
        help_text="The award this proposal produced, if it was funded.",
    )
    cv_ref_slug = models.SlugField(max_length=100, blank=True, null=True, unique=True, help_text=CV_REF_HELP)
    order = models.PositiveIntegerField(default=0, help_text="Manual ordering; lower numbers print first.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-date_abstract_submitted', 'title']
        verbose_name = "Proposal"
        verbose_name_plural = "Proposals"

    def __str__(self):
        return f"{self.title} ({self.sponsor})"

    def get_cv_amount(self):
        if self.amount_requested is None:
            return ""
        if self.currency == 'USD':
            return f"${self.amount_requested:,.0f}"
        return f"{self.amount_requested:,.0f} {self.currency}"

    def get_result(self):
        return self.result_note or self.get_result_display()

    def get_period_of_performance(self):
        if not self.start_date and not self.end_date:
            return ""
        start = self.start_date.strftime('%b %Y') if self.start_date else ""
        end = self.end_date.strftime('%b %Y') if self.end_date else "Present"
        return f"{start} – {end} (proposed)"


class TechReport(models.Model):
    """Section II.A of the Georgia Tech CV: research and technical reports."""
    REPORT_TYPE_CHOICES = [
        ('interim_report', 'Interim technical report'),
        ('briefing', 'Sponsor briefing'),
        ('status_report', 'Recurring status report'),
        ('final_report', 'Final technical report'),
        ('other', 'Other'),
    ]

    grant = models.ForeignKey(
        'Grant', on_delete=models.CASCADE, related_name='tech_reports',
        help_text="The award this report was delivered under. Reports are grouped by award.",
    )
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, unique=True, blank=True, null=True)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES, default='interim_report')
    date = models.DateField()
    page_count = models.PositiveIntegerField(blank=True, null=True, help_text="Length in pages, for written reports.")
    slide_count = models.PositiveIntegerField(blank=True, null=True, help_text="Length in slides, for briefings.")
    authorship_percent = models.PositiveIntegerField(blank=True, null=True, help_text="Candidate's share of authorship.")
    description = models.TextField(blank=True, help_text="Supports [[ref:slug]].")
    report = models.FileField(upload_to='reports/', blank=True, null=True)
    slides = models.FileField(upload_to='reports/slides/', blank=True, null=True)
    cv_ref_slug = models.SlugField(max_length=100, blank=True, null=True, unique=True, help_text=CV_REF_HELP)
    order = models.PositiveIntegerField(default=0, help_text="Manual ordering within the award; lower prints first.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-date', 'title']
        verbose_name = "Technical Report"
        verbose_name_plural = "Technical Reports"

    def __str__(self):
        return f"{self.title} ({self.grant.short_title or self.grant.title})"


class Innovation(models.Model):
    """Section II.B: significant technical innovation on sponsored programs."""
    title = models.CharField(max_length=500, help_text="Title of the innovation or contribution")
    grants = models.ManyToManyField(
        'Grant', blank=True, related_name='innovations',
        help_text="Awards this work was carried out under. Used for the "
                  "'Sponsors/Projects/Dates' line when that field is left blank.",
    )
    sponsors_projects_dates = models.CharField(
        max_length=300, blank=True,
        help_text="'Sponsors/Projects/Dates' line. Derived from the linked awards when blank.",
    )
    description = models.TextField(blank=True, help_text="Description. Supports [[ref:slug]].")
    technical_contributions = models.TextField(
        blank=True, help_text="Candidate's specific technical contributions. Supports [[ref:slug]].",
    )
    cv_ref_slug = models.SlugField(max_length=100, blank=True, null=True, unique=True, help_text=CV_REF_HELP)
    order = models.PositiveIntegerField(default=0, help_text="Manual ordering; lower numbers print first.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'title']
        verbose_name = "Technical Innovation"
        verbose_name_plural = "Technical Innovations"

    def __str__(self):
        return self.title

    def get_sponsors_line(self):
        """'Sponsors/Projects/Dates', derived from the linked awards when blank."""
        if self.sponsors_projects_dates:
            return self.sponsors_projects_dates
        parts = []
        for grant in self.grants.all():
            name = grant.short_title or grant.title
            period = grant.get_period_of_performance()
            parts.append(f"{name} ({period})" if period else name)
        return "; ".join(parts)


class ReferencePerson(models.Model):
    """Model for professional references (distinct from Publication References)"""
    RELATIONSHIP_CHOICES = [
        ('advisor', 'Ph.D. Advisor'),
        ('postdoc_mentor', 'Postdoc Mentor'),
        ('committee_member', 'Committee Member'),
        ('teaching_mentor', 'Teaching Mentor'),
        ('research_mentor', 'Research Mentor'),
        ('other_mentor', 'Other Mentor'),
    ]
    name = models.CharField(max_length=200)
    title = models.CharField(max_length=200, help_text="Professional title")
    institution = models.CharField(max_length=200, help_text="Institution or company")
    email = models.EmailField(blank=True, null=True)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES, default='other_mentor')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Professional Reference"
        verbose_name_plural = "Professional References"
    
    def __str__(self):
        return f"{self.name}"