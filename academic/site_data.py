"""Builds the structured site data served at /sitedata/data.json.

The export is meant as context for people and AI tools, e.g. when drafting job
applications. It lists what the public CV lists, in the same order and with the
same numbers ([J3], [G1], ...), as plain data rather than LaTeX: dates are ISO
strings, amounts are numbers, and ``[[ref:slug]]`` markers in prose become the
title and number of the entry they point at.

Because the URL is public, nothing goes in that the site does not already show:
the CV's own filters apply (hidden references, the venue that rejected a
preprint), and a password-protected grant contributes only what the CV prints.
"""

import datetime
import re

from django.utils.html import strip_tags

from . import cv_builder
from .cv_builder import (PRESENTATION_GROUPS, PUBLICATION_CATEGORY_LABELS,
                         PUBLICATION_GROUPS, SEMESTER_MONTHS, SERVICE_ORDER)
from .models import (Award, Course, DeliveredProduct, Education, Experience,
                     Grant, Innovation, Proposal, Reference, Review, Service,
                     Student, Talk, TechReport)

_REF_PATTERN = re.compile(r'\[\[ref:([\w\-]+)\]\]')

# Every model that can carry a cv_ref_slug, with the field that names an entry.
_REFERABLE = [
    (Reference, 'title'), (Talk, 'title'), (Grant, 'title'), (Proposal, 'title'),
    (DeliveredProduct, 'name'), (Innovation, 'title'), (TechReport, 'title'),
    (Award, 'title'),
]


def compact(data):
    """Drop keys with no value, so entries carry only what is filled in."""
    return {key: value for key, value in data.items()
            if value is not None and value != "" and value != [] and value != {}}


def iso(value):
    return value.isoformat() if value else None


def number(value):
    """A Decimal amount as a JSON number, whole amounts as integers."""
    if value is None:
        return None
    return int(value) if value == int(value) else float(value)


class Resolver:
    """Turns ``[[ref:slug]]`` into '"Title" [J3]' and tidies prose fields."""

    def __init__(self, numbers):
        self.targets = {}
        for model, field in _REFERABLE:
            for obj in model.objects.exclude(cv_ref_slug__isnull=True).exclude(cv_ref_slug=""):
                tag = numbers.get((model, obj.pk))
                title = "“%s”" % getattr(obj, field).rstrip('.')
                self.targets[obj.cv_ref_slug] = "%s [%s]" % (title, tag) if tag else title

    def text(self, value):
        """Prose with references resolved, blank-line paragraphs kept."""
        if not value:
            return None
        value = _REF_PATTERN.sub(lambda m: self.targets.get(m.group(1), m.group(1)), value)
        blocks = re.split(r'\n\s*\n', value.strip())
        return "\n\n".join(" ".join(block.split()) for block in blocks if block.strip()) or None

    def html(self, value):
        """Like text(), for fields the site renders as HTML."""
        return self.text(strip_tags(value)) if value else None


def build_site_data(profile, base_url=None):
    """The whole export as a JSON-ready dict.

    ``base_url`` is used for the self links only when the profile has no website.
    """
    grouped = cv_builder.grouped_publications(profile)
    publications = list(cv_builder.numbered_entries(grouped, PUBLICATION_GROUPS))
    presentations = list(cv_builder.numbered_entries(grouped, PRESENTATION_GROUPS))
    grants = cv_builder.numbered('G', Grant.objects.all())
    proposals = cv_builder.numbered('PR', Proposal.objects.all())
    products = cv_builder.numbered('D', DeliveredProduct.objects.all())
    innovations = cv_builder.numbered('I', Innovation.objects.all())
    reports = cv_builder.report_series()

    numbers = {}
    for _, tag, obj in publications + presentations:
        numbers[(type(obj), obj.pk)] = tag
    for series in (grants, proposals, products, innovations):
        for tag, obj in series:
            numbers[(type(obj), obj.pk)] = tag
    for _, entries in reports:
        for tag, report in entries:
            numbers[(TechReport, report.pk)] = tag
    resolve = Resolver(numbers)

    # A talk on a listed paper is not cited separately; it is noted on the paper.
    listed_papers = {obj.pk for _, _, obj in publications if isinstance(obj, Reference)}
    talks_by_paper = {}
    for talk in Talk.objects.filter(reference_id__in=listed_papers):
        talks_by_paper.setdefault(talk.reference_id, []).append(talk)

    # Prefer the profile's canonical address over whatever host served the request.
    website = (profile.website or "").rstrip('/')
    base = website or (base_url or "").rstrip('/')
    return compact({
        'about': compact({
            'description': (
                "Structured CV data for %s, generated from the database behind "
                "%s. It lists what the public CV lists, newest first, under the "
                "same numbers ([J3], [G1], ...)." % (profile.plain_name(), website or "the site")),
            'generated_at': datetime.datetime.now(datetime.timezone.utc)
                                    .replace(microsecond=0).isoformat(),
            'source': "%s/sitedata/data.json" % base if base else None,
            'cv_pdf': "%s/cv/" % base if base else None,
            'conventions': {
                'cv_number': "The entry's number on the CV PDF. Each series "
                             "counts down, so the last entry printed is 1.",
                'contribution': "The CRediT roles the candidate took on.",
                'author_order': "'alphabetical' when authors are listed "
                                "alphabetically rather than by contribution.",
                'shared_first_author': "First authorship is shared.",
                'dates': "ISO 8601. An appointment or award with no end date is current.",
            },
        }),
        'profile': _profile(profile, resolve),
        'education': _education(profile),
        'appointments': _appointments(profile),
        'sponsored_research': compact({
            'funded_projects': [_grant(tag, grant, resolve) for tag, grant in grants],
            'proposals': [_proposal(tag, proposal, resolve) for tag, proposal in proposals],
            'research_program': resolve.text(profile.research_program),
        }),
        'teaching': _teaching(resolve),
        'mentoring': [_student(student, numbers) for student in
                      Student.objects.order_by('-start_date')],
        'publications': [_listed(category, tag, obj, profile, resolve, talks_by_paper)
                         for category, tag, obj in publications],
        'presentations': [_listed(category, tag, obj, profile, resolve, talks_by_paper)
                          for category, tag, obj in presentations],
        'technical_contributions': compact({
            'delivered_products': [_product(tag, p, resolve) for tag, p in products],
            'innovations': [_innovation(tag, i, resolve) for tag, i in innovations],
            'technical_reports': [_report(tag, grant, report, resolve)
                                  for grant, entries in reports for tag, report in entries],
        }),
        'awards': [_award(award, resolve) for award in Award.objects.all()],
        'service': _service(resolve),
    })


# --- Profile, education, appointments ----------------------------------------

def _profile(profile, resolve):
    address = [profile.room_number, profile.building, profile.street,
               " ".join(bit for bit in (", ".join(b for b in (profile.city, profile.state) if b),
                                        profile.zip_code) if bit),
               profile.country]
    links = {name: getattr(profile, name) for name in (
        'google_scholar', 'orcid', 'github', 'linkedin', 'twitter', 'blue_sky',
        'mastodon', 'youtube')}
    return compact({
        'name': profile.plain_name(),
        'title': profile.long_title or profile.title,
        'department': profile.department,
        'institution': profile.long_institution or profile.institution,
        'email': profile.email,
        'phone': profile.phone,
        'website': profile.website,
        'address': [line for line in address if line],
        'links': compact(links),
        'research_interests': [bit.strip().rstrip('.') for bit in
                               (profile.fields_of_interest or "").split(';') if bit.strip()],
        'bio': resolve.html(profile.bio),
        'short_bio': resolve.html(profile.short_bio),
    })


def _education(profile):
    if not profile.cv_show_preamble_sections:
        return []
    entries = []
    for item in Education.objects.order_by('-graduation_year'):
        dissertation = None
        if item.is_dissertation and item.thesis_title:
            dissertation = compact({'title': item.thesis_title, 'advisor': item.advisor,
                                    'url': item.thesis_url})
        entries.append(compact({
            'degree': item.degree_type,
            'field': item.field_of_study,
            'institution': item.institution,
            'location': item.location,
            'year': item.graduation_year,
            'honors': item.honors,
            'dissertation': dissertation,
        }))
    return entries


def _appointments(profile):
    if not profile.cv_show_preamble_sections:
        return []
    return [compact({
        'title': item.title,
        'department': item.department,
        'institution': item.institution,
        'location': item.location,
        'start': iso(item.start_date),
        'end': iso(item.end_date),
    }) for item in Experience.objects.order_by('-start_date')]


# --- Sponsored research ------------------------------------------------------

def _people(names):
    return [line.strip() for line in (names or "").splitlines() if line.strip()]


def _grant(tag, grant, resolve):
    return compact({
        'cv_number': tag,
        'title': grant.title,
        'short_title': grant.short_title,
        'sponsor': grant.funding_agency,
        'award_number': grant.grant_number,
        'role': grant.get_cv_role(),
        'pi': _people(grant.pi_name),
        'task': grant.task_title,
        'amount': number(grant.amount),
        'currency': grant.currency if grant.amount is not None else None,
        'start': iso(grant.start_date),
        'end': iso(grant.end_date),
        'contributions': resolve.text(grant.contributions),
        # The project page hides a protected grant's description.
        'description': None if grant.password_protected else resolve.html(grant.description),
    })


def _proposal(tag, proposal, resolve):
    return compact({
        'cv_number': tag,
        'title': proposal.title,
        'sponsor': proposal.sponsor,
        'solicitation': proposal.solicitation,
        'role': proposal.candidate_role,
        'pi': _people(proposal.pi_name),
        'amount_requested': number(proposal.amount_requested),
        'currency': proposal.currency if proposal.amount_requested is not None else None,
        'abstract_submitted': iso(proposal.date_abstract_submitted),
        'full_proposal_submitted': iso(proposal.date_full_submitted),
        'full_proposal_note': proposal.full_proposal_note,
        'proposed_start': iso(proposal.start_date),
        'proposed_end': iso(proposal.end_date),
        'status': proposal.get_result(),
        'contribution': resolve.text(proposal.contribution),
    })


# --- Teaching and mentoring --------------------------------------------------

def _teaching(resolve):
    rows = []
    for course in Course.objects.all():
        when = datetime.date(course.year, SEMESTER_MONTHS.get(course.semester, 12), 1)
        rows.append((when, compact({
            'title': course.title,
            'code': course.course_code,
            'format': course.get_course_format_display(),
            'institution': course.get_cv_organization(),
            'term': course.get_cv_when_taught(),
            'role': course.get_cv_role(),
            'level': 'graduate' if course.is_graduate else None,
            'online': True if course.is_online else None,
            ('enrollment' if course.course_format == 'course' else 'attendance'):
                course.attendee_count,
        })))
    for talk in Talk.objects.all():
        if not talk.is_knowledge_sharing():
            continue
        rows.append((talk.date, compact({
            'title': talk.title,
            'format': talk.get_talk_type_display(),
            'institution': talk.venue,
            'location': talk.location,
            'term': talk.date.strftime('%B %Y') if talk.date else None,
            'date': iso(talk.date),
            'role': talk.curriculum_role,
            'attendance': talk.attendee_count,
        })))
    rows.sort(key=lambda row: row[0] or datetime.date.min, reverse=True)
    return [entry for _, entry in rows]


def _student(student, numbers):
    papers = [numbers.get((Reference, p.pk)) for p in student.resulting_publications.all()]
    return compact({
        'name': student.name,
        'level': student.get_level_display(),
        'institution': student.institution,
        'appointment': student.appointment_note,
        'start': iso(student.start_date),
        'end': iso(student.end_date),
        'research_topic': student.research_topic or student.project_title,
        'resulting_publications': [tag for tag in papers if tag],
        'advisor_of_record': student.advisor_of_record,
        'host_lab': student.host_lab,
        'current_position': student.current_position,
    })


# --- Publications and presentations ------------------------------------------

def _listed(category, tag, obj, profile, resolve, talks_by_paper):
    entry = (_reference(obj, resolve, talks_by_paper) if isinstance(obj, Reference)
             else _talk(obj))
    return compact(dict({'cv_number': tag, 'category': PUBLICATION_CATEGORY_LABELS[category]},
                        **entry))


def _reference(ref, resolve, talks_by_paper):
    status = {'in_review': 'under review', 'accepted': 'accepted (to appear)'}.get(
        ref.status, 'preprint' if ref.medium == 'preprint' else 'published')
    # Only a live submission names its venue: a rejected preprint's Journal is
    # the venue that turned it down, which the CV never prints either.
    venue = submitted_to = None
    if ref.status == 'in_review':
        submitted_to = ref.journal
    elif ref.medium != 'preprint':
        venue = ref.journal
    return {
        'title': ref.title,
        'authors': ref.authors,
        'author_order': 'alphabetical' if ref.alphabetical_order else None,
        'shared_first_author': True if ref.shared_first_author else None,
        'year': ref.year,
        'date': iso(ref.publication_date),
        'status': status,
        'venue': venue,
        'submitted_to': submitted_to,
        'refereed': ref.refereed if venue else None,
        'volume': ref.volume,
        'issue': ref.issue,
        'pages': ref.pages,
        'doi': ref.doi,
        'arxiv_id': ref.arxiv_id,
        'url': ref.url,
        'code': ref.code,
        'contribution': ref.credit_roles,
        'abstract': resolve.text(ref.abstract),
        'keywords': [k.strip() for k in (ref.keywords or "").split(',') if k.strip()],
        'presented_at': [compact({'venue': talk.venue, 'location': talk.location,
                                  'date': iso(talk.date),
                                  'invited': True if talk.invited else None})
                         for talk in talks_by_paper.get(ref.pk, [])],
    }


def _talk(talk):
    return {
        'title': talk.title,
        'type': talk.get_talk_type_display(),
        'invited': talk.invited,
        'venue': talk.venue,
        'location': talk.location,
        'date': iso(talk.date),
        'note': " ".join((talk.note or "").split()),
        'url': talk.event_url,
        'contribution': talk.credit_roles,
    }


# --- Technical contributions -------------------------------------------------

def _product(tag, product, resolve):
    return compact({
        'cv_number': tag,
        'name': product.name,
        'summary': product.summary,
        'delivered_to': product.sponsor,
        'period': product.date_range,
        'description': resolve.text(product.description),
        'maturity': resolve.text(product.maturity),
        'contribution': resolve.text(product.technical_contribution),
    })


def _innovation(tag, innovation, resolve):
    return compact({
        'cv_number': tag,
        'title': innovation.title,
        'programs': innovation.get_sponsors_line(),
        'description': resolve.text(innovation.description),
        'contributions': resolve.text(innovation.technical_contributions),
    })


def _report(tag, grant, report, resolve):
    return compact({
        'cv_number': tag,
        'title': report.title,
        'award': grant.short_title or grant.title,
        'type': report.get_report_type_display(),
        'date': iso(report.date),
        'pages': report.page_count,
        'slides': report.slide_count,
        'authorship_percent': report.authorship_percent,
        'description': resolve.text(report.description),
    })


# --- Awards and service ------------------------------------------------------

def _award(award, resolve):
    return compact({
        'title': award.title,
        'organization': award.organization,
        'year': award.year,
        'period': award.date_range,
        'detail': resolve.text(award.detail),
    })


def _service(resolve):
    labels = dict(SERVICE_ORDER)
    reviewing = [compact({
        'category': labels.get(review.get_category()),
        'role': review.get_role(),
        'venue': review.venue,
        'years': review.get_years(),
        'manuscripts': review.manuscript_count,
        'detail': resolve.text(review.detail),
    }) for review in Review.objects.all()]
    activities = [compact({
        'category': labels.get(service.get_category()),
        'role': service.get_role_display(),
        'title': service.title,
        'organization': service.organization,
        'location': service.location,
        'start': iso(service.start_date),
        'end': iso(service.end_date),
        'year': service.year,
        'end_year': service.end_year,
        'detail': resolve.text(service.detail),
    }) for service in Service.objects.order_by('-year', 'title')]
    return compact({'reviewing': reviewing, 'activities': activities})
