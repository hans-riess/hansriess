from django.shortcuts import render, redirect, get_object_or_404
from academic.models import Profile, Reference, Talk, Grant, Course, Service, Education, Experience,Quote,Figure
from django.http import HttpResponse, Http404
from django.core.management import call_command
from django.conf import settings
import logging
import os

logger = logging.getLogger(__name__)

# Cache buster for the coordination sheaf demo's JavaScript and CSS.
#
# In production static files are served from S3 with CacheControl max-age=86400, and
# S3Boto3Storage does not hash filenames, so an edited asset would otherwise be shadowed by
# yesterday's copy in every browser that has already been here. Bump this in the same commit
# that touches static/js/sheaf-demo.js or static/css/sheaf-demo.css.
#
# Deliberately a constant rather than the files' mtime: on Heroku that is slug build time, so
# it would churn on every deploy and throw the cache away for no reason.
DEMO_ASSET_VERSION = "8"


def _demo_context():
    """Everything a template needs to reference the demo's static assets."""
    return {'demo_asset_version': DEMO_ASSET_VERSION}


# Create your views here.
def index(request):
    profile = Profile.objects.first()
    journal_articles = Reference.objects.filter(medium='journal_article')
    conference_proceedings = Reference.objects.filter(medium='conference_proceedings')
    book_chapters = Reference.objects.filter(medium='book_chapter')
    books = Reference.objects.filter(medium='book')
    preprints = Reference.objects.filter(medium='preprint')
    theses = Reference.objects.filter(medium='thesis')
    other = Reference.objects.filter(medium='other')
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
    context.update(_demo_context())

    # The {% static %} template tag will now automatically handle S3 URLs in production
    return render(request, 'index.html', context)


def demo_view(request):
    """
    The coordination sheaf demo on a page of its own.

    The landing page already opens it as an overlay at /#sheaf-demo, but a plain URL is worth
    having on its own: it is what goes in a paper, a talk or a grant report, and it is a far
    easier thing to point a browser at while working on the demo than the homepage is.

    Entirely client-side, and deliberately touches no models: the page needs nothing from the
    database, so it costs no query and still renders if the database is unreachable.
    """
    return render(request, 'demo.html', _demo_context())


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

def cv_redirect(request):
    """
    Redirects /cv/ to the profile's current CV, giving it a stable, shareable
    URL (hansriess.com/cv) independent of the underlying storage URL.

    The CV is rebuilt from the database on the way through, so the download is
    always current without anyone having to remember to regenerate it. A custom
    uploaded CV is served as-is and is never regenerated over.
    """
    profile = Profile.objects.first()
    if not profile:
        raise Http404("CV not found.")

    if not profile.use_custom_cv:
        try:
            call_command('generate_cv')
        except Exception:
            # A LaTeX or storage failure should not take the download with it;
            # fall through and serve whichever copy is already stored.
            logger.exception("CV regeneration failed; serving the stored copy")
        profile.refresh_from_db()

    cv_file = profile.cv_file()
    if not cv_file:
        raise Http404("CV not found.")

    # The stored file keeps the same name every time it is rebuilt, so its URL
    # is stable and both browsers and any CDN in front of storage will happily
    # serve a stale copy. Bust that with the file's own modification time, and
    # tell the client not to cache the redirect itself.
    response = redirect(_cache_busted_url(cv_file))
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    return response


def _cache_busted_url(cv_file):
    """The file's URL with a version stamp, so a rebuilt CV is not served stale."""
    url = cv_file.url
    try:
        stamp = int(cv_file.storage.get_modified_time(cv_file.name).timestamp())
    except Exception:
        # Not every storage backend reports modification times.
        logger.debug("Could not read the CV's modification time", exc_info=True)
        return url
    return f"{url}{'&' if '?' in url else '?'}v={stamp}"

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
