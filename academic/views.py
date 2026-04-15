from django.shortcuts import render, redirect, get_object_or_404
from academic.models import Profile, Reference, Talk, Grant, Course, Service, Education, Experience,Quote,Figure
from django.http import HttpResponse, Http404
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
    Runs the command to generate and upload the CV, but does not redirect to
    the file's public URL to avoid serving potentially cached content.
    """
    # Run the management command to generate the CV
    call_command('generate_cv')
    
    # Intentionally return no content to avoid redirecting to potentially
    # stale cached files on S3.
    return HttpResponse(status=204)

def project_view(request, project_slug):
    grant = get_object_or_404(Grant, slug=project_slug)
    
    password_required = grant.password_protected and not request.session.get(f'grant_{grant.slug}_unlocked')
    error = None

    if password_required and request.method == 'POST':
        password = request.POST.get('password')
        if password == grant.password:
            request.session[f'grant_{grant.slug}_unlocked'] = True
            password_required = False
        else:
            error = 'Incorrect password'

    related_publications = grant.related_publications.all()
    # Assuming talks related to the grant will have the grant's title or part of it in their title
    related_talks = Talk.objects.filter(title__icontains=grant.title)
    milestones = grant.milestones.all()
    
    context = {
        'grant': grant,
        'related_publications': related_publications,
        'related_talks': related_talks,
        'milestones': milestones,
        'profile': Profile.objects.first(),
        'password_required': password_required,
        'error': error,
    }
    
    return render(request, 'project.html', context)

def paper_redirect(request, paper_slug):
    reference = get_object_or_404(Reference, slug=paper_slug)
    
    if reference.pdf_file:
        # This redirects the user directly to the S3 URL
        return redirect(reference.pdf_file.url)
    elif reference.url:
        # This redirects the user to the provided url link
        return redirect(reference.url)
        
    raise Http404("PDF not found for this reference.")

def slide_redirect(request, talk_slug):
    talk = get_object_or_404(Talk, slug=talk_slug)
    
    if talk.slides:
        return redirect(talk.slides.url)
    raise Http404("Slides not found for this talk.")

def poster_redirect(request, talk_slug):
    talk = get_object_or_404(Talk, slug=talk_slug)
    
    if talk.poster:
        return redirect(talk.poster.url)
    raise Http404("Poster not found for this talk.")
