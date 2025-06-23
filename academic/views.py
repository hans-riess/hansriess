from django.shortcuts import render
from django.http import HttpResponse

from .models import Project, Profile

def home(request):
    projects = Project.objects.all()
    profile = Profile.objects.first()  # Assuming only one profile
    return render(request, 'index.html', {'projects': projects, 'profile': profile})
