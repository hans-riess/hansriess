from django.shortcuts import render
from django.http import HttpResponse
from .models import ConferenceProceedings, JournalArticle

def index(request):
    return render(request, 'my_papers/index.html')