from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("generate_cv/", views.generate_cv_pdf, name="generate_cv_pdf"),
    path('project/<slug:project_slug>/', views.project_view, name='project_view'),
    path('paper/<slug:paper_slug>/', views.paper_redirect, name='paper_redirect'),
    path('talk/<slug:talk_slug>/slides/', views.slide_redirect, name='slide_redirect'),
    path('talk/<slug:talk_slug>/poster/', views.poster_redirect, name='poster_redirect'),
]