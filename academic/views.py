from django.shortcuts import render, redirect
from academic.models import Profile, Reference, Talk, Grant, Course, Service, Education, Experience,Quote,Figure
from django.http import HttpResponse
from django.core.management import call_command
from django.conf import settings
import os


# Create your views here.
def index(request):
    profile = Profile.objects.first()
    journal_articles = Reference.objects.filter(reference_type='journal_article')
    conference_proceedings = Reference.objects.filter(reference_type='conference_proceedings')
    book_chapters = Reference.objects.filter(reference_type='book_chapter')
    books = Reference.objects.filter(reference_type='book')
    preprints = Reference.objects.filter(reference_type='preprint')
    theses = Reference.objects.filter(reference_type='thesis')
    other = Reference.objects.filter(reference_type='other')
    talks = Talk.objects.all()
    grants = Grant.objects.all()
    courses = Course.objects.all()
    service = Service.objects.all()
    education = Education.objects.all()
    experience = Experience.objects.all()
    quotes = Quote.objects.all()
    figures = Figure.objects.all()

    context = {
        'profile': profile,
        'journal_articles':journal_articles,
        'conference_proceedings':conference_proceedings,
        'book_chapters':book_chapters,
        'books':books,
        'preprints':preprints,
        'theses':theses,
        'other':other,
        'talks': talks,
        'grants': grants,
        'courses': courses,
        'service': service,
        'education': education,
        'experience': experience,
        'quotes':quotes,
        'figures':figures,
    }

    # The {% static %} template tag will now automatically handle S3 URLs in production
    return render(request, 'index.html', context)

def generate_cv_pdf(request):
    """
    Runs the command to generate and upload the CV, then redirects to the 
    file's public URL.
    """
    # Run the management command to generate the CV
    call_command('generate_cv')

    # Get the updated profile object
    profile = Profile.objects.first()

    # Redirect to the CV's URL, whether it's on S3 or local
    if profile and profile.cv:
        return redirect(profile.cv.url)
    else:
        # Fallback if the CV doesn't exist for some reason
        # You can customize this to redirect to the homepage with an error message
        return redirect('index') 
