import datetime
from io import StringIO
from unittest import mock

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management import CommandError, call_command
from django.test import RequestFactory, TestCase
from django.urls import reverse

from academic import cv_builder
from academic.models import (Award, Course, Grant, Profile, Reference, Review,
                             Service, Student, Talk, TechReport)


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

    def test_every_admin_can_render_its_changelist(self):
        request = self._request()
        for model, model_admin in admin.site._registry.items():
            with self.subTest(model=model.__name__):
                model_admin.get_changelist_instance(request)


class ReferenceClassificationTests(TestCase):
    """The Section I.B placement and status filter, which are pure derivations."""

    def _reference(self, **kwargs):
        return Reference(title="T", authors="H. Riess", year=2026, **kwargs)

    def test_category_follows_medium_refereed_and_status(self):
        cases = [
            (dict(medium='journal_article', status='published'), 'journal'),
            (dict(medium='journal_article', status='in_review'), 'submitted'),
            (dict(medium='conference_proceedings', refereed=True), 'proc_refereed'),
            (dict(medium='conference_proceedings', refereed=False), 'proc_nonrefereed'),
            (dict(medium='preprint', status='in_review'), 'submitted'),
            (dict(medium='preprint', status='published'), ''),
            (dict(medium='thesis', status='published'), ''),
            (dict(medium='journal_article', status='rejected'), ''),
        ]
        for kwargs, expected in cases:
            with self.subTest(**kwargs):
                self.assertEqual(self._reference(**kwargs).get_category(), expected)

    def test_status_filter(self):
        # Accepted and published always show; in review only for journals and
        # preprints; rejected never, even with "show all".
        cases = [
            (dict(medium='journal_article', status='published'), True, True),
            (dict(medium='journal_article', status='accepted'), True, True),
            (dict(medium='journal_article', status='in_review'), True, True),
            (dict(medium='conference_proceedings', status='in_review'), False, True),
            (dict(medium='journal_article', status='rejected'), False, False),
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

    def test_non_conference_lands_without_proceedings(self):
        for talk_type in ('seminar', 'colloquium', 'guest_lecture', 'webinar'):
            with self.subTest(talk_type=talk_type):
                self.assertEqual(self._talk(talk_type=talk_type).get_category(), 'no_proc')


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

    def test_reviews_and_service_split_section_v(self):
        Review.objects.create(venue="Automatica", kind='journal_review',
                              year=2026, manuscript_count=1)
        Review.objects.create(venue="Compositionality", kind='editorial_board',
                              role="Associate Editor", year=2026)
        Review.objects.create(venue="Learning on Graphs", kind='conference_review', year=2024)
        Service.objects.create(title="Game Theory session", role='co_chair',
                               organization="CDC", service_type='conference', year=2022)

        lines = cv_builder.build_section_v(self.profile)
        tex = "\n".join(lines)

        # Editorial work sits with journal reviewing, not with conference work.
        self.assertIn("Reviewer and Editorial Work for Technical Journals", tex)
        self.assertIn(r"\textbf{Associate Editor}, Compositionality", tex)
        self.assertIn(r"\textbf{Reviewer}, Automatica, 2026 (1 manuscript)", tex)
        self.assertIn("Reviewer Work for Conferences", tex)
        self.assertIn("Conference Session Chairs", tex)

    def test_service_alone_does_not_emit_review_subsections(self):
        Service.objects.create(title="Seminar", role='organizer',
                               organization="Penn", service_type='seminar', year=2020)
        tex = "\n".join(cv_builder.build_section_v(self.profile))
        self.assertNotIn("Reviewer", tex)
        self.assertIn("Special Activities", tex)

    def test_knowledge_sharing_merges_courses_and_tutorials(self):
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

        tex = "\n".join(cv_builder.build_section_i(self.profile))
        self.assertIn("Knowledge Sharing", tex)
        self.assertIn("Elementary Statistics (MATH 103)", tex)
        self.assertIn("Applied Category Theory (workshop)", tex)
        self.assertIn("Applied sheaf theory (tutorial)", tex)
        self.assertIn("Invited Conference Presentations", tex)
        # The BIRS talk is a citation, never a row in the teaching table.
        teaching = tex[tex.index("Knowledge Sharing"):]
        self.assertNotIn("BIRS", teaching)

    def test_a_talk_linked_to_a_listed_paper_is_not_cited_twice(self):
        paper = Reference.objects.create(
            title="Quantale-enriched co-design", authors="H. Riess", year=2026,
            medium='conference_proceedings', refereed=True, status='published',
            journal="Proc. CDC")
        Talk.objects.create(title="Quantale-enriched co-design", venue="CDC",
                            talk_type='conference', proceedings=True,
                            date=datetime.date(2026, 12, 1), reference=paper)

        tex = "\n".join(cv_builder.build_section_i(self.profile))
        self.assertEqual(tex.count("Quantale-enriched co-design"), 1)

    def test_empty_sections_are_skipped(self):
        self.assertEqual(cv_builder.build_section_ii(), [])
        self.assertEqual(cv_builder.build_section_iii(self.profile), [])
        self.assertEqual(cv_builder.build_section_v(self.profile), [])

    def test_funded_awards_and_proposals_go_to_different_sections(self):
        Grant.objects.create(title="SEAMAN", funding_agency="DARPA", role='pi',
                             amount=180687, grant_number="HR0011-25-3-0235")
        tex = "\n".join(cv_builder.build_section_iii(self.profile))
        self.assertIn("Leadership in Funded Research", tex)
        self.assertIn("$180,687", tex)
        # No proposals exist, so Section IV stays empty.
        self.assertEqual(cv_builder.build_section_iv(self.profile), [])


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
        tex = "\n".join(cv_builder.build_section_iii(self.profile))
        self.assertIn(r'\textbf{Nivar Anwer}', tex)

    def test_review_and_service_roles_are_bold(self):
        Review.objects.create(venue="Automatica", kind='journal_review', year=2026)
        Review.objects.create(venue="Compositionality", kind='editorial_board',
                              role="Associate Editor", year=2026)
        Service.objects.create(title="GRASP Seminar", role='organizer',
                               organization="Penn", service_type='seminar', year=2020)
        tex = "\n".join(cv_builder.build_section_v(self.profile))
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
        section_i = "\n".join(cv_builder.build_section_i(self.profile))
        section_ii = "\n".join(cv_builder.build_section_ii())
        self.assertIn(r'\textbf{Leggett Family Fellowship}', section_i)
        self.assertIn(r'\textbf{Milestone 3}', section_ii)
