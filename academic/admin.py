from django.contrib import admin
from .models import (Award, Profile, Reference, Course, DeliveredProduct, Experience,
                     Innovation, Talk, Grant, Education, Service, Quote, Figure,
                     Student, ReferencePerson, Milestone)

class ReferenceAdmin(admin.ModelAdmin):
    list_display = ['get_short_title', 'year', 'reference_type']
    list_filter = ['reference_type', 'year']
    search_fields = ['title', 'authors']
    ordering = ['-year', 'title']
    
    # ADD THIS: Automatically fills the slug based on the title
    prepopulated_fields = {'slug': ('title',)} 

    fieldsets = [
        (None, {
            # ADD 'slug' HERE:
            'fields': ['reference_type', 'title', 'slug', 'authors', 'alphabetical_order', 'shared_first_author']
        }),
        ('Publication Details', {
            'fields': ['year','journal', 'volume', 'issue', 'pages','abstract','keywords'],
            'classes': ['collapse']
        }),
        ('Materials', {
            'fields': ['url','code','pdf_file', 'reference_image'],
            'classes': ['collapse']
        }),
        ('Georgia Tech CV', {
            'fields': ['gt_category', 'credit_roles', 'status_note', 'arxiv_id',
                       'pre_gt_hire', 'cv_ref_slug'],
            'classes': ['collapse']
        })
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
        }),
        ('Georgia Tech CV (Knowledge Sharing table)', {
            'fields': ['organization', 'when_taught', 'curriculum_role',
                       'attendee_count', 'pre_gt_hire'],
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
            # 'talk' has been removed from this list
            'fields': ['slides', 'poster', 'event_url'], # Added poster back
            'classes': ['collapse']
        }),
        ('Related Publications', {
            'fields': ['related_publications'],
            'classes': ['collapse']
        }),
        ('Georgia Tech CV', {
            'fields': ['gt_category', 'credit_roles', 'note', 'pre_gt_hire', 'cv_ref_slug'],
            'classes': ['collapse']
        })
    ]

class MilestoneInline(admin.StackedInline):
    model = Milestone
    extra = 0
    fields = ['title', 'slug', 'date', 'report_type', 'page_count', 'slide_count',
              'authorship_percent', 'description', 'report', 'slides', 'cv_ref_slug']
    prepopulated_fields = {'slug': ('title',)}

class GrantAdmin(admin.ModelAdmin):
    list_display = ['title', 'funding_agency', 'role', 'gt_status', 'get_formatted_amount']
    list_filter = ['role', 'gt_status']
    inlines = [MilestoneInline]
    search_fields = ['title', 'funding_agency', 'co_pis']
    ordering = ['title']

    fieldsets = [
        ('Basic Information', {
            # Replaced start_date and end_date with year
            'fields': ['title', 'short_title', 'description','slug', 'image', 'funding_agency', 'role', 'start_date','end_date']
        }),
        ('Password Protection', {
            'fields': ['password_protected', 'password'],
            'classes': ['collapse']
        }),
        ('Funding Details', {
            'fields': ['amount', 'currency', 'co_pis', 'grant_number', 'program_manager', 'sponsor_logo'],
            'classes': ['collapse']
        }),
        ('Related Publications', {
            'fields': ['related_publications'],
            'classes': ['collapse']
        }),
        ('Georgia Tech CV — Section III.A (funded programs)', {
            'fields': ['gt_status', 'pi_name', 'candidate_role_text', 'task_title',
                       'contributions', 'report_series_note', 'cv_ref_slug'],
            'classes': ['collapse']
        }),
        ('Georgia Tech CV — Section IV.B (proposals)', {
            'fields': ['solicitation', 'date_abstract_submitted', 'date_full_submitted',
                       'full_proposal_note', 'amount_requested', 'result_note',
                       'contribution_to_proposal'],
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
        }),
        ('Georgia Tech CV', {
            'fields': ['is_dissertation', 'thesis_url', 'pre_gt_hire'],
            'classes': ['collapse']
        })
    ]

class ServiceAdmin(admin.ModelAdmin):
    list_display = ['role', 'organization', 'service_type', 'gt_category', 'year']
    list_filter = ['role', 'service_type', 'gt_category', 'year']
    search_fields = ['organization', 'location']
    ordering = ['-year', 'title']

    fieldsets = [
        ('Basic Information', {
            'fields': ['title', 'role', 'organization', 'service_type', 'start_date','end_date','year','end_year', 'location']
        }),
        ('Georgia Tech CV', {
            'fields': ['gt_category', 'manuscript_count', 'detail', 'pre_gt_hire'],
            'classes': ['collapse']
        })
    ]

class ProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'title', 'institution', 'email']
    search_fields = ['name', 'title', 'institution']

    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'occupation', 'title','long_title','headshot', 'bio', 'short_bio', 'under_construction', 'show_publications']
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
        }),
        ('Georgia Tech CV', {
            'fields': ['fields_of_interest', 'gt_hire_date', 'research_program',
                       'cv_show_preamble_sections'],
            'classes': ['collapse']
        })
    ]

class QuoteAdmin(admin.ModelAdmin):
    list_display = ['author']
    fieldsets = [
        ('Basic Information', {
            'fields': ['author','quote' ]
        })
    ]

class FigureAdmin(admin.ModelAdmin):
    list_display = ['name']
    fieldsets = [
        (None, {
            'fields': ['name','image','caption']
        })
    ]

class StudentAdmin(admin.ModelAdmin):
    list_display = ['name', 'level', 'degree', 'mentorship_role', 'institution', 'start_date', 'end_date'] # Added degree, mentorship_role
    list_filter = ['level', 'mentorship_role', 'institution', 'start_date'] # Added mentorship_role
    search_fields = ['name', 'institution', 'project_title', 'degree'] # Added degree
    ordering = ['-start_date', 'name']
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'level', 'degree', 'institution'] # Added degree
        }),
        ('Mentorship Details', {
            'fields': ['mentorship_role', 'project_title', 'start_date', 'end_date', 'current_position'], # Added mentorship_role
            'classes': ['collapse']
        }),
        ('Georgia Tech CV', {
            'fields': ['research_topic', 'appointment_note', 'advisor_of_record',
                       'host_lab', 'resulting_publications', 'pre_gt_hire'],
            'classes': ['collapse']
        })
    ]

class ReferencePersonAdmin(admin.ModelAdmin):
    list_display = ['name', 'title', 'institution', 'email']
    search_fields = ['name', 'title', 'institution', 'relationship']
    ordering = ['name']
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'title', 'institution', 'relationship']
        }),
        ('Contact Details', {
            'fields': ['email'],
            'classes': ['collapse']
        })
    ]

class AwardAdmin(admin.ModelAdmin):
    """Section I.D of the Georgia Tech CV."""
    list_display = ['title', 'organization', 'year', 'order']
    search_fields = ['title', 'organization']
    ordering = ['order', '-year', 'title']
    prepopulated_fields = {'cv_ref_slug': ('title',)}
    fieldsets = [
        ('Basic Information', {
            'fields': ['title', 'organization', 'year', 'date_range', 'detail']
        }),
        ('CV Placement', {
            'fields': ['pre_gt_hire', 'cv_ref_slug', 'order']
        })
    ]

class DeliveredProductAdmin(admin.ModelAdmin):
    """Section I.C of the Georgia Tech CV."""
    list_display = ['name', 'sponsor', 'order']
    search_fields = ['name', 'summary', 'sponsor']
    ordering = ['order', 'name']
    prepopulated_fields = {'cv_ref_slug': ('name',)}
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'summary', 'sponsor', 'date_range']
        }),
        ('Product Details', {
            'fields': ['description', 'maturity', 'technical_contribution']
        }),
        ('CV Placement', {
            'fields': ['cv_ref_slug', 'order']
        })
    ]

class InnovationAdmin(admin.ModelAdmin):
    """Section II.B of the Georgia Tech CV."""
    list_display = ['title', 'sponsors_projects_dates', 'order']
    search_fields = ['title', 'sponsors_projects_dates']
    ordering = ['order', 'title']
    prepopulated_fields = {'cv_ref_slug': ('title',)}
    fieldsets = [
        ('Basic Information', {
            'fields': ['title', 'sponsors_projects_dates']
        }),
        ('Details', {
            'fields': ['description', 'technical_contributions']
        }),
        ('CV Placement', {
            'fields': ['cv_ref_slug', 'order']
        })
    ]

admin.site.register(Award, AwardAdmin)
admin.site.register(DeliveredProduct, DeliveredProductAdmin)
admin.site.register(Innovation, InnovationAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Reference, ReferenceAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Experience, ExperienceAdmin)
admin.site.register(Talk, TalkAdmin)
admin.site.register(Grant, GrantAdmin)
admin.site.register(Education, EducationAdmin)
admin.site.register(Service, ServiceAdmin)
admin.site.register(Quote, QuoteAdmin)
admin.site.register(Figure,FigureAdmin)
admin.site.register(Student, StudentAdmin) # Updated registration
admin.site.register(ReferencePerson, ReferencePersonAdmin)

class MilestoneAdmin(admin.ModelAdmin):
    list_display = ('title', 'grant', 'date')
    list_filter = ('grant', 'date')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}

admin.site.register(Milestone, MilestoneAdmin)