from django.contrib import admin
from .models import Profile, Reference

class ReferenceAdmin(admin.ModelAdmin):
    list_display = ['get_short_title', 'year', 'reference_type']
    list_filter = ['reference_type', 'year']
    search_fields = ['title', 'authors']
    ordering = ['-year', 'title']
    
    fieldsets = [
        (None, {
            'fields': ['title', 'long_title', 'authors', 'alphabetical_order', 'shared_first_author', 'year', 'reference_type']
        }),
        ('Publication Details', {
            'fields': ['journal', 'volume', 'issue', 'pages', 'doi', 'url', 'pdf_file', 'reference_image'],
            'classes': ['collapse']
        }),
        ('Additional Information', {
            'fields': ['abstract', 'keywords', 'code', 'slides'],
            'classes': ['collapse']
        })
    ]

class ProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'title', 'institution', 'email']
    search_fields = ['name', 'title', 'institution']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'occupation', 'title','long_title', 'bio']
        }),
        ('Contact Information', {
            'fields': ['email', 'room_number', 'building', 'street', 'city', 'state', 'zip_code', 'country', 'website','phone'],
            'classes': ['collapse']
        }),
        ('Academic Information', {
            'fields': ['department', 'sub_department', 'school', 'institution', 'long_institution', 'cv'],
            'classes': ['collapse']
        }),
        ('Social Media', {
            'fields': ['twitter','blue_sky','youtube','linkedin', 'github', 'google_scholar', 'orcid'],
            'classes': ['collapse']
        })
    ]

admin.site.register(Profile, ProfileAdmin)
admin.site.register(Reference, ReferenceAdmin)