from django.db import models
from django.utils.safestring import mark_safe

class Profile(models.Model):
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=200)
    bio = models.TextField(max_length=5000)
    email = models.EmailField(blank=True, null=True)
    office = models.CharField(max_length=200, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    cv = models.FileField(upload_to='files/', blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)
    github = models.URLField(blank=True, null=True)
    google_scholar = models.URLField(blank=True, null=True)
    department = models.CharField(max_length=200, blank=True, null=True)
    school = models.CharField(max_length=200, blank=True, null=True)
    institution = models.CharField(max_length=200, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Author(models.Model):
    """Database of authors"""
    name = models.CharField(max_length=200)
    is_profile_owner = models.BooleanField(default=False, help_text="Check if this author is the profile owner")
    affiliation = models.CharField(max_length=300, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Remove default ordering to allow ManyToMany fields to preserve selection order
        pass

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
    authors = models.ManyToManyField(Author, related_name='references', blank=True)
    authors_order = models.CharField(max_length=1000, blank=True, help_text="Comma-separated list of author IDs in display order")
    alphabetical_authors = models.BooleanField(default=False, help_text="Check if authors are listed alphabetically rather than by contribution order")
    year = models.IntegerField()
    reference_type = models.CharField(max_length=40, choices=REFERENCE_TYPES)
    journal = models.CharField(max_length=200, blank=True)
    volume = models.CharField(max_length=50, blank=True)
    pages = models.CharField(max_length=50, blank=True)
    doi = models.CharField(max_length=100, blank=True)
    url = models.URLField(blank=True)
    pdf_file = models.FileField(upload_to='references/', blank=True)
    reference_image = models.ImageField(upload_to='references/images/', blank=True, null=True, help_text="Optional image for the publication (e.g., graph, diagram)")
    abstract = models.TextField(blank=True)
    keywords = models.CharField(max_length=500, blank=True)
    code = models.URLField(blank=True)
    slides = models.FileField(upload_to='slides/', blank=True)
    
    class Meta:
        ordering = ['-year', 'title']

    def get_authors_display(self):
        """
        Returns HTML with the profile owner's name bolded
        """
        if self.alphabetical_authors:
            # Sort alphabetically by author name
            authors = self.authors.order_by('name')
        else:
            # Use the authors_order field to preserve the order set in admin
            if self.authors_order:
                author_ids = [int(id_str) for id_str in self.authors_order.split(',') if id_str.strip()]
                authors = []
                for author_id in author_ids:
                    try:
                        author = self.authors.get(id=author_id)
                        authors.append(author)
                    except Author.DoesNotExist:
                        continue
            else:
                # Fallback to natural order if no order is specified
                authors = self.authors.all()
        
        authors_html = []
        for author in authors:
            if author.is_profile_owner:
                authors_html.append(f"<strong>{author.name}</strong>")
            else:
                authors_html.append(author.name)
        
        return mark_safe(", ".join(authors_html))

    def get_authors_plain(self):
        """
        Returns plain text author list without HTML formatting
        """
        if self.alphabetical_authors:
            authors = self.authors.order_by('name')
        else:
            # Use the authors_order field to preserve the order set in admin
            if self.authors_order:
                author_ids = [int(id_str) for id_str in self.authors_order.split(',') if id_str.strip()]
                authors = []
                for author_id in author_ids:
                    try:
                        author = self.authors.get(id=author_id)
                        authors.append(author)
                    except Author.DoesNotExist:
                        continue
            else:
                # Fallback to natural order if no order is specified
                authors = self.authors.all()
        
        return ", ".join([author.name for author in authors])
    
    def get_short_title(self):
        """
        Returns the first 3 key words of the title excluding articles and prepositions
        """
        # Define a list of words to exclude
        exclude_words = ["the",
                         "a",
                         "an",
                         "and",
                         "or",
                         "on",
                         "of",
                         "in",
                         "to",
                         "with",
                         "as",
                         "by",
                         "for",
                         "from",
                         "into",
                         "onto",
                         "over",
                         "under",
                         "upon",
                         "with",
                         "towards"]
        
        # Split the title into words and filter out the excluded words
        words = [word for word in self.title.split(" ") if word.lower() not in exclude_words]
        
        return " ".join(words[:3])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Only populate authors_order if it's empty and not being saved from admin
        # The admin will handle the ordering through its save_model method
        if not self.authors_order and self.authors.exists() and not hasattr(self, '_from_admin'):
            self.authors_order = ','.join(str(author.id) for author in self.authors.all())
            # Save again to update the authors_order field
            super().save(update_fields=['authors_order'])

    def __str__(self):
        return f"{self.title} ({self.year})"
