from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myHomePage', '0013_alter_systemconfig_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='address_zh',
            field=models.TextField(blank=True, default='', verbose_name='Address (Chinese)'),
        ),
        migrations.AddField(
            model_name='profile',
            name='bio_zh',
            field=models.TextField(blank=True, default='', verbose_name='Bio (Chinese)'),
        ),
    ]

