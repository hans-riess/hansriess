from django.db import models
from django.db import models

class Author(models.Model):
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True,null=True)
    affiliation = models.CharField(blank=True,null=True,max_length=200)
    photo = models.URLField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.first_name + " " + self.last_name

class Project(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    photo = models.CharField()

    def __str__(self):
        return self.title