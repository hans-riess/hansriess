"""Seed the 'Coordination Sheaf' demo, which the landing page teased as
hardcoded markup before the Demo model existed.

Active by default, so this preserves the teaser's current on-screen behavior
without anyone having to re-enter it by hand.
"""

from django.db import migrations


BLURB = (
    "A formation holds station around a target only some of the agents can "
    "see — and those that do read a single number each. Steer the target, "
    "wire the agents up differently, and watch what the others can still infer."
)
NOTE = "Keyboard and mouse — desktop only for now"


def seed(apps, schema_editor):
    Demo = apps.get_model("academic", "Demo")
    Demo.objects.get_or_create(
        slug="coordination-sheaf",
        defaults={
            "title": "Coordination sheaf",
            "blurb": BLURB,
            "note": NOTE,
            "is_active": True,
            "order": 0,
        },
    )


def unseed(apps, schema_editor):
    Demo = apps.get_model("academic", "Demo")
    Demo.objects.filter(slug="coordination-sheaf").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("academic", "0070_add_demo_model"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
