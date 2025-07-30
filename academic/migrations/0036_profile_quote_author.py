# Generated manually for adding quote_author field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academic', '0035_profile_quote'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='quote_author',
            field=models.CharField(blank=True, help_text='Author of the quote', max_length=200, null=True),
        ),
    ]