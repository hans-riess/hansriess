from django.contrib import admin
from django import forms
from django.utils.safestring import mark_safe
from .models import Profile, Reference, Author

class ReferenceAdminForm(forms.ModelForm):
    class Meta:
        model = Reference
        fields = '__all__'
        widgets = {
            'authors_order': forms.HiddenInput(attrs={
                'id': 'id_authors_order'
            })
        }

class ReferenceAdmin(admin.ModelAdmin):
    form = ReferenceAdminForm
    list_display = ['get_short_title', 'year', 'reference_type', 'alphabetical_authors']
    list_filter = ['reference_type', 'year', 'alphabetical_authors']
    search_fields = ['title', 'authors__name']
    ordering = ['-year', 'title']
    filter_horizontal = ['authors']
    
    fieldsets = [
        (None, {
            'fields': ['title', 'year', 'reference_type']
        }),
        ('Authors', {
            'fields': ['authors', 'alphabetical_authors'],
            'description': mark_safe(
                'Select authors in the order they should appear (unless alphabetical is checked). '
                'The author order will be automatically saved based on your selection order. '
                '<br><strong>Note:</strong> Author order will only be preserved if "alphabetical_authors" is unchecked.'
            )
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
    
    class Media:
        js = ('admin/js/reference_admin.js',)
    
    def save_model(self, request, obj, form, change):
        # Mark that this is being saved from admin
        obj._from_admin = True
        
        # Always update authors_order based on the form data
        if 'authors_order' in form.cleaned_data and form.cleaned_data['authors_order']:
            # Use the authors_order from the form (updated by JavaScript)
            obj.authors_order = form.cleaned_data['authors_order']
        elif 'authors' in form.cleaned_data:
            # Fallback: if no authors_order, use the selected authors
            selected_authors = form.cleaned_data['authors']
            if selected_authors:
                obj.authors_order = ','.join(str(author.id) for author in selected_authors)
        super().save_model(request, obj, form, change)
    
    def get_authors_plain(self, obj):
        return obj.get_authors_plain()
    get_authors_plain.short_description = 'Authors'

class AuthorAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_profile_owner', 'affiliation', 'email']
    list_filter = ['is_profile_owner']
    search_fields = ['name', 'affiliation']
    ordering = ['name']  # Keep alphabetical ordering in admin interface
    
    fieldsets = [
        (None, {
            'fields': ['name', 'is_profile_owner']
        }),
        ('Contact Information', {
            'fields': ['affiliation', 'email', 'website'],
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
            'fields': ['email', 'office', 'phone', 'website'],
            'classes': ['collapse']
        }),
        ('Academic Information', {
            'fields': ['department', 'school', 'institution', 'address', 'cv'],
            'classes': ['collapse']
        }),
        ('Social Media', {
            'fields': ['twitter', 'linkedin', 'github', 'google_scholar'],
            'classes': ['collapse']
        })
    ]

admin.site.register(Profile, ProfileAdmin)
admin.site.register(Reference, ReferenceAdmin)
admin.site.register(Author, AuthorAdmin)