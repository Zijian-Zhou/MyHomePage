"""Full-site backups: create, inspect, import and restore.

A backup is a zip archive containing:

* ``manifest.json`` - format marker, app version, creation time, counts and the
  applied migrations of the source database;
* ``data.json``     - all database records (``dumpdata`` with natural foreign keys,
  without content types, permissions, sessions and resource-monitor history);
* ``media/...``     - every file under ``MEDIA_ROOT``.

Restoring first writes an automatic "pre-restore" backup of the current state,
swaps the media directory and then replaces the database inside one transaction.
If loading the data fails, the transaction is rolled back and the previous media
files are moved back, so the site is left unchanged.
"""
import io
import json
import os
import re
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.core.management import call_command
from django.db import connection, transaction
from django.db.migrations.recorder import MigrationRecorder
from django.utils import timezone

BACKUP_FORMAT = 'myhomepage-backup'
BACKUP_FORMAT_VERSION = 1
MANIFEST_NAME = 'manifest.json'
DATA_NAME = 'data.json'
MEDIA_PREFIX = 'media/'

# Content types and permissions are recreated by migrations (records reference them
# by natural key); sessions and resource-monitor samples are transient.
DUMP_EXCLUDES = ['contenttypes', 'auth.permission', 'sessions', 'myHomePage.ResourceMetricLog']

BACKUP_NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,150}\.zip$')
KIND_MANUAL = 'manual'
KIND_PRE_RESTORE = 'pre-restore'
KIND_IMPORTED = 'imported'
_NAME_PREFIXES = {
    KIND_MANUAL: 'myhomepage-backup',
    KIND_PRE_RESTORE: 'myhomepage-pre-restore',
    KIND_IMPORTED: 'imported',
}


class BackupError(Exception):
    """A user-facing backup problem (invalid archive, incompatible version, ...)."""

    def __init__(self, code, **params):
        self.code = code
        self.params = params
        super().__init__(code)


def backup_root():
    root = Path(settings.BACKUP_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _media_root():
    return Path(settings.MEDIA_ROOT)


def _applied_migrations():
    applied = MigrationRecorder(connection).applied_migrations()
    result = {}
    for app_label, name in sorted(applied):
        result.setdefault(app_label, []).append(name)
    return result


def _unique_path(root, filename):
    stem, suffix = os.path.splitext(filename)
    candidate = root / filename
    counter = 1
    while candidate.exists():
        candidate = root / '{}-{}{}'.format(stem, counter, suffix)
        counter += 1
    return candidate


def _timestamp():
    return timezone.localtime().strftime('%Y%m%d-%H%M%S')


def _iter_media_files():
    media_root = _media_root()
    if not media_root.is_dir():
        return
    for dirpath, dirnames, filenames in os.walk(media_root, followlinks=False):
        dirnames.sort()
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            if path.is_symlink() or not path.is_file():
                continue
            yield path, path.relative_to(media_root).as_posix()


def create_backup(kind=KIND_MANUAL, note=''):
    """Write a new backup archive and return its summary (see ``describe_backup``)."""
    root = backup_root()
    target = _unique_path(root, '{}-{}.zip'.format(_NAME_PREFIXES.get(kind, 'myhomepage-backup'), _timestamp()))
    partial = target.with_name(target.name + '.part')

    buffer = io.StringIO()
    call_command('dumpdata', use_natural_foreign_keys=True, exclude=DUMP_EXCLUDES, stdout=buffer, verbosity=0)
    data_text = buffer.getvalue()
    record_count = len(json.loads(data_text or '[]'))

    media_count = 0
    media_bytes = 0
    try:
        with zipfile.ZipFile(partial, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
            archive.writestr(DATA_NAME, data_text.encode('utf-8'))
            for path, rel in _iter_media_files():
                archive.write(path, MEDIA_PREFIX + rel)
                media_count += 1
                media_bytes += path.stat().st_size
            manifest = {
                'format': BACKUP_FORMAT,
                'format_version': BACKUP_FORMAT_VERSION,
                'app_version': settings.APP_VERSION,
                'created_at': timezone.now().isoformat(),
                'kind': kind,
                'note': (note or '').strip()[:500],
                'database': {'vendor': connection.vendor, 'record_count': record_count},
                'media': {'file_count': media_count, 'total_bytes': media_bytes},
                'migrations': _applied_migrations(),
            }
            archive.writestr(MANIFEST_NAME, json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8'))
        os.replace(partial, target)
    finally:
        if partial.exists():
            partial.unlink()
    return describe_backup(target)


def _check_member_name(name):
    """Reject absolute paths, drive letters, backslashes and parent-directory segments."""
    if not name or name.startswith('/') or '\\' in name or ':' in name or '\x00' in name:
        raise BackupError('unsafe_path', name=name)
    parts = PurePosixPath(name).parts
    if any(part in ('..', '') for part in parts):
        raise BackupError('unsafe_path', name=name)
    if name not in (MANIFEST_NAME, DATA_NAME) and not name.startswith(MEDIA_PREFIX):
        raise BackupError('unexpected_member', name=name)


def _read_manifest(archive):
    try:
        manifest = json.loads(archive.read(MANIFEST_NAME).decode('utf-8'))
    except KeyError:
        raise BackupError('missing_manifest')
    except (ValueError, UnicodeDecodeError):
        raise BackupError('invalid_manifest')
    if not isinstance(manifest, dict) or manifest.get('format') != BACKUP_FORMAT:
        raise BackupError('invalid_manifest')
    try:
        format_version = int(manifest.get('format_version', 0))
    except (TypeError, ValueError):
        raise BackupError('invalid_manifest')
    if format_version < 1 or format_version > BACKUP_FORMAT_VERSION:
        raise BackupError('unsupported_format', version=manifest.get('format_version'))
    return manifest


def inspect_backup(path, deep=False):
    """Validate an archive and return its manifest.

    ``deep`` also checks every member name and the zip CRCs (used for imports and
    before restoring); the listing only reads the manifest.
    """
    try:
        with zipfile.ZipFile(path) as archive:
            manifest = _read_manifest(archive)
            if deep:
                names = archive.namelist()
                if DATA_NAME not in names:
                    raise BackupError('missing_data')
                for name in names:
                    _check_member_name(name)
                if archive.testzip() is not None:
                    raise BackupError('corrupt_archive')
            return manifest
    except zipfile.BadZipFile:
        raise BackupError('not_a_zip')


def _kind_from_name(name):
    if name.startswith(_NAME_PREFIXES[KIND_IMPORTED] + '-'):
        return KIND_IMPORTED
    if name.startswith(_NAME_PREFIXES[KIND_PRE_RESTORE] + '-'):
        return KIND_PRE_RESTORE
    return KIND_MANUAL


def describe_backup(path):
    path = Path(path)
    stat = path.stat()
    info = {
        'name': path.name,
        'size': stat.st_size,
        'modified': datetime.fromtimestamp(stat.st_mtime, tz=timezone.get_current_timezone()),
        'kind': _kind_from_name(path.name),
        'manifest': None,
        'error': None,
    }
    try:
        info['manifest'] = inspect_backup(path)
    except BackupError as exc:
        info['error'] = exc
    return info


def list_backups():
    root = backup_root()
    paths = [p for p in root.iterdir() if p.is_file() and p.suffix.lower() == '.zip']
    paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [describe_backup(p) for p in paths]


def resolve_backup(name):
    """Map a user-supplied archive name to a path inside BACKUP_ROOT (or raise)."""
    if not name or not BACKUP_NAME_RE.match(name):
        raise BackupError('not_found')
    root = backup_root().resolve()
    path = (root / name).resolve()
    if path.parent != root or not path.is_file():
        raise BackupError('not_found')
    return path


def delete_backup(name):
    resolve_backup(name).unlink()


def _sanitize_upload_name(filename):
    stem = os.path.splitext(os.path.basename(filename or ''))[0]
    stem = re.sub(r'[^A-Za-z0-9._-]+', '-', stem).strip('.-_')[:80]
    return stem or 'backup'


def import_backup(uploaded_file):
    """Validate an uploaded archive and store it in BACKUP_ROOT."""
    root = backup_root()
    fd, temp_name = tempfile.mkstemp(prefix='.upload-', suffix='.part', dir=root)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, 'wb') as handle:
            for chunk in uploaded_file.chunks():
                handle.write(chunk)
        inspect_backup(temp_path, deep=True)
        target = _unique_path(root, '{}-{}-{}.zip'.format(
            _NAME_PREFIXES[KIND_IMPORTED], _timestamp(), _sanitize_upload_name(uploaded_file.name)))
        os.replace(temp_path, target)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    return describe_backup(target)


def _check_compatibility(manifest):
    """Refuse archives whose schema is newer than this installation."""
    current = _applied_migrations()
    unknown = []
    for app_label, names in (manifest.get('migrations') or {}).items():
        known = set(current.get(app_label, []))
        unknown.extend('{}.{}'.format(app_label, n) for n in names if n not in known)
    if unknown:
        raise BackupError('newer_schema', migrations=', '.join(unknown[:5]) + (' ...' if len(unknown) > 5 else ''),
                          version=manifest.get('app_version', '?'))


def _extract_media(archive, destination):
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    for info in archive.infolist():
        if not info.filename.startswith(MEDIA_PREFIX) or info.is_dir():
            continue
        rel = info.filename[len(MEDIA_PREFIX):]
        if not rel:
            continue
        target = (destination / rel).resolve()
        if root not in target.parents:
            raise BackupError('unsafe_path', name=info.filename)
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as src, open(target, 'wb') as dst:
            shutil.copyfileobj(src, dst)


def _move_children(source, destination):
    for child in list(source.iterdir()):
        shutil.move(str(child), str(destination / child.name))


def _clear_children(directory):
    for child in list(directory.iterdir()):
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def restore_backup(name):
    """Replace the database and media with the archive's contents.

    Returns ``{'restored': <summary>, 'safety_backup': <summary>}``.
    """
    path = resolve_backup(name)
    manifest = inspect_backup(path, deep=True)
    _check_compatibility(manifest)

    with zipfile.ZipFile(path) as archive:
        needed = sum(i.file_size for i in archive.infolist())
    if shutil.disk_usage(str(backup_root())).free < needed * 2:
        raise BackupError('disk_full')

    safety = create_backup(kind=KIND_PRE_RESTORE, note='Automatic backup before restoring {}'.format(path.name))

    media_root = _media_root()
    media_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.restore-', dir=str(backup_root())) as work:
        work = Path(work)
        new_media = work / 'media_new'
        old_media = work / 'media_old'
        old_media.mkdir()
        with zipfile.ZipFile(path) as archive:
            archive.extract(DATA_NAME, str(work))
            _extract_media(archive, new_media)

        # 1) swap media (reversible), 2) replace the database atomically.
        _move_children(media_root, old_media)
        try:
            _move_children(new_media, media_root)
            with transaction.atomic():
                call_command('flush', interactive=False, verbosity=0)
                call_command('loaddata', str(work / DATA_NAME), ignore=True, verbosity=0)
        except Exception:
            _clear_children(media_root)
            _move_children(old_media, media_root)
            raise

    return {'restored': describe_backup(path), 'safety_backup': safety}
