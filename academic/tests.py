from django.contrib import admin
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from academic import cv_builder
from academic.models import Profile, Reference, Talk


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
        import datetime
        march = self._reference(medium='journal_article', publication_date=datetime.date(2026, 3, 1))
        october = self._reference(medium='journal_article', publication_date=datetime.date(2026, 10, 1))
        self.assertLess(march.cv_sort_key(), october.cv_sort_key())


class TalkClassificationTests(TestCase):
    """A workshop is a venue, not something taught; only a tutorial teaches."""

    def _talk(self, **kwargs):
        import datetime
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
