from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("generate_cv/", views.generate_cv_pdf, name="generate_cv_pdf"),
    path('project/<slug:project_slug>/', views.project_view, name='project_view'),
]