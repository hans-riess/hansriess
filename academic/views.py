from django.shortcuts import render
from django.http import HttpResponse
from .models import Profile, Reference, Course, Experience, Talk, Grant, Education, Service

def home(request):
    # Load the most recent profile
    profile = Profile.objects.latest('created_at')
    
    # Publications
    journal_articles = Reference.objects.filter(reference_type='journal_article')
    conference_proceedings = Reference.objects.filter(reference_type='conference_proceedings')
    book_chapters = Reference.objects.filter(reference_type='book_chapter')
    books = Reference.objects.filter(reference_type='book')
    preprints = Reference.objects.filter(reference_type='preprint')
    theses = Reference.objects.filter(reference_type='thesis')
    other = Reference.objects.filter(reference_type='other')
    
    # Teaching
    courses = Course.objects.all()
    
    # Experience
    experiences = Experience.objects.all()
    
    # Talks
    talks = Talk.objects.all()
    
    # Grants
    grants = Grant.objects.all()
    
    # Education
    education = Education.objects.all()
    
    # Service
    service = Service.objects.all()

    context = {
        'profile': profile, 
        'journal_articles': journal_articles,
        'conference_proceedings': conference_proceedings,
        'book_chapters': book_chapters,
        'books': books,
        'preprints': preprints,
        'theses': theses,
        'other': other,
        'courses': courses,
        'experiences': experiences,
        'talks': talks,
        'grants': grants,
        'education': education,
        'service': service,
    }

    return render(request, 'index.html', context)

def generate_html_cv(request):
    """Generate an HTML CV that matches the academic-cv.sty styling"""
    # Load the most recent profile
    profile = Profile.objects.latest('created_at')
    
    # Publications
    journal_articles = Reference.objects.filter(reference_type='journal_article')
    conference_proceedings = Reference.objects.filter(reference_type='conference_proceedings')
    book_chapters = Reference.objects.filter(reference_type='book_chapter')
    books = Reference.objects.filter(reference_type='book')
    preprints = Reference.objects.filter(reference_type='preprint')
    theses = Reference.objects.filter(reference_type='thesis')
    other = Reference.objects.filter(reference_type='other')
    
    # Teaching
    courses = Course.objects.all()
    
    # Experience
    experiences = Experience.objects.all()
    
    # Talks
    talks = Talk.objects.all()
    
    # Grants
    grants = Grant.objects.all()
    
    # Education
    education = Education.objects.all()
    
    # Service
    service = Service.objects.all()

    context = {
        'profile': profile, 
        'journal_articles': journal_articles,
        'conference_proceedings': conference_proceedings,
        'book_chapters': book_chapters,
        'books': books,
        'preprints': preprints,
        'theses': theses,
        'other': other,
        'courses': courses,
        'experiences': experiences,
        'talks': talks,
        'grants': grants,
        'education': education,
        'service': service,
    }

    return render(request, 'cv.html', context)