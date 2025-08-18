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
    # This command now generates the .tex file, compiles it, and uploads it to S3
    call_command('generate_cv')

    # Redirect the user directly to the known S3 URL for the CV
    bucket_name = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    if bucket_name:
        s3_url = f"https://{bucket_name}.s3.amazonaws.com/cv.pdf"
        return redirect(s3_url)
    else:
        # Fallback for local development if S3 is not configured
        # This will likely result in a 404 unless you have a cv.pdf in your local static files
        return redirect('/static/files/cv.pdf')
