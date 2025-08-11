from django.contrib import admin
from .models import Profile, Reference, Course, Experience, Talk, Grant, Education, Service

class ReferenceAdmin(admin.ModelAdmin):
    list_display = ['get_short_title', 'year', 'reference_type']
    list_filter = ['reference_type', 'year']
    search_fields = ['title', 'authors']
    ordering = ['-year', 'title']
    
    fieldsets = [
        (None, {
            'fields': ['reference_type', 'title', 'authors', 'abstract','keywords','code','alphabetical_order', 'shared_first_author', 'year']
        }),
        ('Publication Details', {
            'fields': ['journal', 'volume', 'issue', 'pages', 'url','doi', 'pdf_file', 'reference_image'],
            'classes': ['collapse']
        }),
    ]

class CourseAdmin(admin.ModelAdmin):
    list_display = ['course_code', 'title', 'institution', 'semester', 'year', 'role']
    list_filter = ['semester', 'year', 'role', 'is_graduate', 'is_online']
    search_fields = ['course_code', 'title', 'institution']
    ordering = ['-year', '-semester', 'course_code']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['course_code', 'title', 'institution', 'department', 'semester', 'year', 'role']
        }),
        ('Course Details', {
            'fields': ['description', 'is_graduate', 'is_online', 'syllabus'],
            'classes': ['collapse']
        })
    ]

class ExperienceAdmin(admin.ModelAdmin):
    list_display = ['title', 'institution', 'job_type', 'academic_position_type', 'start_date', 'is_current']
    list_filter = ['job_type', 'academic_position_type', 'full_time', 'tenure_track', 'is_current']
    search_fields = ['title', 'institution', 'department']
    ordering = ['-start_date', 'title']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['title', 'institution', 'department', 'location', 'job_type', 'academic_position_type']
        }),
        ('Position Details', {
            'fields': ['full_time', 'tenure_track', 'start_date', 'end_date', 'is_current', 'supervisor']
        }),
        ('Description', {
            'fields': ['description'],
            'classes': ['collapse']
        })
    ]

class TalkAdmin(admin.ModelAdmin):
    list_display = ['get_short_title', 'talk_type', 'date']
    list_filter = ['talk_type', 'is_invited', 'date']
    search_fields = ['title', 'venue', 'location']
    ordering = ['-date', 'title']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['title', 'abstract', 'venue', 'location', 'talk_type', 'is_invited', 'date']
        }),
        ('Materials', {
            'fields': ['slides', 'event_url'],
            'classes': ['collapse']
        }),
        ('Related Publications', {
            'fields': ['related_publications'],
            'classes': ['collapse']
        })
    ]

class GrantAdmin(admin.ModelAdmin):
    list_display = ['title', 'funding_agency', 'role', 'get_formatted_amount']
    list_filter = ['role']
    search_fields = ['title', 'funding_agency', 'co_pis']
    ordering = ['title']
    
    fieldsets = [
        ('Basic Information', {
            # Replaced start_date and end_date with year
            'fields': ['title', 'funding_agency', 'role', 'start_date','end_date']
        }),
        ('Funding Details', {
            'fields': ['amount', 'currency', 'co_pis', 'grant_number'],
            'classes': ['collapse']
        }),
        ('Related Publications', {
            'fields': ['related_publications'],
            'classes': ['collapse']
        })
    ]

class EducationAdmin(admin.ModelAdmin):
    list_display = ['degree_type', 'field_of_study', 'institution', 'graduation_year', 'gpa']
    search_fields = ['field_of_study', 'institution', 'location']
    ordering = ['-graduation_year', 'degree_type']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['degree_type', 'degree_type_short', 'field_of_study', 'institution', 'location', 'graduation_year']
        }),
        ('Academic Details', {
            'fields': ['gpa', 'thesis_title', 'advisor', 'honors'],
            'classes': ['collapse']
        }),
        ('Related Publications', {
            'fields': ['related_publications'],
            'classes': ['collapse']
        })
    ]

class ServiceAdmin(admin.ModelAdmin):
    list_display = ['role', 'organization', 'service_type', 'year']
    list_filter = ['role', 'service_type', 'year']
    search_fields = ['organization', 'location']
    ordering = ['-year', 'title']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['title', 'role', 'organization', 'service_type', 'start_date','end_date','year','end_year', 'location']
        })
    ]

class ProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'title', 'institution', 'email']
    search_fields = ['name', 'title', 'institution']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'occupation', 'title','long_title', 'bio', 'short_bio', 'quote', 'quote_author', 'under_construction']
        }),
        ('Contact Information', {
            'fields': ['email', 'room_number', 'building', 'street', 'city', 'state', 'zip_code', 'country', 'website','phone'],
            'classes': ['collapse']
        }),
        ('Academic Information', {
            'fields': ['department', 'sub_department', 'school', 'institution', 'long_institution', 'cv','cv_button'],
            'classes': ['collapse']
        }),
        ('Social Media', {
            'fields': ['twitter','blue_sky','youtube','linkedin', 'github', 'google_scholar', 'orcid'],
            'classes': ['collapse']
        })
    ]

admin.site.register(Profile, ProfileAdmin)
admin.site.register(Reference, ReferenceAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Experience, ExperienceAdmin)
admin.site.register(Talk, TalkAdmin)
admin.site.register(Grant, GrantAdmin)
admin.site.register(Education, EducationAdmin)
admin.site.register(Service, ServiceAdmin)
