from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("academic", "0075_tutorials_are_presentations"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="show_projects",
            field=models.BooleanField(
                default=True,
                help_text="Show the Projects section on the home page.",
            ),
        ),
    ]
