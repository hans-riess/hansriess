from django.contrib import admin
from .models import Profile, Reference

class ReferenceAdmin(admin.ModelAdmin):
    list_display = ['get_short_title', 'year', 'reference_type']
    list_filter = ['reference_type', 'year']
    search_fields = ['title', 'authors']
    ordering = ['-year', 'title']
    
    fieldsets = [
        (None, {
            'fields': ['title', 'authors', 'year', 'reference_type']
        }),
        ('Publication Details', {
            'fields': ['journal', 'volume', 'pages', 'doi', 'url', 'pdf_file', 'reference_image'],
            'classes': ['collapse']
        }),
        ('Additional Information', {
            'fields': ['abstract', 'keywords'],
            'classes': ['collapse']
        })
    ]

class ProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'title', 'institution', 'email']
    search_fields = ['name', 'title', 'institution']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'title', 'bio']
        }),
        ('Contact Information', {
            'fields': ['email', 'office', 'website'],
            'classes': ['collapse']
        }),
        ('Academic Information', {
            'fields': ['department', 'school', 'institution', 'cv'],
            'classes': ['collapse']
        }),
        ('Social Media', {
            'fields': ['twitter', 'linkedin', 'github', 'google_scholar', 'orcid'],
            'classes': ['collapse']
        })
    ]

admin.site.register(Profile, ProfileAdmin)
admin.site.register(Reference, ReferenceAdmin)