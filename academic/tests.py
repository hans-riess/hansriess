import datetime
import os
import shutil
import tempfile
from io import StringIO
from unittest import mock

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.core.files.base import ContentFile
from django.core.management import CommandError, call_command
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from academic import cv_builder, views
from academic.models import (Award, Course, Demo, Education, Grant, Profile, Proposal,
                             Reference, Review, Service, Student, Talk, TechReport)


class AdminFormTests(TestCase):
    """Every registered admin must be able to build its change form.

    `manage.py check` does not catch a stale name in `fields`/`fieldsets`: those
    may legitimately refer to form fields rather than model fields, so Django
    only raises when the form is actually constructed — which happens on the
    first request to the change page, in production. A `completed_before_hire`
    left behind in ReferenceAdmin after the field was dropped from the model got
    through exactly that gap, so build every form here instead.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser('admin', 'a@example.com', 'pw')

    def _request(self):
        request = self.factory.get('/admin/')
        request.user = self.user
        return request

    def test_every_admin_builds_its_form(self):
        for model, model_admin in admin.site._registry.items():
            with self.subTest(model=model.__name__):
                model_admin.get_form(self._request())()

    def test_every_inline_builds_its_formset(self):
        request = self._request()
        for model, model_admin in admin.site._registry.items():
            for inline in model_admin.get_inline_instances(request):
                with self.subTest(model=model.__name__, inline=type(inline).__name__):
                    inline.get_formset(request)

    def test_reference_list_says_where_each_paper_lands(self):
        profile = Profile.objects.create(name="Hans Riess")
        preprint = Reference.objects.create(title="P", authors="H. Riess", year=2024,
                                            medium='preprint', status='published')
        column = admin.site._registry[Reference].cv_subsection
        self.assertEqual(column(preprint),
                         "Preprints (hidden: tick 'Show all references' on the profile)")
        profile.cv_show_all_references = True
        profile.save()
        self.assertEqual(column(preprint), "Preprints")
        # A rejected submission left on arXiv is still a Preprint.
        preprint.status = 'rejected'
        self.assertEqual(column(preprint), "Preprints")
        preprint.status = 'in_review'
        self.assertEqual(column(preprint), "Papers Under Review")
        preprint.medium = 'thesis'
        self.assertEqual(column(preprint), "—")

    def test_every_admin_can_render_its_changelist(self):
        request = self._request()
        for model, model_admin in admin.site._registry.items():
            with self.subTest(model=model.__name__):
                model_admin.get_changelist_instance(request)


class ReferenceClassificationTests(TestCase):
    """The publication-list placement and status filter, which are pure derivations."""

    def _reference(self, **kwargs):
        return Reference(title="T", authors="H. Riess", year=2026, **kwargs)

    def test_category_follows_medium_refereed_and_status(self):
        cases = [
            (dict(medium='journal_article', status='published'), 'journal'),
            (dict(medium='journal_article', status='in_review'), 'submitted'),
            (dict(medium='conference_proceedings', refereed=True), 'proc_refereed'),
            (dict(medium='conference_proceedings', refereed=False), 'proc_nonrefereed'),
            (dict(medium='conference_proceedings', status='accepted', refereed=True), 'proc_refereed'),
            (dict(medium='conference_proceedings', status='in_review', refereed=True), 'submitted_conf'),
            (dict(medium='preprint', status='in_review'), 'submitted'),
            (dict(medium='preprint', status='published'), 'preprints'),
            (dict(medium='thesis', status='published'), ''),
            (dict(medium='journal_article', status='rejected'), ''),
            (dict(medium='preprint', status='rejected'), 'preprints'),
        ]
        for kwargs, expected in cases:
            with self.subTest(**kwargs):
                self.assertEqual(self._reference(**kwargs).get_category(), expected)

    def test_status_filter(self):
        # Accepted and published always show; in review only for journals and
        # preprints. Conference submissions and standalone preprints — including
        # one whose submission was rejected — need "show all"; any other
        # rejected work never shows, even with it.
        cases = [
            (dict(medium='journal_article', status='published'), True, True),
            (dict(medium='journal_article', status='accepted'), True, True),
            (dict(medium='journal_article', status='in_review'), True, True),
            (dict(medium='preprint', status='in_review'), True, True),
            (dict(medium='conference_proceedings', status='in_review'), False, True),
            (dict(medium='preprint', status='published'), False, True),
            (dict(medium='journal_article', status='rejected'), False, False),
            (dict(medium='preprint', status='rejected'), False, True),
            (dict(medium='conference_proceedings', status='rejected'), False, False),
        ]
        for kwargs, default, show_all in cases:
            with self.subTest(**kwargs):
                ref = self._reference(**kwargs)
                self.assertIs(ref.show_on_cv(show_all=False), default)
                self.assertIs(ref.show_on_cv(show_all=True), show_all)

    def test_publication_date_orders_within_a_year(self):
        march = self._reference(medium='journal_article', publication_date=datetime.date(2026, 3, 1))
        october = self._reference(medium='journal_article', publication_date=datetime.date(2026, 10, 1))
        self.assertLess(march.cv_sort_key(), october.cv_sort_key())


class TalkClassificationTests(TestCase):
    """A workshop is a venue, not something taught; only a tutorial teaches."""

    def _talk(self, **kwargs):
        return Talk(title="T", venue="V", date=datetime.date(2026, 1, 1), **kwargs)

    def test_workshop_invitation_is_a_conference_presentation(self):
        talk = self._talk(talk_type='workshop', invited=True)
        self.assertFalse(talk.is_knowledge_sharing())
        self.assertEqual(talk.get_category(), 'invited_conf')

    def test_tutorial_is_knowledge_sharing(self):
        self.assertTrue(self._talk(talk_type='tutorial').is_knowledge_sharing())

    def test_uninvited_talks_are_contributed(self):
        for talk_type in ('seminar', 'colloquium', 'guest_lecture', 'webinar', 'poster'):
            with self.subTest(talk_type=talk_type):
                self.assertEqual(self._talk(talk_type=talk_type).get_category(), 'no_proc')

    def test_an_invited_seminar_is_an_invited_talk(self):
        # Job-market CVs count invited seminars and colloquia as invited talks,
        # not only invited conference presentations.
        for talk_type in ('seminar', 'colloquium'):
            with self.subTest(talk_type=talk_type):
                talk = self._talk(talk_type=talk_type, invited=True)
                self.assertEqual(talk.get_category(), 'invited_conf')

    def test_proceedings_only_count_for_conference_talks(self):
        talk = self._talk(talk_type='seminar', invited=True, proceedings=True)
        self.assertEqual(talk.get_category(), 'invited_conf')
        talk = self._talk(talk_type='conference', proceedings=True)
        self.assertEqual(talk.get_category(), 'proc_nonrefereed')


class CvBuilderTests(TestCase):
    """The document builds, and skips sections that have no data."""

    def test_builds_with_only_a_profile(self):
        profile = Profile.objects.create(name="Hans Riess")
        tex = cv_builder.build_document(profile)
        self.assertIn(r'\begin{document}', tex)
        self.assertIn(r'\end{document}', tex)
        # No data, so no numbered sections were emitted.
        self.assertNotIn(r'\cvsection', tex)

    def test_latex_specials_and_cross_references_survive_escaping(self):
        self.assertEqual(cv_builder.clean("100% of A&B"), r"100\% of A\&B")
        self.assertEqual(cv_builder.clean("see [[ref:my-paper]]"), r"see \ref{cv:my-paper}")

    def test_candidate_is_bolded_once_in_an_author_list(self):
        rendered = cv_builder.format_authors("A. Other, B. Third, and H. Riess", "Riess")
        self.assertEqual(rendered.count(r'\textbf{'), 1)
        self.assertIn(r'and \textbf{H. Riess}', rendered)


class SectionBuilderTests(TestCase):
    """Which model feeds which section, and what gets left out."""

    def setUp(self):
        self.profile = Profile.objects.create(name="Hans Riess", institution="Georgia Tech")

    def test_reviews_and_service_split_into_subsections(self):
        Review.objects.create(venue="Automatica", kind='journal_review',
                              year=2026, manuscript_count=1)
        Review.objects.create(venue="Compositionality", kind='editorial_board',
                              role="Associate Editor", year=2026)
        Review.objects.create(venue="Learning on Graphs", kind='conference_review', year=2024)
        Service.objects.create(title="Game Theory session", role='co_chair',
                               organization="CDC", service_type='conference', year=2022)

        lines = cv_builder.build_service(self.profile)
        tex = "\n".join(lines)

        # Editorial work sits with journal reviewing, not with conference work.
        self.assertIn("Editorial Service and Journal Reviewing", tex)
        self.assertIn(r"\textbf{Associate Editor}, Compositionality", tex)
        self.assertIn(r"\textbf{Reviewer}, Automatica, 2026 (1 manuscript)", tex)
        self.assertIn("Conference Reviewing and Program Committees", tex)
        self.assertIn("Conference Organization and Session Chairs", tex)

    def test_service_alone_does_not_emit_review_subsections(self):
        Service.objects.create(title="Seminar", role='organizer',
                               organization="Penn", service_type='seminar', year=2020)
        tex = "\n".join(cv_builder.build_service(self.profile))
        self.assertNotIn("Reviewer", tex)
        self.assertIn("Other Professional Service", tex)

    def test_teaching_merges_courses_and_tutorials(self):
        Course.objects.create(title="Elementary Statistics", course_code="MATH 103",
                              institution="College of Charleston", semester='fall',
                              year=2024, attendee_count="~30")
        Course.objects.create(title="Applied Category Theory", course_format='workshop',
                              institution="ACC", semester='spring', year=2026)
        Talk.objects.create(title="Applied sheaf theory", venue="ACC",
                            talk_type='tutorial', date=datetime.date(2026, 5, 1),
                            attendee_count="~30")
        # A workshop invitation is a presentation, so it must not appear here.
        Talk.objects.create(title="Lattice theory", venue="BIRS", talk_type='workshop',
                            invited=True, date=datetime.date(2023, 2, 1))

        teaching = "\n".join(cv_builder.build_teaching_and_mentoring(self.profile))
        self.assertIn(r"\cvsection{Teaching}", teaching)
        self.assertIn("Elementary Statistics (MATH 103)", teaching)
        self.assertIn("Enrollment: ", teaching)
        self.assertIn("Applied Category Theory (workshop)", teaching)
        self.assertIn("Applied sheaf theory (tutorial)", teaching)
        # The BIRS talk is a presentation, never a teaching entry.
        self.assertNotIn("BIRS", teaching)
        presentations = "\n".join(cv_builder.build_presentations(self.profile))
        self.assertIn("Invited Talks", presentations)
        self.assertIn("BIRS", presentations)
        self.assertNotIn("Applied sheaf theory", presentations)

    def test_teaching_is_newest_first_by_semester(self):
        Course.objects.create(title="Spring course", institution="X", semester='spring', year=2024)
        Course.objects.create(title="Fall course", institution="X", semester='fall', year=2024)
        tex = "\n".join(cv_builder.build_teaching_and_mentoring(self.profile))
        self.assertLess(tex.index("Fall course"), tex.index("Spring course"))

    def test_mentoring_joins_teaching_under_one_heading(self):
        Course.objects.create(title="Elementary Statistics", institution="X",
                              semester='fall', year=2024)
        Student.objects.create(name="Nivar Anwer", level='masters', institution="Georgia Tech",
                               start_date=datetime.date(2026, 4, 1))
        tex = "\n".join(cv_builder.build_teaching_and_mentoring(self.profile))
        self.assertIn(r"\cvsection{Teaching and Mentoring}", tex)
        self.assertIn(r"\cvsubsection{Student Mentoring}", tex)

    def test_a_talk_linked_to_a_listed_paper_is_not_cited_twice(self):
        paper = Reference.objects.create(
            title="Quantale-enriched co-design", authors="H. Riess", year=2026,
            medium='conference_proceedings', refereed=True, status='published',
            journal="Proc. CDC")
        Talk.objects.create(title="Quantale-enriched co-design", venue="CDC",
                            talk_type='conference', proceedings=True,
                            date=datetime.date(2026, 12, 1), reference=paper)

        tex = "\n".join(cv_builder.build_publications(self.profile)
                        + cv_builder.build_presentations(self.profile))
        self.assertEqual(tex.count("Quantale-enriched co-design"), 1)

    def test_conference_submissions_and_preprints_need_show_all(self):
        Reference.objects.create(
            title="Sheaf coordination", authors="H. Riess", year=2027,
            medium='conference_proceedings', refereed=True, status='in_review',
            journal="Proc. CDC", arxiv_id="2701.00001")
        Reference.objects.create(
            title="Lattice diffusion", authors="H. Riess", year=2024,
            medium='preprint', status='rejected', journal="Proc. ICASSP",
            arxiv_id="2401.00001")

        tex = "\n".join(cv_builder.build_publications(self.profile))
        self.assertNotIn("Sheaf coordination", tex)
        self.assertNotIn("Lattice diffusion", tex)

        self.profile.cv_show_all_references = True
        tex = "\n".join(cv_builder.build_publications(self.profile))
        # A submission is not listed among the accepted proceedings.
        self.assertNotIn("Conference Proceedings", tex)
        submitted = tex[tex.index("Papers Under Review"):tex.index("Preprints")]
        self.assertIn("Sheaf coordination", submitted)
        self.assertIn(r"Submitted to \textit{Proc. CDC}", submitted)
        preprints = tex[tex.index("Preprints"):]
        self.assertIn("Lattice diffusion", preprints)
        self.assertIn("arXiv:2401.00001, 2024.", preprints)
        # The venue that turned it down is never named.
        self.assertNotIn("ICASSP", tex)

    def test_journal_and_conference_submissions_share_a_subsection(self):
        self.profile.cv_show_all_references = True
        Reference.objects.create(title="Journal submission", authors="H. Riess", year=2026,
                                 medium='journal_article', status='in_review', journal="TAC")
        Reference.objects.create(title="Conference submission", authors="H. Riess", year=2027,
                                 medium='conference_proceedings', status='in_review',
                                 journal="CDC")
        tex = "\n".join(cv_builder.build_publications(self.profile))
        self.assertEqual(tex.count("Papers Under Review"), 1)
        self.assertIn(r"\cvcite{S2}{\textbf{H. Riess}, ``Conference submission", tex)
        self.assertIn(r"\cvcite{S1}{\textbf{H. Riess}, ``Journal submission", tex)

    def test_empty_sections_are_skipped(self):
        for build in (cv_builder.build_interests, cv_builder.build_education,
                      cv_builder.build_appointments, cv_builder.build_sponsored_research,
                      cv_builder.build_teaching_and_mentoring, cv_builder.build_publications,
                      cv_builder.build_presentations, cv_builder.build_service):
            with self.subTest(build=build.__name__):
                self.assertEqual(build(self.profile), [])
        self.assertEqual(cv_builder.build_technical_contributions(), [])
        self.assertEqual(cv_builder.build_awards(), [])

    def test_funded_awards_and_proposals_are_listed_apart(self):
        Grant.objects.create(title="SEAMAN", funding_agency="DARPA", role='pi',
                             amount=180687, grant_number="HR0011-25-3-0235")
        tex = "\n".join(cv_builder.build_sponsored_research(self.profile))
        self.assertIn("Funded Projects", tex)
        self.assertIn("$180,687", tex)
        self.assertIn("Role: Principal Investigator.", tex)
        # The candidate is PI of record by default, which the role already says.
        self.assertNotIn("PI:", tex)
        # No proposals exist, so that subsection stays out.
        self.assertNotIn("Proposals", tex)

        Proposal.objects.create(title="ARGUS", sponsor="DARPA", amount_requested=2100000,
                                date_abstract_submitted=datetime.date(2026, 6, 30))
        tex = "\n".join(cv_builder.build_sponsored_research(self.profile))
        self.assertIn(r"\cvsubsection{Proposals}", tex)
        self.assertIn(r"\cventry{PR1}{\textbf{ARGUS}}{Jun 2026}", tex)
        self.assertIn(r"Amount requested: \$2,100,000.", tex)

    def test_dissertation_is_listed_under_its_degree(self):
        Education.objects.create(degree_type="Ph.D.", field_of_study="ESE",
                                 institution="Penn", graduation_year=2022,
                                 thesis_title="Lattice Theory in Multi-Agent Systems",
                                 advisor="Robert Ghrist", is_dissertation=True)
        tex = "\n".join(cv_builder.build_education(self.profile))
        self.assertIn("Dissertation: ``Lattice Theory in Multi-Agent Systems.''", tex)
        self.assertIn("Advisor: Robert Ghrist.", tex)


class CvLayoutTests(TestCase):
    """The job-market layout: section order, numbering, and no colour."""

    def setUp(self):
        self.profile = Profile.objects.create(name="Hans Riess, Ph.D.",
                                              email="hans@example.com",
                                              website="https://hansriess.com/")

    def test_sponsored_research_and_teaching_come_before_publications(self):
        Grant.objects.create(title="SEAMAN", funding_agency="DARPA", role='pi')
        Course.objects.create(title="Statistics", institution="X", semester='fall', year=2024)
        Reference.objects.create(title="A paper", authors="H. Riess", year=2024,
                                 medium='journal_article', journal="TAC")
        Talk.objects.create(title="A talk", venue="V", talk_type='seminar', invited=True,
                            date=datetime.date(2025, 1, 1))
        tex = cv_builder.build_document(self.profile)
        order = [tex.index(r'\cvsection{%s}' % name) for name in
                 ("Sponsored Research", "Teaching", "Publications", "Presentations")]
        self.assertEqual(order, sorted(order))

    def test_header_is_the_plain_name_with_contact_details(self):
        tex = "\n".join(cv_builder.build_header(self.profile))
        self.assertIn(r'\cvname{Hans Riess}', tex)
        self.assertIn(r'\href{mailto:hans@example.com}{hans@example.com}', tex)
        self.assertIn(r'\href{https://hansriess.com/}{hansriess.com}', tex)

    def test_numbers_count_down_and_proceedings_share_a_series(self):
        for year, refereed in ((2022, True), (2024, True), (2026, False)):
            Reference.objects.create(title="Paper %d" % year, authors="H. Riess", year=year,
                                     medium='conference_proceedings', refereed=refereed,
                                     journal="Proc. %d" % year)
        tex = "\n".join(cv_builder.build_publications(self.profile))
        # Refereed proceedings print first, so they take the higher numbers even
        # though the non-refereed paper is newer.
        self.assertIn(r'\cvcite{C3}{\textbf{H. Riess}, ``Paper 2024', tex)
        self.assertIn(r'\cvcite{C2}{\textbf{H. Riess}, ``Paper 2022', tex)
        self.assertIn(r'\cvcite{C1}{\textbf{H. Riess}, ``Paper 2026', tex)

    def test_cross_references_point_at_the_numbered_entry(self):
        Reference.objects.create(title="A paper", authors="H. Riess", year=2024,
                                 medium='journal_article', journal="TAC",
                                 cv_ref_slug="a-paper")
        tex = "\n".join(cv_builder.build_publications(self.profile))
        self.assertIn(r'\cvcite{J1}{\label{cv:a-paper}', tex)

    def test_marker_key_only_names_markers_in_use(self):
        Reference.objects.create(title="A paper", authors="H. Riess", year=2024,
                                 medium='journal_article', alphabetical_order=True)
        tex = "\n".join(cv_builder.build_publications(self.profile))
        self.assertIn("Authors listed alphabetically", tex)
        self.assertNotIn("Shared first authorship", tex)

    def test_style_file_uses_no_colour(self):
        path = os.path.join(os.path.dirname(cv_builder.__file__), 'tex', 'academic-cv.sty')
        with open(path, encoding='utf-8') as sty:
            source = sty.read()
        self.assertNotIn('xcolor', source)
        self.assertNotIn(r'\color', source)
        self.assertNotIn(r'\definecolor', source)


class CvDownloadTests(TestCase):
    """/cv/ rebuilds on demand, busts caches, and honours the custom override."""

    def setUp(self):
        self.profile = Profile.objects.create(name="Hans Riess")
        self.url = reverse('cv_redirect')

    def _fake_build(self, *args, **kwargs):
        """Stand in for the management command so the tests need no LaTeX."""
        self.profile.refresh_from_db()
        self.profile.cv.save('cv.pdf', ContentFile(b'%PDF-1.4 generated'), save=True)

    def test_regenerates_before_redirecting(self):
        with mock.patch('academic.views.call_command', side_effect=self._fake_build) as build:
            response = self.client.get(self.url)
        build.assert_called_once_with('generate_cv')
        self.assertEqual(response.status_code, 302)
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.cv)

    def test_redirect_is_cache_busted_and_not_cacheable(self):
        with mock.patch('academic.views.call_command', side_effect=self._fake_build):
            response = self.client.get(self.url)
        self.assertIn('?v=', response['Location'])
        self.assertIn('no-store', response['Cache-Control'])

    def test_a_build_failure_still_serves_the_stored_copy(self):
        self.profile.cv.save('cv.pdf', ContentFile(b'%PDF-1.4 stale'), save=True)
        with mock.patch('academic.views.call_command', side_effect=OSError("pdflatex exploded")):
            # assertLogs both asserts the failure was logged and keeps the
            # expected traceback out of the test output.
            with self.assertLogs('academic.views', level='ERROR'):
                response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_custom_cv_is_served_and_never_regenerated_over(self):
        self.profile.custom_cv.save('mine.pdf', ContentFile(b'%PDF-1.4 custom'), save=True)
        self.profile.use_custom_cv = True
        self.profile.save()
        with mock.patch('academic.views.call_command') as build:
            response = self.client.get(self.url)
        build.assert_not_called()
        self.assertEqual(response.status_code, 302)
        self.assertIn('mine', response['Location'])

    def test_no_cv_at_all_is_a_404(self):
        self.profile.use_custom_cv = True
        self.profile.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)


class CvButtonTests(TestCase):
    """The button no longer depends on a placeholder file being uploaded."""

    def setUp(self):
        self.profile = Profile.objects.create(name="Hans Riess")

    def test_shown_with_no_stored_file(self):
        self.assertTrue(self.profile.show_cv_button())

    def test_hidden_when_explicitly_turned_off(self):
        self.profile.cv_button = False
        self.assertFalse(self.profile.show_cv_button())

    def test_custom_mode_needs_an_uploaded_file(self):
        self.profile.use_custom_cv = True
        self.assertFalse(self.profile.show_cv_button())


class MigrationStateTests(TestCase):
    """The models and the migrations must not drift apart."""

    def test_no_migrations_are_missing(self):
        try:
            call_command('makemigrations', 'academic', check=True, dry_run=True,
                         stdout=StringIO(), stderr=StringIO())
        except SystemExit:
            self.fail("Model changes are not captured in a migration; "
                      "run manage.py makemigrations academic.")
        except CommandError as exc:
            self.fail(f"makemigrations --check failed: {exc}")


class EntryEmphasisTests(TestCase):
    """Every entry leads with its identifier in bold.

    Awards and technical reports already did; students and Section V entries did
    not, which read inconsistently against the rest of the document.
    """

    def setUp(self):
        self.profile = Profile.objects.create(name="Hans Riess")

    def test_student_names_are_bold(self):
        Student.objects.create(name="Nivar Anwer", level='masters',
                               institution="Georgia Tech",
                               start_date=datetime.date(2026, 4, 1))
        tex = "\n".join(cv_builder.build_teaching_and_mentoring(self.profile))
        self.assertIn(r'\textbf{Nivar Anwer}', tex)

    def test_review_and_service_roles_are_bold(self):
        Review.objects.create(venue="Automatica", kind='journal_review', year=2026)
        Review.objects.create(venue="Compositionality", kind='editorial_board',
                              role="Associate Editor", year=2026)
        Service.objects.create(title="GRASP Seminar", role='organizer',
                               organization="Penn", service_type='seminar', year=2020)
        tex = "\n".join(cv_builder.build_service(self.profile))
        self.assertIn(r'\textbf{Reviewer}, Automatica', tex)
        self.assertIn(r'\textbf{Associate Editor}, Compositionality', tex)
        self.assertIn(r'\textbf{Organizer}, GRASP Seminar', tex)

    def test_awards_and_reports_keep_their_bold(self):
        Award.objects.create(title="Leggett Family Fellowship",
                             organization="Penn", year=2017)
        grant = Grant.objects.create(title="SEAMAN", funding_agency="DARPA", role='pi')
        TechReport.objects.create(grant=grant, title="Milestone 3",
                                  report_type='interim_report',
                                  date=datetime.date(2026, 5, 1))
        awards = "\n".join(cv_builder.build_awards())
        reports = "\n".join(cv_builder.build_technical_contributions())
        self.assertIn(r'\textbf{Leggett Family Fellowship}', awards)
        self.assertIn(r'\textbf{Milestone 3}', reports)


class SheafDemoTests(TestCase):
    """The coordination sheaf demo's markup, assets and standalone page.

    These are the first tests in the suite that render the landing page, which
    needs a headshot: `index.html` reaches for `{{ profile.headshot.url }}`
    unguarded, and `FieldFile.url` raises `ValueError` on an empty field --
    something Django's template variable resolution does *not* swallow.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Otherwise every run drops another headshot into the developer's media/.
        media = tempfile.mkdtemp()
        cls.addClassCleanup(shutil.rmtree, media, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media)
        override.enable()
        cls.addClassCleanup(override.disable)

    def setUp(self):
        self.profile = Profile.objects.create(name="Hans Riess")
        self.profile.headshot.save('headshot.png', ContentFile(b'x'), save=True)

    def test_launcher_sits_beside_the_cv_button(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'id="sheaf-demo-open"')
        self.assertContains(response, 'href="#sheaf-demo"')

    def test_demo_assets_carry_a_cache_buster(self):
        """S3 serves these with max-age=86400 and does not hash filenames, so an
        edited asset without a fresh token is invisible for a day."""
        response = self.client.get(reverse('index'))
        content = response.content.decode()
        self.assertIn(f'js/sheaf-demo.js?v={views.DEMO_ASSET_VERSION}', content)
        self.assertIn(f'css/sheaf-demo.css?v={views.DEMO_ASSET_VERSION}', content)

    def test_the_panel_stays_outside_the_page_wrapper(self):
        """`#page-wrapper` opens before the header and closes right after the
        title section, with a second closing div after the footer. The panel is
        `position: fixed`, so it only escapes that tangle by being a direct child
        of <body>; tidying it back inside would put it in a containing block."""
        content = self.client.get(reverse('index')).content.decode()
        self.assertGreater(content.index('id="sheaf-demo"'), content.index('id="footer"'))

    def test_static_assets_are_findable(self):
        """Catches a typo'd path or a file left out of a commit, which would
        otherwise surface only as a 404 in production."""
        self.assertIsNotNone(finders.find('js/sheaf-demo.js'))
        self.assertIsNotNone(finders.find('css/sheaf-demo.css'))

    def test_standalone_page_renders(self):
        response = self.client.get(reverse('demo'))
        self.assertContains(response, 'data-sheaf="view"')
        self.assertContains(response, 'sheaf-demo--page')

    def test_standalone_page_needs_no_database(self):
        """The demo is entirely client-side, so it should cost no query and keep
        working if the database is unreachable."""
        with self.assertNumQueries(0):
            self.client.get(reverse('demo'))

    def test_slugged_standalone_page_renders_the_same_demo(self):
        """/demo/coordination-sheaf/ is the explicit form of the /demo/ shorthand."""
        response = self.client.get(reverse('demo_slug', args=['coordination-sheaf']))
        self.assertContains(response, 'data-sheaf="view"')
        self.assertContains(response, 'sheaf-demo--page')

    def test_slugged_standalone_page_needs_no_database(self):
        """The slug is resolved against a static registry, not the Demo model, so
        this keeps the same zero-query guarantee as the unslugged /demo/."""
        with self.assertNumQueries(0):
            self.client.get(reverse('demo_slug', args=['coordination-sheaf']))

    def test_unknown_demo_slug_404s(self):
        response = self.client.get(reverse('demo_slug', args=['no-such-demo']))
        self.assertEqual(response.status_code, 404)

    def test_overlay_starts_inert(self):
        """Until it is opened the panel must stay out of the tab order and the
        accessibility tree."""
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'inert')
        self.assertContains(response, 'aria-expanded="false"')

    def test_teaser_uses_the_demo_record_copy(self):
        """The landing page's title/blurb/note come from the Demo row, not from
        markup baked into the template."""
        demo = Demo.objects.get(slug='coordination-sheaf')
        demo.title = 'Custom Demo Title'
        demo.blurb = 'Custom blurb text.'
        demo.save()
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Custom Demo Title')
        self.assertContains(response, 'Custom blurb text.')

    def test_switching_the_demo_off_hides_the_teaser(self):
        """Toggling Demo.is_active off in the admin removes the launcher (and
        the panel it would open) from the landing page entirely."""
        Demo.objects.filter(slug='coordination-sheaf').update(is_active=False)
        response = self.client.get(reverse('index'))
        self.assertNotContains(response, 'id="sheaf-demo-open"')
