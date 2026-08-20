from django.contrib import admin
from .models import (Award, Profile, Proposal, Reference, Course, DeliveredProduct,
                     Experience, Innovation, Talk, Grant, Education, Service, Quote,
                     Figure, Student, ReferencePerson, Milestone, Review, TechReport)

class ReferenceAdmin(admin.ModelAdmin):
    list_display = ['get_short_title', 'year', 'medium', 'status', 'refereed']
    list_filter = ['medium', 'status', 'refereed', 'year']
    search_fields = ['title', 'authors']
    ordering = ['-year', 'title']

    prepopulated_fields = {'slug': ('title',), 'cv_ref_slug': ('title',)}

    fieldsets = [
        (None, {
            'fields': ['title', 'slug', 'authors', 'alphabetical_order',
                       'shared_first_author', 'credit_roles']
        }),
        ('Publication Details', {
            'fields': ['medium', 'status', 'refereed', 'year', 'publication_date',
                       'journal', 'volume', 'issue', 'pages',
                       'abstract', 'keywords']
        }),
        ('Materials', {
            'fields': ['url', 'code', 'doi', 'arxiv_id', 'pdf_file', 'reference_image',
                       'cv_ref_slug']
        })
    ]

class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'course_format', 'course_code', 'institution', 'semester', 'year', 'role']
    list_filter = ['course_format', 'semester', 'year', 'role', 'is_graduate', 'is_online']
    search_fields = ['course_code', 'title', 'institution']
    ordering = ['-year', '-semester', 'course_code']

    fieldsets = [
        ('Basic Information', {
            'fields': ['course_format', 'course_code', 'title', 'institution',
                       'department', 'semester', 'year', 'role']
        }),
        ('Course Details', {
            'fields': ['description', 'is_graduate', 'is_online', 'syllabus',
                       'organization', 'when_taught', 'curriculum_role',
                       'attendee_count']
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
    list_display = ['get_short_title', 'talk_type', 'invited', 'proceedings', 'date']
    list_filter = ['talk_type', 'invited', 'proceedings', 'date']
    search_fields = ['title', 'venue', 'location']
    ordering = ['-date', 'title']

    prepopulated_fields = {'slug': ('title',), 'cv_ref_slug': ('title',)}

    fieldsets = [
        ('Basic Information', {
            'fields': ['title', 'slug', 'abstract', 'venue', 'location', 'date',
                       'talk_type', 'invited', 'proceedings', 'reference',
                       'note', 'credit_roles', 'cv_ref_slug']
        }),
        ('Knowledge Sharing', {
            'description': 'Used when the talk is a tutorial, which the CV lists in '
                           'Section I.E rather than with the publications.',
            'fields': ['curriculum_role', 'attendee_count']
        }),
        ('Materials', {
            'fields': ['slides', 'poster', 'event_url', 'related_publications']
        })
    ]

class MilestoneInline(admin.StackedInline):
    model = Milestone
    extra = 0
    fields = ['title', 'slug', 'date', 'description', 'report', 'slides']
    prepopulated_fields = {'slug': ('title',)}

class TechReportInline(admin.StackedInline):
    model = TechReport
    extra = 0
    fields = ['title', 'slug', 'report_type', 'date', 'page_count', 'slide_count',
              'authorship_percent', 'description', 'report', 'slides', 'cv_ref_slug', 'order']
    prepopulated_fields = {'slug': ('title',), 'cv_ref_slug': ('title',)}

class GrantAdmin(admin.ModelAdmin):
    list_display = ['title', 'funding_agency', 'role', 'get_formatted_amount']
    list_filter = ['role']
    inlines = [TechReportInline, MilestoneInline]
    search_fields = ['title', 'funding_agency', 'co_pis']
    ordering = ['title']

    fieldsets = [
        ('Basic Information', {
            'fields': ['title', 'short_title', 'description', 'slug', 'image',
                       'funding_agency', 'role', 'candidate_role_text', 'task_title',
                       'pi_name', 'start_date', 'end_date']
        }),
        ('Funding Details', {
            'fields': ['amount', 'currency', 'co_pis', 'grant_number', 'program_manager',
                       'sponsor_logo', 'contributions', 'report_series_note', 'cv_ref_slug']
        }),
        ('Password Protection', {
            'fields': ['password_protected', 'password'],
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
            'fields': ['gpa', 'honors']
        }),
        ('Thesis', {
            'fields': ['thesis_title', 'thesis_url', 'advisor', 'is_dissertation',
                       'related_publications']
        })
    ]

class ServiceAdmin(admin.ModelAdmin):
    list_display = ['role', 'organization', 'service_type', 'category', 'year']
    list_filter = ['role', 'service_type', 'category', 'year']
    search_fields = ['organization', 'location']
    ordering = ['-year', 'title']

    fieldsets = [
        ('Basic Information', {
            'fields': ['title', 'role', 'organization', 'service_type', 'start_date','end_date','year','end_year', 'location']
        }),
        ('Details', {
            'fields': ['category', 'detail']
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
            'fields': ['department', 'sub_department', 'school', 'institution',
                       'long_institution', 'cv', 'custom_cv', 'use_custom_cv', 'cv_button'],
            'classes': ['collapse']
        }),
        ('Social Media', {
            'fields': ['twitter','blue_sky','mastodon','youtube','linkedin', 'github', 'google_scholar', 'orcid'],
            'classes': ['collapse']
        }),
        ('Curriculum Vitae', {
            'fields': ['fields_of_interest', 'research_program',
                       'cv_show_all_references', 'cv_show_preamble_sections']
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
        ('Research', {
            'fields': ['research_topic', 'appointment_note', 'advisor_of_record',
                       'host_lab', 'resulting_publications']
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
    """Section I.D of the CV."""
    list_display = ['title', 'organization', 'year', 'order']
    search_fields = ['title', 'organization']
    ordering = ['order', '-year', 'title']
    prepopulated_fields = {'cv_ref_slug': ('title',)}
    fieldsets = [
        ('Basic Information', {
            'fields': ['title', 'organization', 'year', 'date_range', 'detail']
        }),
        ('Placement', {
            'fields': ['cv_ref_slug', 'order']
        })
    ]

class DeliveredProductAdmin(admin.ModelAdmin):
    """Section I.C of the CV."""
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
        ('Placement', {
            'fields': ['cv_ref_slug', 'order']
        })
    ]

class InnovationAdmin(admin.ModelAdmin):
    """Section II.B of the CV."""
    list_display = ['title', 'sponsors_projects_dates', 'order']
    search_fields = ['title', 'sponsors_projects_dates']
    ordering = ['order', 'title']
    prepopulated_fields = {'cv_ref_slug': ('title',)}
    fieldsets = [
        ('Basic Information', {
            'fields': ['title', 'grants', 'sponsors_projects_dates']
        }),
        ('Details', {
            'fields': ['description', 'technical_contributions']
        }),
        ('Placement', {
            'fields': ['cv_ref_slug', 'order']
        })
    ]

class ProposalAdmin(admin.ModelAdmin):
    """Section IV.B of the CV."""
    list_display = ['title', 'sponsor', 'result', 'amount_requested', 'date_abstract_submitted']
    list_filter = ['result', 'sponsor']
    search_fields = ['title', 'sponsor', 'solicitation']
    ordering = ['order', '-date_abstract_submitted', 'title']
    prepopulated_fields = {'slug': ('title',), 'cv_ref_slug': ('short_title',)}
    fieldsets = [
        ('Basic Information', {
            'fields': ['title', 'short_title', 'slug', 'sponsor', 'solicitation',
                       'pi_name', 'candidate_role', 'grant']
        }),
        ('Submission', {
            'fields': ['date_abstract_submitted', 'date_full_submitted',
                       'full_proposal_note', 'amount_requested', 'currency',
                       'result', 'result_note', 'start_date', 'end_date']
        }),
        ('Contribution', {
            'fields': ['contribution', 'cv_ref_slug', 'order']
        })
    ]

class TechReportAdmin(admin.ModelAdmin):
    """Section II.A of the CV."""
    list_display = ['title', 'grant', 'report_type', 'date', 'authorship_percent']
    list_filter = ['report_type', 'grant']
    search_fields = ['title', 'description']
    ordering = ['order', '-date', 'title']
    prepopulated_fields = {'slug': ('title',), 'cv_ref_slug': ('title',)}
    fieldsets = [
        ('Basic Information', {
            'fields': ['grant', 'title', 'slug', 'report_type', 'date']
        }),
        ('Details', {
            'fields': ['page_count', 'slide_count', 'authorship_percent', 'description']
        }),
        ('Materials', {
            'fields': ['report', 'slides', 'cv_ref_slug', 'order']
        })
    ]

class ReviewAdmin(admin.ModelAdmin):
    """Sections V.A and V.B: peer review and editorial work."""
    list_display = ['venue', 'kind', 'year', 'manuscript_count']
    list_filter = ['kind', 'year']
    search_fields = ['venue', 'role']
    ordering = ['-year', 'venue']
    fieldsets = [
        ('Basic Information', {
            'fields': ['venue', 'kind', 'role', 'year', 'end_year', 'manuscript_count']
        }),
        ('Details', {
            'fields': ['detail']
        })
    ]

admin.site.register(Review, ReviewAdmin)
admin.site.register(Proposal, ProposalAdmin)
admin.site.register(TechReport, TechReportAdmin)
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