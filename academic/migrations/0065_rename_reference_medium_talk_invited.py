"""Rename Reference.reference_type -> medium and Talk.is_invited -> invited.

Written by hand rather than generated so the renames are unambiguous: the
autodetector would otherwise offer to match these against the unrelated fields
added in the next migration, and answering that wrong would drop real data.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("academic", "0064_profile_show_publications"),
    ]

    operations = [
        migrations.RenameField(
            model_name="reference",
            old_name="reference_type",
            new_name="medium",
        ),
        migrations.RenameField(
            model_name="talk",
            old_name="is_invited",
            new_name="invited",
        ),
    ]
