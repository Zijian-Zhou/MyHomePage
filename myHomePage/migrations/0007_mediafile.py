from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myHomePage', '0006_alter_systemconfig_value'),
    ]

    operations = [
        migrations.CreateModel(
            name='MediaFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Title')),
                ('file', models.FileField(upload_to='markdown_assets/', verbose_name='File')),
                ('is_active', models.BooleanField(default=True, verbose_name='Active')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
            ],
            options={
                'verbose_name': 'Media File',
                'verbose_name_plural': 'Media Files',
                'ordering': ['-created_at'],
            },
        ),
    ]
