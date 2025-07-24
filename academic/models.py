from django.db import models


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
    orcid = models.URLField(blank=True, null=True)
    department = models.CharField(max_length=200, blank=True, null=True)
    school = models.CharField(max_length=200, blank=True, null=True)
    institution = models.CharField(max_length=200, blank=True, null=True)
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
    keywords = models.CharField(max_length=500, blank=True, help_text="Comma-separated list of keywords")
    code = models.URLField(blank=True, help_text="Link to the code repository")
    slides = models.FileField(upload_to='slides/', blank=True, help_text="Optional slides for the publication")
    
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
