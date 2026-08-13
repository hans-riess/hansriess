"""Seed Reference.medium/refereed/status from what reference_type implied.

Section I.B used to be placed by an explicit `gt_category`; it is now derived
from medium + refereed + status. This backfills the new fields so existing rows
keep landing in the subsections they were already printed in, with nothing to
re-enter by hand.
"""

from django.db import migrations


def seed(apps, schema_editor):
    Reference = apps.get_model("academic", "Reference")

    # 'paper' was a catch-all predating the medium choices; those rows are
    # journal articles.
    Reference.objects.filter(medium="paper").update(medium="journal_article")

    # Conference proceedings were all printed under "with Proceedings
    # (refereed)", so preserve that rather than silently demoting them.
    Reference.objects.filter(medium="conference_proceedings").update(refereed=True)

    # A preprint is work in review; everything else already has a venue and
    # keeps the 'published' default.
    Reference.objects.filter(medium="preprint").update(status="in_review")


class Migration(migrations.Migration):

    dependencies = [
        ("academic", "0066_remove_grant_amount_requested_and_more"),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
