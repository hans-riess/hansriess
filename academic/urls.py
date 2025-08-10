from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("cv/", views.generate_html_cv, name="generate_html_cv"),
]