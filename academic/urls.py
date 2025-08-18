from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("",views.generate_cv_pdf, name="generate_cv_pdf")    
]