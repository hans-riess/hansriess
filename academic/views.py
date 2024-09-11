from django.shortcuts import render
from django.http import HttpResponse
from .models import ConferenceProceedings, JournalArticle

def home(request):
    return render(request, 'index.html')