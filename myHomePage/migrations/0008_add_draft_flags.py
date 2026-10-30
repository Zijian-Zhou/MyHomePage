from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myHomePage', '0007_mediafile'),
    ]

    operations = [
        migrations.AddField(
            model_name='mediafile',
            name='is_draft',
            field=models.BooleanField(default=False, verbose_name='Draft'),
        ),
        migrations.AddField(
            model_name='news',
            name='is_draft',
            field=models.BooleanField(default=False, verbose_name='Draft'),
        ),
        migrations.AddField(
            model_name='profile',
            name='is_draft',
            field=models.BooleanField(default=False, verbose_name='Draft'),
        ),
        migrations.AddField(
            model_name='publication',
            name='is_draft',
            field=models.BooleanField(default=False, verbose_name='Draft'),
        ),
        migrations.AddField(
            model_name='research',
            name='is_draft',
            field=models.BooleanField(default=False, verbose_name='Draft'),
        ),
        migrations.AddField(
            model_name='section',
            name='is_draft',
            field=models.BooleanField(default=False, verbose_name='Draft'),
        ),
    ]
