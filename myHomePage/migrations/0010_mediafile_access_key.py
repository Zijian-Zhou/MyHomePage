from django.db import migrations, models
import hashlib
import time


def _build_access_key(instance):
    ts = str(int(time.time() * 1000))
    h = hashlib.sha256()
    h.update(ts.encode('utf-8'))
    h.update(b'|')
    h.update((getattr(instance.file, 'name', '') or '').encode('utf-8'))
    h.update(b'|')
    try:
        if instance.file:
            instance.file.open('rb')
            chunk = instance.file.read(1024 * 1024)
            instance.file.close()
            h.update(chunk or b'')
    except Exception:
        pass
    return h.hexdigest()


def populate_access_keys(apps, schema_editor):
    MediaFile = apps.get_model('myHomePage', 'MediaFile')
    existing = set()
    for item in MediaFile.objects.all().iterator():
        if item.access_key:
            continue
        key = _build_access_key(item)
        while key in existing:
            key = _build_access_key(item)
        existing.add(key)
        item.access_key = key
        item.save(update_fields=['access_key'])


class Migration(migrations.Migration):

    dependencies = [
        ('myHomePage', '0009_sectionitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='mediafile',
            name='access_key',
            field=models.CharField(blank=True, db_index=True, default='', max_length=64),
        ),
        migrations.RunPython(populate_access_keys, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='mediafile',
            name='access_key',
            field=models.CharField(blank=True, db_index=True, default='', max_length=64, unique=True),
        ),
    ]
