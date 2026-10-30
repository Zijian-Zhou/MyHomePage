from django.db import migrations, models


def set_default_sync_interval(apps, schema_editor):
    SystemConfig = apps.get_model('myHomePage', 'SystemConfig')
    for config in SystemConfig.objects.filter(category='sync_interval'):
        if not (config.value or '').strip():
            config.value = '24'
            config.save(update_fields=['value'])


class Migration(migrations.Migration):

    dependencies = [
        ('myHomePage', '0005_alter_publication_bibtex_key'),
    ]

    operations = [
        migrations.AlterField(
            model_name='systemconfig',
            name='value',
            field=models.TextField(blank=True, default='', verbose_name='Value'),
        ),
        migrations.RunPython(set_default_sync_interval, migrations.RunPython.noop),
    ]
