from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myHomePage', '0010_mediafile_access_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='news',
            name='content_zh',
            field=models.TextField(blank=True, default='', verbose_name='Content (Chinese)'),
        ),
        migrations.AddField(
            model_name='news',
            name='title_zh',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='Title (Chinese)'),
        ),
        migrations.AddField(
            model_name='research',
            name='description_zh',
            field=models.TextField(blank=True, default='', verbose_name='Description (Chinese)'),
        ),
        migrations.AddField(
            model_name='research',
            name='title_zh',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='Title (Chinese)'),
        ),
        migrations.AddField(
            model_name='section',
            name='content_zh',
            field=models.TextField(blank=True, default='', verbose_name='Content (Chinese)'),
        ),
        migrations.AddField(
            model_name='section',
            name='title_zh',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='Title (Chinese)'),
        ),
        migrations.AddField(
            model_name='sectionitem',
            name='content_zh',
            field=models.TextField(blank=True, default='', verbose_name='Content (Chinese)'),
        ),
        migrations.AddField(
            model_name='sectionitem',
            name='title_zh',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='Title (Chinese)'),
        ),
    ]

