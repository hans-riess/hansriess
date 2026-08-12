"""Builds the LaTeX source for the CV in the official Georgia Tech format.

The document follows the five-part structure of the Georgia Tech research-faculty
CV:

    I.   Mastery of a Complex Field
    II.  Technical Contributions and Innovation
    III. Project Leadership and Supervision
    IV.  Sponsored Program Development
    V.   Outreach and Service

Every ``build_*`` function returns a list of LaTeX lines and returns an empty
list when it has no data, so sections that have not been filled in yet are
skipped rather than printed empty.

Typesetting lives in ``academic/tex/academic-cv.sty``.
"""

import datetime
import re

from .models import (Award, Course, DeliveredProduct, Education, Experience,
                     Grant, GT_PUB_CATEGORIES, GT_PUB_CATEGORY_ORDER,
                     Innovation, Proposal, Reference, Service, Student, Talk,
                     TechReport)

GT_PUB_CATEGORY_LABELS = dict(GT_PUB_CATEGORIES)

# Section V subsections, in the order the official CV prints them.
GT_SERVICE_ORDER = [
    ('journal_review', 'Reviewer Work for Technical Journals'),
    ('conference_review', 'Reviewer Work for Conferences'),
    ('session_chair', 'Conference Session Chairs'),
    ('special_activity', 'Special Activities'),
    ('outside_professional', 'Outside Professional Activities/Consulting'),
    ('civic', 'Civic Activities'),
]

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
    """A clickable URL printed as its own text, as the official CV does."""
    if not url:
        return ""
    return r'\href{%s}{%s}' % (url_target(url), url_text(url))


def label_for(obj):
    """A ``\\label`` line for an object carrying a cross-reference slug."""
    slug = getattr(obj, 'cv_ref_slug', None)
    if slug:
        return r'\label{cv:%s}' % slug
    return ""


def is_pre_gt(obj, profile, when):
    """Whether an entry predates the Georgia Tech hire date (the ``*`` marker)."""
    explicit = getattr(obj, 'pre_gt_hire', None)
    if explicit is not None:
        return explicit
    if not profile.gt_hire_date or when is None:
        return False
    return when < profile.gt_hire_date


def marker_prefix(obj, profile, when):
    """The stacked ``*`` / dagger / double-dagger prefix for a publication."""
    marks = ""
    if is_pre_gt(obj, profile, when):
        marks += "*"
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
    """The italic CRediT sentence that closes most Section I.B entries."""
    if not roles:
        return ""
    return r' \textit{Contributed %s.}' % clean(roles.strip().rstrip('.'))


def quoted(title):
    """A title in the curly double quotes the official CV uses."""
    return "``%s,''" % clean(title.rstrip('.'))


# --- Section I.B citations ---------------------------------------------------

def format_reference(ref, profile):
    """An IEEE-style citation for a Reference, in the official CV's dialect."""
    parts = [marker_prefix(ref, profile, ref.cv_date())]

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
    """A presentation entry, in the style of Section I.B.2 and I.B.5."""
    parts = [marker_prefix(talk, profile, talk.date)]

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


# --- Header and preamble -----------------------------------------------------

def build_header(profile):
    lines = [r'\begin{cvheader}', r'\cvheadertitle{Curriculum Vitae}']
    lines.append(r'\cvheadername{%s}' % clean(profile.name))
    for value in (profile.long_title or profile.title, profile.department,
                  profile.long_institution or profile.institution):
        if value:
            lines.append(r'\cvheaderline{%s}' % clean(value))
    lines.append(r'\end{cvheader}')

    if profile.fields_of_interest:
        lines.append(r'\cvminihead{Current Fields of Interest:}')
        lines.append(r'\cvline{%s}' % clean(' '.join(profile.fields_of_interest.split())))

    lines.extend(build_preamble_sections(profile))
    lines.extend(build_key(profile))
    return lines


def build_preamble_sections(profile):
    """EDUCATION and PROFESSIONAL APPOINTMENTS.

    The strict Georgia Tech format has neither, but dropping them would lose the
    only record of Hans's degrees and positions on the public CV, so they are
    printed above Section I unless the profile turns them off.
    """
    if not profile.cv_show_preamble_sections:
        return []

    lines = []
    educations = Education.objects.order_by('-graduation_year')
    if educations.exists():
        lines.append(r'\cvminihead{Education}')
        for item in educations:
            degree = clean(item.degree_type)
            if item.field_of_study:
                degree = "%s, %s" % (degree, clean(item.field_of_study))
            where = [clean(item.institution)]
            if item.location:
                where.append(clean(item.location))
            if item.honors:
                where.append(clean(item.honors))
            lines.append(r'\cvpreentry{%s}{%s}{%s}' % (
                degree, ", ".join(where), item.graduation_year))

    experiences = Experience.objects.order_by('-start_date')
    if experiences.exists():
        lines.append(r'\cvminihead{Professional Appointments}')
        for item in experiences:
            start = item.start_date.strftime('%b %Y') if item.start_date else ""
            end = item.end_date.strftime('%b %Y') if item.end_date else "Present"
            where = [clean(item.institution)]
            if item.department:
                where.insert(0, clean(item.department))
            if item.location:
                where.append(clean(item.location))
            lines.append(r'\cvpreentry{%s}{%s}{%s}' % (
                clean(item.title), ", ".join(where), "%s – %s" % (start, end)))

    return lines


def build_key(profile):
    """The KEY block explaining the *, dagger and double-dagger markers."""
    lines = [r'\cvminihead{Key}']
    lines.append(r'\cvline{* %s}' % clean(profile.gt_key_note()))
    lines.append(r'\cvline{\dag{} Authors listed alphabetically.}')
    lines.append(r'\cvline{\ddag{} Shared first authorship.}')
    return lines


# --- Section I ---------------------------------------------------------------

def build_section_i(profile):
    blocks = [
        _thesis_block(profile),
        _publications_block(profile),
        _delivered_products_block(),
        _awards_block(profile),
        _knowledge_sharing_block(profile),
    ]
    body = [line for block in blocks for line in block]
    if not body:
        return []
    return [r'\cvsection{Mastery of a Complex Field}'] + body


def _thesis_block(profile):
    theses = Education.objects.filter(is_dissertation=True).order_by('-graduation_year')
    theses = [t for t in theses if t.thesis_title]
    if not theses:
        return []

    lines = [r'\cvsubsection{Thesis/Dissertation}']
    for item in theses:
        when = datetime.date(item.graduation_year, 12, 31) if item.graduation_year else None
        entry = [marker_prefix(item, profile, when)]
        entry.append("%s. ``%s.''" % (clean(_surname_first(profile)), clean(item.thesis_title.rstrip('.'))))
        degree = item.degree_type or ""
        if 'dissertation' not in degree.lower() and 'thesis' not in degree.lower():
            degree = ("%s Dissertation" % degree).strip()
        entry.append(" %s, %s, %s." % (clean(degree), clean(item.institution),
                                       item.graduation_year))
        if item.thesis_url:
            entry.append(" %s" % link(item.thesis_url))
        lines.append(r'\cvplainentry{%s}' % "".join(entry))
    return lines


def _surname_first(profile):
    """"Hans Riess" -> "Riess, Hans", the form the thesis entry uses."""
    parts = profile.name_parts()
    if len(parts) < 2:
        return profile.plain_name()
    return "%s, %s" % (parts[-1], " ".join(parts[:-1]))


def _publications_block(profile):
    """Section I.B, merging Reference and Talk rows into six subsections.

    References are filtered by status unless the profile says to show all. A talk
    that links a reference which is itself listed here is dropped, so a paper and
    the talk announcing it are not both cited.
    """
    show_all = profile.cv_show_all_references
    grouped = {key: [] for key in GT_PUB_CATEGORY_ORDER}

    listed_reference_ids = set()
    for ref in Reference.objects.all():
        if not ref.show_on_cv(show_all):
            continue
        category = ref.get_gt_category()
        if category in grouped:
            grouped[category].append((ref.cv_sort_key(), ref))
            listed_reference_ids.add(ref.pk)

    for talk in Talk.objects.all():
        if talk.reference_id and talk.reference_id in listed_reference_ids:
            continue
        category = talk.get_gt_category()
        if category in grouped:
            grouped[category].append((talk.cv_sort_key(), talk))

    if not any(grouped.values()):
        return []

    lines = [r'\cvsubsection{Publications, Presentations, Posters}']
    for key in GT_PUB_CATEGORY_ORDER:
        entries = grouped[key]
        if not entries:
            continue
        lines.append(r'\cvsubsubsection{%s}' % clean(GT_PUB_CATEGORY_LABELS[key]))
        for _, obj in sorted(entries, key=lambda pair: pair[0], reverse=True):
            if isinstance(obj, Reference):
                body = format_reference(obj, profile)
            else:
                body = format_talk(obj, profile)
            lines.append(r'\cventryitem{%s%s}' % (label_for(obj), body))
    return lines


def _delivered_products_block():
    products = DeliveredProduct.objects.all()
    if not products.exists():
        return []

    lines = [r'\cvsubsection{Key Delivered Products}']
    for product in products:
        lines.append(r'\cvsubsubsection{%s}' % clean(product.get_cv_heading()))
        if product.cv_ref_slug:
            lines.append(label_for(product))
        sponsor_bits = []
        if product.sponsor:
            sponsor_bits.append(clean(product.sponsor))
        if product.date_range:
            sponsor_bits.append("Date range for work performed by the candidate: %s"
                                % clean(product.date_range))
        if sponsor_bits:
            lines.append(r'\cventryitem{\cvlabelled{Sponsor/to whom delivered}{%s}}'
                         % ". ".join(sponsor_bits))
        for caption, value in (("Product description", product.description),
                               ("Current maturity", product.maturity),
                               ("Candidate's technical contribution", product.technical_contribution)):
            if value:
                lines.append(r'\cventryitem{\cvlabelled{%s}{%s}}'
                             % (clean(caption), " ".join(paragraphs(value))))
    return lines


def _awards_block(profile):
    awards = Award.objects.all()
    if not awards.exists():
        return []

    lines = [r'\cvsubsection{Professional Research Recognition Awards}']
    for award in awards:
        when = datetime.date(award.year, 12, 31) if award.year else None
        entry = [marker_prefix(award, profile, when)]
        entry.append(r'\textbf{%s}' % clean(award.title))
        tail = [bit for bit in (clean(award.organization), clean(award.get_cv_date())) if bit]
        if tail:
            entry.append(", " + ", ".join(tail))
        entry.append(".")
        if award.detail:
            entry.append(r' \textit{(%s)}' % clean(award.detail.strip().rstrip('.')))
        lines.append(r'\cvplainentry{%s}' % "".join(entry))
    return lines


def _knowledge_sharing_block(profile):
    """Section I.E, from courses taught plus tutorial and workshop presentations."""
    rows = []
    for course in Course.objects.all():
        when = datetime.date(course.year, 12, 31) if course.year else None
        rows.append((when, [
            clean(course.get_cv_organization()),
            clean(course.get_cv_when_taught()),
            clean(course.get_cv_title()),
            clean(course.get_cv_role()),
            clean(course.attendee_count),
        ], is_pre_gt(course, profile, when)))

    for talk in Talk.objects.all():
        if not talk.is_knowledge_sharing():
            continue
        rows.append((talk.date, [
            clean(talk.venue),
            talk.date.strftime('%B %Y') if talk.date else "",
            "%s (%s)" % (clean(talk.title), clean(talk.get_talk_type_display())),
            clean(talk.curriculum_role) or clean(talk.get_talk_type_display()),
            clean(talk.attendee_count),
        ], is_pre_gt(talk, profile, talk.date)))

    if not rows:
        return []

    rows.sort(key=lambda row: row[0] or datetime.date.min, reverse=True)
    lines = [r'\cvsubsection{Knowledge Sharing}', r'\begin{cvteachtable}']
    for _, cells, pre_gt in rows:
        cells = list(cells)
        if pre_gt:
            cells[0] = "*" + cells[0]
        lines.append(r'\cvteachrow{%s}{%s}{%s}{%s}{%s}' % tuple(cells))
    lines.append(r'\end{cvteachtable}')
    return lines


# --- Section II --------------------------------------------------------------

def build_section_ii():
    blocks = [_reports_block(), _innovations_block()]
    body = [line for block in blocks for line in block]
    if not body:
        return []
    return [r'\cvsection{Technical Contributions and Innovation}'] + body


def _reports_block():
    """Section II.A: one numbered report series per award that has reports."""
    grants = [g for g in Grant.objects.all() if g.tech_reports.exists()]
    if not grants:
        return []

    lines = [r'\cvsubsection{Research/Technical Reports}']
    for grant in grants:
        heading = "%s — Technical Report Series." % (grant.short_title or grant.title)
        preamble = " ".join(paragraphs(grant.report_series_note))
        lines.append(r'\cvsubsubrun{%s}{%s}' % (clean(heading), preamble))
        for report in grant.tech_reports.all():
            bits = [r'\textbf{%s}.' % clean(report.title)]
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
            lines.append(r'\cventryitem{%s%s}' % (label_for(report), "".join(bits)))
    return lines


def _innovations_block():
    innovations = Innovation.objects.all()
    if not innovations.exists():
        return []

    lines = [r'\cvsubsection{Significant Technical Innovation and/or Contributions on Sponsored Programs}']
    for innovation in innovations:
        lines.append(r'\cvsubsubrun{%s}{}' % clean(innovation.title))
        if innovation.cv_ref_slug:
            lines.append(label_for(innovation))
        sponsors = innovation.get_sponsors_line()
        if sponsors:
            lines.append(r'\cvbody{\cvlabelled{Sponsors/Projects/Dates}{%s}}'
                         % clean(sponsors))
        for caption, value in (("Description", innovation.description),
                               ("Candidate's specific technical contributions",
                                innovation.technical_contributions)):
            for index, block in enumerate(paragraphs(value)):
                if index == 0:
                    lines.append(r'\cvbody{\cvlabelled{%s}{%s}}' % (clean(caption), block))
                else:
                    lines.append(r'\cvbody{%s}' % block)
    return lines


# --- Section III -------------------------------------------------------------

def build_section_iii(profile):
    blocks = [_funded_research_block(profile), _student_guidance_block()]
    body = [line for block in blocks for line in block]
    if not body:
        return []
    return [r'\cvsection{Project Leadership and Supervision}'] + body


def _funded_research_block(profile):
    grants = Grant.objects.all()
    if not grants.exists():
        return []

    lines = [
        r'\cvsubsection{Leadership in Funded Research}',
        r'\cvsubsubsection{Externally Sponsored Programs for which the Candidate Served in a Leadership Role}',
    ]
    for grant in grants:
        lines.append(r'\cvitemhead{%s%s}' % (label_for(grant), clean(grant.title)))
        lines.append(r'\begin{cvkeytable}')
        rows = [
            ("Title", clean(grant.title)),
            ("Contract Number", clean(grant.grant_number)),
            ("Sponsor", clean(grant.funding_agency)),
            ("P.I.", _pi_cell(grant, profile)),
            ("Candidate's Role", clean(grant.get_cv_role())),
            ("Task Title", clean(grant.task_title)),
            ("Amount Funded for Project", clean(grant.get_cv_amount())),
            ("Period of Performance", clean(grant.get_period_of_performance())),
            ("Contributions", r' \par '.join(paragraphs(grant.contributions))),
        ]
        lines.extend(_key_rows(rows))
        lines.append(r'\end{cvkeytable}')
    return lines


def _proposals_block(profile):
    proposals = Proposal.objects.all()
    if not proposals.exists():
        return []

    lines = [
        r'\cvsubsection{Research Proposals}',
        r'\cvsubsubsection{External Proposals to Sponsors}',
    ]
    for proposal in proposals:
        lines.append(r'\cvitemhead{%s%s}' % (label_for(proposal), clean(proposal.title)))
        lines.append(r'\begin{cvkeytable}')
        rows = [
            ("Title", clean(proposal.title)),
            ("Sponsor", clean(proposal.sponsor)),
            ("Solicitation", clean(proposal.solicitation)),
            ("PI", _pi_cell(proposal, profile)),
            ("Candidate's Role", clean(proposal.candidate_role)),
            ("Date Submitted", _submission_cell(proposal)),
            ("Amount Requested", clean(proposal.get_cv_amount())),
            ("Result", clean(proposal.get_result())),
            ("Period of Performance", clean(proposal.get_period_of_performance())),
            ("Contribution to Proposal", r' \par '.join(paragraphs(proposal.contribution))),
        ]
        lines.extend(_key_rows(rows))
        lines.append(r'\end{cvkeytable}')
    return lines


def _key_rows(rows):
    """Emit only the rows that have a value, so tables stay tight."""
    return [r'\cvkeyrow{%s}{%s}' % (clean(label), value) for label, value in rows if value]


def _pi_cell(grant, profile):
    if grant.pi_name:
        return r' \par '.join(clean(line) for line in grant.pi_name.splitlines() if line.strip())
    return clean(profile.plain_name())


def _submission_cell(proposal):
    bits = []
    if proposal.date_abstract_submitted:
        bits.append("Abstract: %s" % proposal.date_abstract_submitted.strftime('%B %-d, %Y'))
    if proposal.full_proposal_note:
        bits.append("Full Proposal: %s" % clean(proposal.full_proposal_note))
    elif proposal.date_full_submitted:
        bits.append("Full Proposal: %s" % proposal.date_full_submitted.strftime('%B %-d, %Y'))
    return r' \par '.join(bits)


def _student_guidance_block():
    students = Student.objects.order_by('-start_date')
    if not students.exists():
        return []

    lines = [
        r'\cvsubsection{Individual Student Guidance/Development}',
        r'\cvsubsubsection{Graduate Research Assistants, Student Assistants, and/or Co-op Students '
        r'Trained/Supervised}',
    ]
    for student in students:
        bits = ["%s, %s student, %s." % (clean(student.name),
                                         clean(student.get_level_display()),
                                         clean(student.institution))]
        appointment = [clean(student.appointment_note)] if student.appointment_note else []
        appointment.append(student.get_date_range())
        bits.append(" %s." % ", ".join(part for part in appointment if part))

        topic = student.research_topic or student.project_title
        if topic:
            bits.append(" Research topic: %s." % clean(topic.rstrip('.')))
        publications = list(student.resulting_publications.all())
        refs = [p.cv_ref_slug for p in publications if p.cv_ref_slug]
        if refs:
            joined = ", ".join(r'\ref{cv:%s}' % slug for slug in refs)
            bits.append(" Resulting publication: see %s." % joined)
        if student.advisor_of_record:
            bits.append(" Advisor of record: %s." % clean(student.advisor_of_record.rstrip('.')))
        if student.host_lab:
            bits.append(" Host lab: %s." % clean(student.host_lab.rstrip('.')))
        if student.current_position:
            bits.append(" Current position: %s." % clean(student.current_position.rstrip('.')))
        lines.append(r'\cventryitem{%s}' % "".join(bits))
    return lines


# --- Section IV --------------------------------------------------------------

def build_section_iv(profile):
    blocks = [_research_program_block(profile), _proposals_block(profile)]
    body = [line for block in blocks for line in block]
    if not body:
        return []
    return [r'\cvsection{Sponsored Program Development}'] + body


def _research_program_block(profile):
    blocks = paragraphs(profile.research_program)
    if not blocks:
        return []
    lines = [r'\cvsubsection{Research Program Development}']
    lines.extend(r'\cvnarrative{%s}' % block for block in blocks)
    return lines


# --- Section V ---------------------------------------------------------------

def build_section_v(profile):
    services = list(Service.objects.order_by('-year', 'title'))
    if not services:
        return []

    grouped = {key: [] for key, _ in GT_SERVICE_ORDER}
    for service in services:
        category = service.get_gt_category()
        if category in grouped:
            grouped[category].append(service)

    if not any(grouped.values()):
        return []

    lines = [r'\cvsection{Outreach and Service}']
    for key, heading in GT_SERVICE_ORDER:
        entries = grouped[key]
        if not entries:
            continue
        lines.append(r'\cvsubsection{%s}' % clean(heading))
        for service in entries:
            lines.append(r'\cvplainentry{%s}' % _service_entry(service, profile))
    return lines


def _service_entry(service, profile):
    when = datetime.date(service.year, 12, 31) if service.year else None
    bits = ["*" if is_pre_gt(service, profile, when) else ""]

    lead = [clean(service.get_role_display())]
    if service.title:
        lead.append(clean(service.title))
    lead.append(clean(service.organization))
    if service.location:
        lead.append(clean(service.location))
    lead.append(_service_years(service))
    bits.append(", ".join(part for part in lead if part))

    if service.manuscript_count:
        bits.append(" (%d manuscript%s)" % (service.manuscript_count,
                                            "" if service.manuscript_count == 1 else "s"))
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
    lines.extend(build_header(profile))
    lines.extend(build_section_i(profile))
    lines.extend(build_section_ii())
    lines.extend(build_section_iii(profile))
    lines.extend(build_section_iv(profile))
    lines.extend(build_section_v(profile))
    lines.append(r'\end{document}')
    return "\n".join(line for line in lines if line)
