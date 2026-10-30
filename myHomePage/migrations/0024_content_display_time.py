from django.db import migrations, models
from django.db.models import F
from django.utils import timezone


def copy_created_time(apps, schema_editor):
    for model_name in ('Publication', 'Research', 'News', 'Section', 'SectionItem'):
        model = apps.get_model('myHomePage', model_name)
        model.objects.update(display_time=F('created_at'))


class Migration(migrations.Migration):

    dependencies = [
        ('myHomePage', '0023_alter_aiconfig_provider'),
    ]

    operations = [
        migrations.AddField(
            model_name='publication',
            name='display_time',
            field=models.DateTimeField(default=timezone.now, verbose_name='Display Time'),
        ),
        migrations.AddField(
            model_name='research',
            name='display_time',
            field=models.DateTimeField(default=timezone.now, verbose_name='Display Time'),
        ),
        migrations.AddField(
            model_name='news',
            name='display_time',
            field=models.DateTimeField(default=timezone.now, verbose_name='Display Time'),
        ),
        migrations.AddField(
            model_name='section',
            name='display_time',
            field=models.DateTimeField(default=timezone.now, verbose_name='Display Time'),
        ),
        migrations.AddField(
            model_name='sectionitem',
            name='display_time',
            field=models.DateTimeField(default=timezone.now, verbose_name='Display Time'),
        ),
        migrations.RunPython(copy_created_time, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name='news',
            options={
                'ordering': ['-order', '-display_time'],
                'verbose_name': 'News',
                'verbose_name_plural': 'News',
            },
        ),
    ]
