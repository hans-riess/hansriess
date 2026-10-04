"""Builds the LaTeX source for the CV.

The document follows the usual shape of an academic job-market CV, with
sponsored research and teaching ahead of the publication list:

    Research Interests
    Education
    Appointments
    Sponsored Research          funded projects [G], proposals [PR]
    Teaching and Mentoring
    Publications                [J], [C], [S], [P]
    Presentations               [T]
    Technical Contributions     delivered products [D], innovations [I],
                                technical reports [R]
    Honors and Awards
    Service

Entries that can be cross-referenced are numbered within their series. Numbers
count down, so the last entry printed in a series is 1 and an entry keeps its
number as new ones are added above it.

Every ``build_*`` function returns a list of LaTeX lines and returns an empty
list when it has no data, so sections that have not been filled in yet are
skipped rather than printed empty.

Typesetting lives in ``academic/tex/academic-cv.sty``.
"""

import datetime
import re

from .models import (Award, Course, DeliveredProduct, Education, Experience,
                     Grant, PUBLICATION_CATEGORIES, PUBLICATION_CATEGORY_ORDER,
                     Innovation, Proposal, Reference, Review, Service, Student,
                     Talk, TechReport)

PUBLICATION_CATEGORY_LABELS = dict(PUBLICATION_CATEGORIES)

# Service subsections, in print order. The first two come from Review; the
# rest are the Service categories, under the labels the admin shows.
SERVICE_ORDER = [
    ('journal_review', 'Editorial Service and Journal Reviewing'),
    ('conference_review', 'Conference Reviewing and Program Committees'),
] + Service.SERVICE_CATEGORIES

# LaTeX specials, longest-first so that backslashes are not re-escaped.
_LATEX_ESCAPES = [
    ('\\', r'\textbackslash{}'),
    ('&', r'\&'),
    ('%', r'\%'),
    ('$', r'\$'),
    ('#', r'\#'),
    ('_', r'\_'),
    ('{', r'\{'),
    ('}', r'\}'),
    ('~', r'\textasciitilde{}'),
    ('^', r'\textasciicircum{}'),
]

# Characters the CV uses that have no T1 slot, or that read better as a LaTeX
# command. En dashes, em dashes and curly quotes are fine under T1 and are left
# alone.
_UNICODE_MAP = {
    '•': r'\textbullet{}',   # bullet
    '†': r'\dag{}',          # dagger
    '‡': r'\ddag{}',         # double dagger
    '−': '--',               # minus sign
    ' ': '~',                # non-breaking space
    '…': r'\ldots{}',        # ellipsis
}

_REF_PATTERN = re.compile(r'\[\[ref:([\w\\\-]+)\]\]')


def escape_latex(text):
    """Escape LaTeX specials and map Unicode that pdflatex cannot typeset."""
    if not text:
        return ""
    text = str(text)
    for char, replacement in _LATEX_ESCAPES:
        text = text.replace(char, replacement)
    for char, replacement in _UNICODE_MAP.items():
        text = text.replace(char, replacement)
    return text


def resolve_refs(text):
    """Turn ``[[ref:some-slug]]`` markers into LaTeX cross-references.

    Run this *after* :func:`escape_latex`, which leaves the brackets alone but
    escapes underscores inside the slug; those are unescaped here.
    """
    def _replace(match):
        slug = match.group(1).replace('\\', '')
        return r'\ref{cv:%s}' % slug
    return _REF_PATTERN.sub(_replace, text or "")


def clean(text):
    """Escape a value and resolve its cross-references. The usual entry point."""
    return resolve_refs(escape_latex(text))


def paragraphs(text):
    """Split a text field into escaped paragraphs on blank lines."""
    if not text:
        return []
    blocks = re.split(r'\n\s*\n', text.strip())
    return [clean(' '.join(block.split())) for block in blocks if block.strip()]


def url_target(url):
    """Escape a URL for use as the target of ``\\href``.

    hyperref converts these escapes back, so the link still resolves.
    """
    if not url:
        return ""
    out = str(url)
    for char in ('\\', '{', '}'):
        out = out.replace(char, '')
    for char in ('%', '#', '&'):
        out = out.replace(char, '\\' + char)
    return out


def url_text(url):
    """Render a URL as visible body text that can break across lines."""
    if not url:
        return ""
    escaped = escape_latex(url)
    # Allow line breaks after the characters URLs are conventionally broken at.
    for char in ('/', '-', '.', '?', '=', r'\&', r'\_'):
        escaped = escaped.replace(char, char + r'\allowbreak{}')
    return escaped


def link(url):
    """A clickable URL printed as its own text, so it survives printing."""
    if not url:
        return ""
    return r'\href{%s}{%s}' % (url_target(url), url_text(url))


def label_for(obj):
    """A ``\\label`` line for an object carrying a cross-reference slug."""
    slug = getattr(obj, 'cv_ref_slug', None)
    if slug:
        return r'\label{cv:%s}' % slug
    return ""


def marker_prefix(obj):
    """The stacked dagger / double-dagger prefix for a publication."""
    marks = ""
    if getattr(obj, 'alphabetical_order', False):
        marks += r'\dag{}'
    if getattr(obj, 'shared_first_author', False):
        marks += r'\ddag{}'
    return marks


def format_authors(authors, surname):
    """Escape an author list, bolding the author whose name matches ``surname``."""
    if not authors:
        return ""
    if not surname:
        return escape_latex(authors)

    # Split on commas and on "and", keeping the separators so the list can be
    # rebuilt verbatim. Only the name itself is bolded, never the separator.
    pieces = re.split(r'(,\s*|\s+and\s+)', authors)
    rendered = []
    for index, piece in enumerate(pieces):
        if index % 2:                       # a separator
            rendered.append(escape_latex(piece))
            continue
        # ", and X" splits as ", " + "and X"; keep the conjunction unbolded.
        conjunction, name = re.match(r'^(and\s+)?(.*)$', piece.strip(),
                                     flags=re.IGNORECASE).groups()
        escaped = escape_latex(name)
        if escaped and re.search(r'\b%s\b' % re.escape(surname), name, flags=re.IGNORECASE):
            escaped = r'\textbf{%s}' % escaped
        rendered.append(escape_latex(conjunction or "") + escaped)
    return "".join(rendered)


def credit_sentence(roles):
    """The italic CRediT sentence that closes most publication entries."""
    if not roles:
        return ""
    return r' \textit{Contributed %s.}' % clean(roles.strip().rstrip('.'))


def quoted(title):
    """A title in curly double quotes, closed with the IEEE comma."""
    return "``%s,''" % clean(title.rstrip('.'))


# --- Citations ---------------------------------------------------------------

def format_reference(ref, profile):
    """An IEEE-style citation for a Reference."""
    parts = [marker_prefix(ref)]

    authors = format_authors(ref.authors, profile.surname())
    parts.append("%s, %s" % (authors, quoted(ref.title)) if authors else quoted(ref.title))

    # Work still in review is cited by its preprint rather than by a venue.
    as_preprint = ref.medium == 'preprint' or ref.status == 'in_review'
    venue_bits = []
    if as_preprint:
        if ref.arxiv_id:
            venue_bits.append("arXiv:%s" % clean(ref.arxiv_id))
        if ref.year:
            venue_bits.append(str(ref.year))
    else:
        if ref.journal:
            venue = r'\textit{%s}' % clean(ref.journal)
            if ref.medium == 'conference_proceedings':
                venue = "in " + venue
            venue_bits.append(venue)
        if ref.volume:
            venue_bits.append("vol. %s" % clean(ref.volume))
        if ref.issue:
            venue_bits.append("no. %s" % clean(ref.issue))
        if ref.pages:
            venue_bits.append("pp. %s" % clean(ref.pages))
        if ref.year:
            venue_bits.append(str(ref.year))

    if venue_bits:
        parts.append(" " + ", ".join(venue_bits))

    tail = ""
    note = ref.get_status_note()
    if note:
        # "to appear" continues the citation; "Submitted to X" is its own sentence.
        if note.lower().startswith('submitted'):
            tail = ". %s" % _italicise_submitted(note)
        else:
            tail = ", %s" % clean(note)
    parts.append(tail + ".")

    url = ref.url or (("https://doi.org/%s" % ref.doi) if ref.doi else "")
    if not url and ref.pdf_file:
        url = ref.pdf_file.url
    if url:
        parts.append(" [Online]. Available: %s." % link(url))

    parts.append(credit_sentence(ref.credit_roles))
    return "".join(parts)


def _italicise_submitted(note):
    """Render "Submitted to Compositionality" with the venue italicised."""
    match = re.match(r'^(Submitted to)\s+(.*)$', note, flags=re.IGNORECASE)
    if match:
        return r'%s \textit{%s}' % (clean(match.group(1)), clean(match.group(2).rstrip('.')))
    return clean(note)


def format_talk(talk, profile):
    """A presentation entry, cited like a paper with the candidate as speaker."""
    parts = [marker_prefix(talk)]

    name = r'\textbf{%s}' % clean(_initialled_name(profile))
    parts.append("%s, %s" % (name, quoted(talk.title)))

    verb = "poster presented at" if talk.talk_type == 'poster' else "presented at"
    venue_bits = [r'\textit{%s}' % clean(talk.venue)] if talk.venue else []
    if talk.location:
        venue_bits.append(clean(talk.location))
    if talk.date:
        venue_bits.append(talk.date.strftime('%B %Y'))
    parts.append(" %s %s." % (verb, ", ".join(venue_bits)))

    if talk.note:
        parts.append(" [%s]" % clean(' '.join(talk.note.split())))
    if talk.poster:
        parts.append(" [Online]. Available: %s." % link(talk.poster.url))
    elif talk.event_url:
        parts.append(" [Online]. Available: %s." % link(talk.event_url))

    parts.append(credit_sentence(talk.credit_roles))
    return "".join(parts)


def _initialled_name(profile):
    """"Hans Riess, Ph.D." -> "H. Riess", the form used in the citation lists."""
    parts = profile.name_parts()
    if len(parts) < 2:
        return profile.plain_name()
    initials = " ".join("%s." % p[0] for p in parts[:-1])
    return "%s %s" % (initials, parts[-1])


# --- Shared pieces -----------------------------------------------------------

def countdown(prefix, total):
    """Tags for a series printed top to bottom: J5, J4, ..., J1."""
    return ["%s%d" % (prefix, number) for number in range(total, 0, -1)]


def section(title, blocks):
    """A section heading over its blocks, or nothing if every block is empty."""
    body = [line for block in blocks for line in block]
    if not body:
        return []
    return [r'\cvsection{%s}' % title] + body


def sentence(text):
    """Close a fragment with exactly one full stop."""
    text = (text or "").strip()
    if not text:
        return ""
    return text if text.endswith(('.', '?', '!')) else text + "."


def month_range(start, end, open_ended="Present"):
    """'Aug 2025 – Aug 2026', or '' when neither end is known."""
    if not start and not end:
        return ""
    first = start.strftime('%b %Y') if start else ""
    last = end.strftime('%b %Y') if end else open_ended
    return "%s – %s" % (first, last)


def _people(names):
    """One person per line in a text field -> 'A; B'."""
    return "; ".join(clean(line.strip()) for line in (names or "").splitlines() if line.strip())


# --- Header ------------------------------------------------------------------

def build_header(profile):
    lines = [r'\begin{cvheader}', r'\cvname{%s}' % clean(profile.plain_name())]
    for value in (profile.long_title or profile.title, profile.department,
                  profile.long_institution or profile.institution):
        if value:
            lines.append(r'\cvheaderline{%s}' % clean(value))
    contact = _contact_line(profile)
    if contact:
        lines.append(r'\cvcontact{%s}' % contact)
    lines.append(r'\end{cvheader}')
    return lines


def _contact_line(profile):
    bits = []
    if profile.email:
        bits.append(r'\href{mailto:%s}{%s}' % (url_target(profile.email),
                                               escape_latex(profile.email)))
    if profile.phone:
        bits.append(clean(profile.phone))
    if profile.website:
        bits.append(r'\href{%s}{%s}' % (url_target(profile.website),
                                        escape_latex(profile.display_website.rstrip('/'))))
    return r'\cvsep{}'.join(bits)


def build_interests(profile):
    if not profile.fields_of_interest:
        return []
    return [r'\cvsection{Research Interests}',
            r'\cvparagraph{%s}' % clean(' '.join(profile.fields_of_interest.split()))]


# --- Education and appointments ----------------------------------------------

def build_education(profile):
    """Degrees, newest first, each with its dissertation if it has one."""
    if not profile.cv_show_preamble_sections:
        return []
    educations = Education.objects.order_by('-graduation_year')
    if not educations.exists():
        return []

    lines = [r'\cvsection{Education}']
    for item in educations:
        degree = clean(item.degree_type)
        if item.field_of_study:
            degree = "%s, %s" % (degree, clean(item.field_of_study))
        where = [clean(item.institution)]
        if item.location:
            where.append(clean(item.location))
        if item.honors:
            where.append(clean(item.honors))
        details = [", ".join(where)]
        if item.is_dissertation and item.thesis_title:
            details.append(_dissertation_line(item))
        lines.append(r'\cventry{}{\textbf{%s}}{%s}{%s}' % (
            degree, item.graduation_year, r'\cvpar '.join(details)))
    return lines


def _dissertation_line(item):
    kind = "Dissertation" if re.search(r'ph\.?\s*d|doctor', item.degree_type or "",
                                       flags=re.IGNORECASE) else "Thesis"
    bits = ["%s: ``%s.''" % (kind, clean(item.thesis_title.rstrip('.')))]
    if item.advisor:
        bits.append("Advisor: %s." % clean(item.advisor.rstrip('.')))
    if item.thesis_url:
        bits.append(link(item.thesis_url))
    return " ".join(bits)


def build_appointments(profile):
    if not profile.cv_show_preamble_sections:
        return []
    experiences = Experience.objects.order_by('-start_date')
    if not experiences.exists():
        return []

    lines = [r'\cvsection{Appointments}']
    for item in experiences:
        where = [clean(item.institution)]
        if item.department:
            where.insert(0, clean(item.department))
        if item.location:
            where.append(clean(item.location))
        lines.append(r'\cventry{}{\textbf{%s}}{%s}{%s}' % (
            clean(item.title), month_range(item.start_date, item.end_date),
            ", ".join(where)))
    return lines


# --- Sponsored research ------------------------------------------------------

def build_sponsored_research(profile):
    return section('Sponsored Research', [
        _funded_projects_block(profile),
        _proposals_block(profile),
        _research_program_block(profile),
    ])


def _funded_projects_block(profile):
    grants = list(Grant.objects.all())
    if not grants:
        return []

    lines = [r'\cvsubsection{Funded Projects}']
    for tag, grant in zip(countdown('G', len(grants)), grants):
        sponsor = clean(grant.funding_agency)
        if grant.grant_number:
            sponsor = "%s, %s" % (sponsor, clean(grant.grant_number))
        facts = [sentence(sponsor)]
        # The P.I. of record defaults to the candidate, which the role already says.
        if grant.pi_name:
            facts.append("PI: %s." % _people(grant.pi_name))
        facts.append(sentence("Role: %s" % clean(grant.get_cv_role())))
        if grant.task_title:
            facts.append(sentence("Task: %s" % clean(grant.task_title)))
        if grant.amount is not None:
            facts.append("Total award: %s." % clean(grant.get_cv_amount()))
        details = [" ".join(facts)] + paragraphs(grant.contributions)
        lines.append(r'\cventry{%s}{%s\textbf{%s}}{%s}{%s}' % (
            tag, label_for(grant), clean(grant.title),
            clean(grant.get_period_of_performance()), r'\cvpar '.join(details)))
    return lines


def _proposals_block(profile):
    proposals = list(Proposal.objects.all())
    if not proposals:
        return []

    lines = [r'\cvsubsection{Proposals}']
    for tag, proposal in zip(countdown('PR', len(proposals)), proposals):
        sponsor = clean(proposal.sponsor)
        if proposal.solicitation:
            sponsor = "%s, %s" % (sponsor, clean(proposal.solicitation))
        facts = [sentence(sponsor)]
        if proposal.pi_name:
            facts.append("PI: %s." % _people(proposal.pi_name))
        if proposal.candidate_role:
            facts.append(sentence("Role: %s" % clean(proposal.candidate_role)))
        if proposal.amount_requested is not None:
            facts.append("Amount requested: %s." % clean(proposal.get_cv_amount()))
        period = month_range(proposal.start_date, proposal.end_date)
        if period:
            facts.append("Proposed period: %s." % period)
        submitted = _submission_text(proposal)
        if submitted:
            facts.append(sentence(submitted))
        facts.append(sentence("Status: %s" % clean(proposal.get_result())))
        details = [" ".join(facts)] + paragraphs(proposal.contribution)
        lines.append(r'\cventry{%s}{%s\textbf{%s}}{%s}{%s}' % (
            tag, label_for(proposal), clean(proposal.title),
            _submission_month(proposal), r'\cvpar '.join(details)))
    return lines


def _submission_text(proposal):
    bits = []
    if proposal.date_abstract_submitted:
        bits.append("Abstract submitted %s"
                    % proposal.date_abstract_submitted.strftime('%B %-d, %Y'))
    if proposal.full_proposal_note:
        bits.append("full proposal %s" % clean(proposal.full_proposal_note))
    elif proposal.date_full_submitted:
        bits.append("full proposal submitted %s"
                    % proposal.date_full_submitted.strftime('%B %-d, %Y'))
    text = "; ".join(bits)
    return text[:1].upper() + text[1:]


def _submission_month(proposal):
    """The date column: when the proposal last went to the sponsor."""
    when = proposal.date_full_submitted or proposal.date_abstract_submitted
    return when.strftime('%b %Y') if when else ""


def _research_program_block(profile):
    blocks = paragraphs(profile.research_program)
    if not blocks:
        return []
    lines = [r'\cvsubsection{Research Program Development}']
    lines.extend(r'\cvparagraph{%s}' % block for block in blocks)
    return lines


# --- Teaching and mentoring --------------------------------------------------

# Where in the year each semester ends, so that courses sort chronologically.
SEMESTER_MONTHS = {'winter': 1, 'spring': 5, 'summer': 8, 'fall': 12}


def build_teaching_and_mentoring(profile):
    teaching, mentoring = _teaching_block(), _mentoring_block()
    if teaching and mentoring:
        return ([r'\cvsection{Teaching and Mentoring}', r'\cvsubsection{Teaching}']
                + teaching
                + [r'\cvsubsection{Student Mentoring}'] + mentoring)
    if teaching:
        return [r'\cvsection{Teaching}'] + teaching
    if mentoring:
        return [r'\cvsection{Student Mentoring}'] + mentoring
    return []


def _teaching_block():
    """Courses and workshops taught, plus tutorial lectures, newest first."""
    rows = []
    for course in Course.objects.all():
        when = None
        if course.year:
            when = datetime.date(course.year, SEMESTER_MONTHS.get(course.semester, 12), 1)
        count = ""
        if course.attendee_count:
            noun = "Enrollment" if course.course_format == 'course' else "Attendance"
            count = "%s: %s." % (noun, clean(course.attendee_count))
        rows.append((when,
                     r'\textbf{%s}, %s' % (clean(course.get_cv_title()),
                                           clean(course.get_cv_organization())),
                     clean(course.get_cv_when_taught()),
                     " ".join(bit for bit in (sentence(clean(course.get_cv_role())), count) if bit)))

    for talk in Talk.objects.all():
        if not talk.is_knowledge_sharing():
            continue
        role = clean(talk.curriculum_role) or clean(talk.get_talk_type_display())
        count = "Attendance: %s." % clean(talk.attendee_count) if talk.attendee_count else ""
        rows.append((talk.date,
                     r'\textbf{%s (tutorial)}, %s' % (clean(talk.title), clean(talk.venue)),
                     talk.date.strftime('%B %Y') if talk.date else "",
                     " ".join(bit for bit in (sentence(role), count) if bit)))

    rows.sort(key=lambda row: row[0] or datetime.date.min, reverse=True)
    return [r'\cventry{}{%s}{%s}{%s}' % row[1:] for row in rows]


def _mentoring_block():
    lines = []
    for student in Student.objects.order_by('-start_date'):
        heading = r"\textbf{%s}, %s student, %s" % (clean(student.name),
                                                    clean(student.get_level_display()),
                                                    clean(student.institution))
        bits = []
        if student.appointment_note:
            bits.append(sentence(clean(student.appointment_note)))
        topic = student.research_topic or student.project_title
        if topic:
            bits.append("Research topic: %s." % clean(topic.rstrip('.')))
        refs = [p.cv_ref_slug for p in student.resulting_publications.all() if p.cv_ref_slug]
        if refs:
            joined = ", ".join(r'\ref{cv:%s}' % slug for slug in refs)
            bits.append("Resulting publication%s: %s." % ("s" if len(refs) > 1 else "", joined))
        if student.advisor_of_record:
            bits.append("Advisor of record: %s." % clean(student.advisor_of_record.rstrip('.')))
        if student.host_lab:
            bits.append("Host lab: %s." % clean(student.host_lab.rstrip('.')))
        if student.current_position:
            bits.append("Current position: %s." % clean(student.current_position.rstrip('.')))
        lines.append(r'\cventry{}{%s}{%s}{%s}' % (heading, student.get_date_range(),
                                                 " ".join(bits)))
    return lines


# --- Publications and presentations ------------------------------------------

# Which categories print together, and the prefix they are numbered under.
# Headings come from PUBLICATION_CATEGORIES. Groups sharing a prefix form one
# series, so refereed and non-refereed proceedings run C5 ... C1 between them.
PUBLICATION_GROUPS = [
    (('journal',), 'J'),
    (('proc_refereed',), 'C'),
    (('proc_nonrefereed',), 'C'),
    (('submitted', 'submitted_conf'), 'S'),
    (('preprints',), 'P'),
]
PRESENTATION_GROUPS = [
    (('invited_conf',), 'T'),
    (('no_proc',), 'T'),
]


def _grouped_publications(profile):
    """Reference and Talk rows by category, as (sort key, object) pairs.

    References are filtered by status unless the profile says to show all. A talk
    that links a reference which is itself listed here is dropped, so a paper and
    the talk announcing it are not both cited.
    """
    show_all = profile.cv_show_all_references
    grouped = {key: [] for key in PUBLICATION_CATEGORY_ORDER}

    listed_reference_ids = set()
    for ref in Reference.objects.all():
        if not ref.show_on_cv(show_all):
            continue
        category = ref.get_category()
        if category in grouped:
            grouped[category].append((ref.cv_sort_key(), ref))
            listed_reference_ids.add(ref.pk)

    for talk in Talk.objects.all():
        if talk.reference_id and talk.reference_id in listed_reference_ids:
            continue
        category = talk.get_category()
        if category in grouped:
            grouped[category].append((talk.cv_sort_key(), talk))
    return grouped


def _numbered_groups(grouped, groups, profile):
    """A subsection per non-empty group, entries numbered down within each prefix."""
    remaining = {}
    for categories, prefix in groups:
        remaining[prefix] = remaining.get(prefix, 0) + sum(len(grouped[c]) for c in categories)

    lines = []
    for categories, prefix in groups:
        entries = [pair for category in categories for pair in grouped[category]]
        if not entries:
            continue
        lines.append(r'\cvsubsection{%s}' % clean(PUBLICATION_CATEGORY_LABELS[categories[0]]))
        for _, obj in sorted(entries, key=lambda pair: pair[0], reverse=True):
            tag = "%s%d" % (prefix, remaining[prefix])
            remaining[prefix] -= 1
            if isinstance(obj, Reference):
                body = format_reference(obj, profile)
            else:
                body = format_talk(obj, profile)
            lines.append(r'\cvcite{%s}{%s%s}' % (tag, label_for(obj), body))
    return lines


def _marker_key(grouped, groups):
    """The dagger key, naming only the markers that are actually used."""
    listed = [obj for categories, _ in groups for c in categories for _, obj in grouped[c]]
    notes = []
    if any(getattr(obj, 'alphabetical_order', False) for obj in listed):
        notes.append(r'\dag{} Authors listed alphabetically.')
    if any(getattr(obj, 'shared_first_author', False) for obj in listed):
        notes.append(r'\ddag{} Shared first authorship.')
    return [r'\cvnote{%s}' % r'\qquad '.join(notes)] if notes else []


def build_publications(profile):
    grouped = _grouped_publications(profile)
    body = _numbered_groups(grouped, PUBLICATION_GROUPS, profile)
    if not body:
        return []
    return ([r'\cvsection{Publications}'] + _marker_key(grouped, PUBLICATION_GROUPS)
            + body)


def build_presentations(profile):
    grouped = _grouped_publications(profile)
    return section('Presentations', [_numbered_groups(grouped, PRESENTATION_GROUPS, profile)])


# --- Technical contributions -------------------------------------------------

def build_technical_contributions():
    return section('Technical Contributions', [
        _delivered_products_block(),
        _innovations_block(),
        _reports_block(),
    ])


def _labelled_paragraphs(caption, value):
    """Paragraphs of a prose field, the first one opening with an italic label."""
    blocks = paragraphs(value)
    if not blocks:
        return []
    return [r'\cvlabelled{%s}{%s}' % (clean(caption), blocks[0])] + blocks[1:]


def _delivered_products_block():
    products = list(DeliveredProduct.objects.all())
    if not products:
        return []

    lines = [r'\cvsubsection{Delivered Products}']
    for tag, product in zip(countdown('D', len(products)), products):
        heading = r'%s\textbf{%s}' % (label_for(product), clean(product.name))
        if product.summary:
            heading += " — %s" % clean(product.summary)
        details = []
        if product.sponsor:
            details.append(r'\cvlabelled{Delivered to}{%s}' % sentence(clean(product.sponsor)))
        for caption, value in (("Description", product.description),
                               ("Maturity", product.maturity),
                               ("Contribution", product.technical_contribution)):
            details.extend(_labelled_paragraphs(caption, value))
        lines.append(r'\cventry{%s}{%s}{%s}{%s}' % (
            tag, heading, clean(product.date_range), r'\cvpar '.join(details)))
    return lines


def _innovations_block():
    innovations = list(Innovation.objects.all())
    if not innovations:
        return []

    lines = [r'\cvsubsection{Technical Innovations on Sponsored Programs}']
    for tag, innovation in zip(countdown('I', len(innovations)), innovations):
        details = []
        sponsors = innovation.get_sponsors_line()
        if sponsors:
            details.append(r'\cvlabelled{Programs}{%s}' % sentence(clean(sponsors)))
        details.extend(_labelled_paragraphs("Description", innovation.description))
        details.extend(_labelled_paragraphs("Contributions", innovation.technical_contributions))
        lines.append(r'\cventry{%s}{%s\textbf{%s}}{}{%s}' % (
            tag, label_for(innovation), clean(innovation.title), r'\cvpar '.join(details)))
    return lines


def _reports_block():
    """Reports delivered to sponsors, grouped by award, numbered as one series."""
    grants = [(grant, list(grant.tech_reports.all())) for grant in Grant.objects.all()]
    grants = [(grant, reports) for grant, reports in grants if reports]
    if not grants:
        return []

    tags = iter(countdown('R', sum(len(reports) for _, reports in grants)))
    lines = [r'\cvsubsection{Technical Reports and Briefings}']
    for grant, reports in grants:
        heading = "%s technical report series." % (grant.short_title or grant.title)
        preamble = " ".join(paragraphs(grant.report_series_note))
        lines.append(r'\cvrunin{%s}{%s}' % (clean(heading), preamble))
        for report in reports:
            bits = [r'\textbf{%s}.' % clean(report.title.rstrip('.'))]
            detail = [clean(report.get_report_type_display())]
            if report.date:
                detail.append(report.date.strftime('%B %Y'))
            if report.page_count:
                detail.append("%d pages" % report.page_count)
            if report.slide_count:
                detail.append("%d slides" % report.slide_count)
            if report.authorship_percent is not None:
                detail.append(r"%d\%% authorship" % report.authorship_percent)
            bits.append(" %s." % "; ".join(bit for bit in detail if bit))
            if report.description:
                bits.append(" %s" % " ".join(paragraphs(report.description)))
            lines.append(r'\cvcite{%s}{%s%s}' % (next(tags), label_for(report), "".join(bits)))
    return lines


# --- Honors and awards -------------------------------------------------------

def build_awards():
    awards = Award.objects.all()
    if not awards.exists():
        return []

    lines = [r'\cvsection{Honors and Awards}']
    for award in awards:
        heading = r'\textbf{%s}' % clean(award.title)
        if award.organization:
            heading += ", %s" % clean(award.organization)
        lines.append(r'\cventry{}{%s}{%s}{%s}' % (
            heading, clean(award.get_cv_date()),
            " ".join(sentence(block) for block in paragraphs(award.detail))))
    return lines


# --- Service -----------------------------------------------------------------

def build_service(profile):
    """Reviewing and editorial work (from Review), then everything else (Service)."""
    grouped = {key: [] for key, _ in SERVICE_ORDER}

    for review in Review.objects.all():
        category = review.get_category()
        if category in grouped:
            grouped[category].append(_review_entry(review, profile))
    for service in Service.objects.order_by('-year', 'title'):
        category = service.get_category()
        if category in grouped:
            grouped[category].append(_service_entry(service, profile))

    if not any(grouped.values()):
        return []

    lines = [r'\cvsection{Service}']
    for key, heading in SERVICE_ORDER:
        entries = grouped[key]
        if not entries:
            continue
        lines.append(r'\cvsubsection{%s}' % clean(heading))
        lines.extend(r'\cvplain{%s}' % body for body in entries)
    return lines


def _review_entry(review, profile):
    """A reviewing or editorial entry, e.g. "Reviewer, Automatica, 2026 (1 manuscript)."."""
    bits = [", ".join(part for part in (
        r'\textbf{%s}' % clean(review.get_role()),
        clean(review.venue), clean(review.get_years())) if part)]
    if review.manuscript_count:
        bits.append(" (%d manuscript%s)" % (review.manuscript_count,
                                            "" if review.manuscript_count == 1 else "s"))
    bits.append(".")
    if review.detail:
        bits.append(" %s" % " ".join(paragraphs(review.detail)))
    return "".join(bits)


def _service_entry(service, profile):
    bits = []

    lead = [r'\textbf{%s}' % clean(service.get_role_display())]
    if service.title:
        lead.append(clean(service.title))
    lead.append(clean(service.organization))
    if service.location:
        lead.append(clean(service.location))
    lead.append(_service_years(service))
    bits.append(", ".join(part for part in lead if part))

    bits.append(".")
    if service.detail:
        bits.append(" %s" % " ".join(paragraphs(service.detail)))
    return "".join(bits)


def _service_years(service):
    if service.start_date:
        start = service.start_date.strftime('%b %Y')
        end = service.end_date.strftime('%b %Y') if service.end_date else "Present"
        return "%s -- %s" % (start, end)
    if service.end_year and service.end_year != service.year:
        return "%s -- %s" % (service.year, service.end_year)
    return str(service.year) if service.year else ""


# --- Document ----------------------------------------------------------------

def build_document(profile):
    """Assemble the complete LaTeX source for the CV."""
    lines = [
        r'\documentclass[11pt]{article}',
        r'\usepackage{academic-cv}',
        r'\cvfootername{%s}' % clean(profile.plain_name()),
        r'\begin{document}',
    ]
    for part in (build_header(profile),
                 build_interests(profile),
                 build_education(profile),
                 build_appointments(profile),
                 build_sponsored_research(profile),
                 build_teaching_and_mentoring(profile),
                 build_publications(profile),
                 build_presentations(profile),
                 build_technical_contributions(),
                 build_awards(),
                 build_service(profile)):
        lines.extend(part)
    lines.append(r'\end{document}')
    return "\n".join(line for line in lines if line)
