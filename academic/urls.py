from django.urls import path

from . import api, views

urlpatterns = [
    path("", views.index, name="index"),
    path("cv/", views.cv_redirect, name="cv_redirect"),
    path("cv/tex/", views.cv_tex, name="cv_tex"),
    path("demo/", views.demo_view, name="demo"),
    path("demo/<slug:demo_slug>/", views.demo_view, name="demo_slug"),
    path("generate_cv/", views.generate_cv_pdf, name="generate_cv_pdf"),
    path("sitedata/data.json", views.site_data, name="site_data"),
    path('project/<slug:project_slug>/', views.project_view, name='project_view'),
    path('paper/<slug:paper_slug>/', views.paper_redirect, name='paper_redirect'),
    path('talk/<slug:talk_slug>/slides/', views.slide_redirect, name='slide_redirect'),
    path('talk/<slug:talk_slug>/poster/', views.poster_redirect, name='poster_redirect'),
    # Token-protected JSON API for correcting CV entries; see academic/api.py.
    path("api/cv/", api.index, name="cv_api_index"),
    path("api/cv/lookup/<str:tag>/", api.lookup, name="cv_api_lookup"),
    path("api/cv/<str:model_name>/", api.collection, name="cv_api_collection"),
    path("api/cv/<str:model_name>/<int:pk>/", api.item, name="cv_api_item"),
]
