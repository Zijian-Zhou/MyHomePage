from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('myHomePage', '0008_add_draft_flags'),
    ]

    operations = [
        migrations.AlterField(
            model_name='section',
            name='content',
            field=models.TextField(blank=True, verbose_name='Content'),
        ),
        migrations.CreateModel(
            name='SectionItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, max_length=200, verbose_name='Title')),
                ('content', models.TextField(verbose_name='Content')),
                ('is_active', models.BooleanField(default=True, verbose_name='Active')),
                ('is_draft', models.BooleanField(default=False, verbose_name='Draft')),
                ('order', models.IntegerField(default=0, verbose_name='Order')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('section', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='myHomePage.section', verbose_name='Section')),
            ],
            options={
                'verbose_name': 'Section Item',
                'verbose_name_plural': 'Section Items',
                'ordering': ['order', '-created_at'],
            },
        ),
    ]
