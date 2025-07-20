from django.shortcuts import render
from django.http import HttpResponse
from .models import Profile, Reference

def home(request):
    # Load the most recent profile
    profile = Profile.objects.latest('created_at')
    journal_articles = Reference.objects.filter(reference_type='journal_article')
    conference_proceedings = Reference.objects.filter(reference_type='conference_proceedings')
    book_chapters = Reference.objects.filter(reference_type='book_chapter')
    books = Reference.objects.filter(reference_type='book')
    preprints = Reference.objects.filter(reference_type='preprint')
    theses = Reference.objects.filter(reference_type='thesis')
    other = Reference.objects.filter(reference_type='other')

    context = {
        'profile': profile, 
        'journal_articles': journal_articles,
        'conference_proceedings': conference_proceedings,
        'book_chapters': book_chapters,
        'books': books,
        'preprints': preprints,
        'theses': theses,
        'other': other,
    }

    return render(request, 'index.html', context)