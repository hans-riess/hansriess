from django.db import models
from django.db import models

class Author(models.Model):
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    email = models.EmailField()
    affiliation = models.CharField(max_length=200)
    photo = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.first_name + " " + self.last_name

class ConferenceProceedings(models.Model):
    title = models.CharField(max_length=200)
    authors = models.ManyToManyField(Author)
    conference_name = models.CharField(max_length=200)
    conference_location = models.CharField(max_length=200)
    conference_date = models.DateField()
    abstract = models.TextField()
    slides = models.URLField(blank=True, null=True)
    paper = models.URLField(blank=True, null=True)
    code = models.URLField(blank=True, null=True)
    poster = models.URLField(blank=True,null=True)
    doi = models.URLField(blank=True,null=True)

    def __str__(self):
        return self.title
    
class Preprint(models.Model):
    title = models.CharField(max_length=200)
    authors = models.ManyToManyField(Author)
    publication_date = models.DateField()
    abstract = models.TextField()
    slides = models.URLField(blank=True, null=True)
    paper = models.URLField(blank=True, null=True)
    code = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.title

class JournalArticle(models.Model):
    title = models.CharField(max_length=200)
    authors = models.ManyToManyField(Author)
    journal_name = models.CharField(max_length=200)
    volume = models.IntegerField(blank=True, null=True)
    issue = models.IntegerField(blank=True, null=True)
    publication_date = models.DateField()
    abstract = models.TextField()
    slides = models.URLField(blank=True, null=True)
    paper = models.URLField(blank=True, null=True)
    code = models.URLField(blank=True, null=True)
    doi = models.URLField(blank=True,null=True)

    def __str__(self):
        return self.title

class Thesis(models.Model):
    title = models.CharField(max_length=200)
    authors = models.ManyToManyField(Author)
    school = models.CharField(max_length=200)
    department = models.CharField(max_length=200)
    date = models.DateField()
    thesis = models.URLField(blank=True,null=True)
    abstract = models.TextField()
    doi = models.URLField(blank=True,null=True)

    def __str__(self):
        return self.title

class Project(models.Model):
    title = models.CharField(max_length=200)
    conference_papers = models.ManyToManyField(ConferenceProceedings)
    journal_papers = models.ManyToManyField(JournalArticle)
    description = models.TextField()
    photo = models.URLField()

    def __str__(self):
        return self.title
