"""A small file manager over MEDIA_ROOT (admin "Media Files" page).

Every file uploaded to the site lives under MEDIA_ROOT, one folder per purpose:

* ``markdown_assets/`` - the free upload area. Files here are published through a
  ``MediaFile`` record (``/media-file/<key>/``); this is the only area where folders
  can be created and files uploaded, renamed or moved.
* ``profile_images/``, ``news_images/``, ``publication_images/``, ``research_images/``,
  ``publication_files/`` - owned by their records (Profile, News, ...). They can be
  browsed, downloaded and, when no record uses a file any more, cleaned up.

Paths handled here are always relative to MEDIA_ROOT, use ``/`` and are validated so
nothing outside MEDIA_ROOT (or hidden, or symlinked) is ever touched.
"""
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import quote

from django.apps import apps
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import models
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.utils.text import get_valid_filename

UPLOAD_ROOT = 'markdown_assets'
PRIVATE_FOLDERS = {'publication_files'}
FOLDER_LABELS = {
    'markdown_assets': ('Uploads', '上传文件'),
    'profile_images': ('Profile Images', '头像图片'),
    'news_images': ('News Images', '新闻图片'),
    'publication_images': ('Publication Images', '论文图片'),
    'research_images': ('Research Images', '研究图片'),
    'publication_files': ('Publication Files', '论文附件'),
}
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.ico', '.avif'}
KIND_EXTENSIONS = {
    'pdf': {'.pdf'},
    'document': {'.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.md', '.csv',
                 '.json', '.bib', '.tex', '.odt', '.ods', '.odp', '.rtf'},
    'archive': {'.zip', '.tar', '.gz', '.tgz', '.7z', '.rar'},
    'audio': {'.mp3', '.wav', '.ogg', '.m4a', '.flac'},
    'video': {'.mp4', '.webm', '.mov', '.m4v'},
    'font': {'.ttf', '.otf', '.woff', '.woff2'},
}
# HTML, SVG, JS and similar are refused: uploads are served from this site's origin,
# where such files could run scripts.
UPLOAD_EXTENSIONS = IMAGE_EXTENSIONS.union(*KIND_EXTENSIONS.values())
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
# In-browser preview (admin only): what the browser can show natively.
PREVIEW_TYPES = {
    'image': IMAGE_EXTENSIONS,
    'video': {'.mp4', '.webm', '.mov', '.m4v'},
    'audio': {'.mp3', '.wav', '.ogg', '.m4a', '.flac'},
    'pdf': {'.pdf'},
    'text': {'.txt', '.md', '.csv', '.json', '.bib', '.tex'},
}
TEXT_PREVIEW_MAX_BYTES = 1024 * 1024
SEARCH_LIMIT = 500
SKIPPED_MODELS = {'AuditLog', 'MediaFile', 'ResourceMetricLog'}


class FileManagerError(Exception):
    """A user-facing error with English and Chinese text."""

    def __init__(self, en, zh, code='error', references=None):
        super().__init__(en)
        self.en = en
        self.zh = zh
        self.code = code
        self.references = references or []

    def text(self, zh):
        return self.zh if zh else self.en


# ---------------------------------------------------------------- paths

def media_root():
    return os.path.realpath(settings.MEDIA_ROOT)


def normalize(rel):
    """Clean a MEDIA_ROOT-relative path; refuse traversal and hidden entries."""
    rel = str(rel or '').replace('\\', '/').strip().strip('/')
    parts = [part for part in rel.split('/') if part not in ('', '.')]
    for part in parts:
        if part == '..' or part.startswith('.'):
            raise FileManagerError('Invalid path.', '路径无效。')
    return '/'.join(parts)


def absolute(rel):
    root = media_root()
    path = os.path.join(root, *rel.split('/')) if rel else root
    if os.path.islink(path):
        raise FileManagerError('Invalid path.', '路径无效。')
    real = os.path.realpath(path)
    if real != root and not real.startswith(root + os.sep):
        raise FileManagerError('Invalid path.', '路径无效。')
    return real


def is_editable(rel):
    """Folders/files the manager may create, rename or move (the upload area)."""
    return rel == UPLOAD_ROOT or rel.startswith(UPLOAD_ROOT + '/')


def top_folder(rel):
    return rel.split('/', 1)[0] if rel else ''


def is_private(rel):
    return top_folder(rel) in PRIVATE_FOLDERS


def folder_label(name, zh):
    labels = FOLDER_LABELS.get(name)
    return (labels[1] if zh else labels[0]) if labels else name


def file_kind(name):
    ext = os.path.splitext(name)[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return 'image'
    for kind, extensions in KIND_EXTENSIONS.items():
        if ext in extensions:
            return kind
    return 'other'


def preview_type(name):
    """How the admin can preview a file in the browser ('' when it cannot)."""
    ext = os.path.splitext(name)[1].lower()
    for kind, extensions in PREVIEW_TYPES.items():
        if ext in extensions:
            return kind
    return ''


def _visible(entry):
    return not entry.name.startswith('.') and not entry.is_symlink()


# ---------------------------------------------------------------- listing

@dataclass
class Reference:
    label: str
    url: str = ''
    via: str = 'field'  # field: a record's file/image field; path / key: a link in text


@dataclass
class FileEntry:
    name: str
    path: str
    size: int
    modified: datetime
    kind: str
    is_dir: bool = False
    file_count: int = 0
    label: str = ''
    record: object = None
    references: list = field(default_factory=list)

    @property
    def preview(self):
        return '' if self.is_dir else preview_type(self.name)

    @property
    def folder(self):
        return self.path.rsplit('/', 1)[0] if '/' in self.path else ''

    @property
    def editable(self):
        return is_editable(self.path) and self.path != UPLOAD_ROOT

    @property
    def private(self):
        return is_private(self.path)

    @property
    def used(self):
        return bool(self.references)

    @property
    def field_references(self):
        return [ref for ref in self.references if ref.via == 'field']

    @property
    def public_url(self):
        if self.is_dir or self.private:
            return ''
        if top_folder(self.path) == UPLOAD_ROOT:
            if not self.record:
                return ''
            return reverse('media_file_access', args=[self.record.access_key])
        return settings.MEDIA_URL + quote(self.path)

    @property
    def markdown(self):
        url = self.public_url
        if not url:
            return ''
        title = (self.record.title if self.record else os.path.splitext(self.name)[0]) or 'file'
        title = title.replace('[', '(').replace(']', ')')
        return ('![{}]({})' if self.kind == 'image' else '[{}]({})').format(title, url)


def _mtime(stat):
    return datetime.fromtimestamp(stat.st_mtime, tz=timezone.get_current_timezone())


def _dir_stats(path):
    count = size = 0
    for current, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and not os.path.islink(os.path.join(current, d))]
        for name in files:
            full = os.path.join(current, name)
            if name.startswith('.') or os.path.islink(full):
                continue
            try:
                size += os.path.getsize(full)
                count += 1
            except OSError:
                continue
    return count, size


def _file_entry(rel, stat):
    name = rel.rsplit('/', 1)[-1]
    return FileEntry(name=name, path=rel, size=stat.st_size, modified=_mtime(stat), kind=file_kind(name))


def list_folder(rel, zh=False):
    """Direct sub-folders and files of a folder."""
    path = absolute(rel)
    if not os.path.isdir(path):
        raise FileManagerError('Folder not found.', '文件夹不存在。', code='not_found')
    folders, files = [], []
    with os.scandir(path) as entries:
        for entry in entries:
            if not _visible(entry):
                continue
            child = '{}/{}'.format(rel, entry.name) if rel else entry.name
            stat = entry.stat()
            if entry.is_dir():
                count, size = _dir_stats(entry.path)
                folders.append(FileEntry(
                    name=entry.name, path=child, size=size, modified=_mtime(stat), kind='folder',
                    is_dir=True, file_count=count,
                    label=folder_label(entry.name, zh) if not rel else entry.name,
                ))
            elif entry.is_file():
                files.append(_file_entry(child, stat))
    return folders, files


def walk_files(rel=''):
    """Every file below a folder (recursive)."""
    base = absolute(rel)
    result = []
    for current, dirs, names in os.walk(base):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.') and not os.path.islink(os.path.join(current, d)))
        for name in names:
            full = os.path.join(current, name)
            if name.startswith('.') or os.path.islink(full):
                continue
            child = os.path.relpath(full, media_root()).replace(os.sep, '/')
            try:
                result.append(_file_entry(child, os.stat(full)))
            except OSError:
                continue
    return result


def editable_folders():
    """All folders of the upload area, for the "move to" picker."""
    base = absolute(UPLOAD_ROOT)
    if not os.path.isdir(base):
        return [UPLOAD_ROOT]
    result = [UPLOAD_ROOT]
    for current, dirs, _names in os.walk(base):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.') and not os.path.islink(os.path.join(current, d)))
        for name in dirs:
            result.append(os.path.relpath(os.path.join(current, name), media_root()).replace(os.sep, '/'))
    return result


def storage_summary(zh=False):
    folders, files = list_folder('', zh)
    total_files = sum(f.file_count for f in folders) + len(files)
    total_size = sum(f.size for f in folders) + sum(f.size for f in files)
    return folders, total_files, total_size


# ---------------------------------------------------------------- references

def _admin_url(obj):
    model_name = obj._meta.model_name
    target = obj
    if model_name == 'sectionitem':
        target = obj.section
    elif model_name == 'publicationfile':
        target = obj.publication
    try:
        return reverse('admin:myHomePage_{}_change'.format(target._meta.model_name), args=[target.pk])
    except NoReverseMatch:
        return ''


def _label(obj):
    text = str(obj)
    if len(text) > 60:
        text = text[:57] + '...'
    return '{}: {}'.format(str(obj._meta.verbose_name).capitalize(), text)


class ReferenceIndex:
    """Which records use which file, built once per request.

    A file counts as used when a record's file/image field points at it, or when any
    text (Markdown content, footer settings, ...) links to ``/media/<path>`` or to its
    ``/media-file/<key>/`` address.
    """

    def __init__(self):
        from .models import MediaFile
        self.records = {mf.file.name: mf for mf in MediaFile.objects.all() if mf.file}
        self.field_refs = {}
        self.texts = []
        for model in apps.get_app_config('myHomePage').get_models():
            if model.__name__ in SKIPPED_MODELS:
                continue
            fields = model._meta.concrete_fields
            file_fields = [f for f in fields if isinstance(f, models.FileField)]
            text_fields = [f for f in fields if isinstance(f, (models.CharField, models.TextField))]
            if not file_fields and not text_fields:
                continue
            for obj in model.objects.all():
                reference = None
                for f in file_fields:
                    name = getattr(obj, f.attname) or ''
                    if name:
                        reference = reference or Reference(_label(obj), _admin_url(obj))
                        self.field_refs.setdefault(str(name), []).append(reference)
                blob = '\n'.join(str(getattr(obj, f.attname) or '') for f in text_fields)
                if '/media' in blob:
                    self.texts.append((obj, blob))

    def references(self, rel):
        refs = list(self.field_refs.get(rel, []))
        record = self.records.get(rel)
        path_needle = settings.MEDIA_URL + rel
        key_needle = '/media-file/{}/'.format(record.access_key) if record else None
        for obj, blob in self.texts:
            if path_needle in blob or quote(path_needle) in blob:
                refs.append(Reference(_label(obj), _admin_url(obj), via='path'))
            elif key_needle and key_needle in blob:
                refs.append(Reference(_label(obj), _admin_url(obj), via='key'))
        return refs

    def annotate(self, entries):
        for entry in entries:
            if entry.is_dir:
                continue
            entry.record = self.records.get(entry.path)
            entry.references = self.references(entry.path)
        return entries


# ---------------------------------------------------------------- operations

def _require_editable(rel, allow_root=False):
    if not is_editable(rel) or (rel == UPLOAD_ROOT and not allow_root):
        raise FileManagerError(
            'Only files and folders under "Uploads" can be changed here; the other folders belong to their records.',
            '只能修改“上传文件”中的文件和文件夹；其他文件夹由对应的内容记录管理。',
        )


def _clean_name(name, is_file):
    raw = str(name or '').strip().replace('\\', '/').split('/')[-1]
    cleaned = get_valid_filename(raw) if raw else ''
    if not cleaned or cleaned.startswith('.') or cleaned in ('.', '..'):
        raise FileManagerError('Please enter a valid name.', '请输入有效的名称。')
    if is_file and os.path.splitext(cleaned)[1].lower() not in UPLOAD_EXTENSIONS:
        raise FileManagerError(
            'This file type is not allowed: {}'.format(cleaned),
            '不支持该文件类型：{}'.format(cleaned),
        )
    return cleaned[:150]


def upload(folder, uploaded_files):
    """Save uploads into a folder of the upload area; each gets a MediaFile record."""
    from .models import MediaFile
    folder = normalize(folder)
    _require_editable(folder, allow_root=True)
    os.makedirs(absolute(UPLOAD_ROOT), exist_ok=True)
    if not os.path.isdir(absolute(folder)):
        raise FileManagerError('Folder not found.', '文件夹不存在。')
    saved, errors = [], []
    for uploaded in uploaded_files:
        try:
            name = _clean_name(uploaded.name, is_file=True)
            if uploaded.size > MAX_UPLOAD_BYTES:
                raise FileManagerError(
                    '{} is larger than 50 MB.'.format(name), '{} 超过 50 MB。'.format(name))
            stored = default_storage.save('{}/{}'.format(folder, name), uploaded)
            record = MediaFile(title=os.path.splitext(name)[0][:200], file=stored, is_active=True, is_draft=False)
            record.save()
            saved.append(stored)
        except FileManagerError as exc:
            errors.append(exc)
    return saved, errors


def make_folder(parent, name):
    parent = normalize(parent)
    _require_editable(parent, allow_root=True)
    os.makedirs(absolute(UPLOAD_ROOT), exist_ok=True)
    if not os.path.isdir(absolute(parent)):
        raise FileManagerError('Folder not found.', '文件夹不存在。')
    rel = '{}/{}'.format(parent, _clean_name(name, is_file=False))
    target = absolute(rel)
    if os.path.exists(target):
        raise FileManagerError('A file or folder with this name already exists.', '已存在同名的文件或文件夹。')
    os.mkdir(target)
    return rel


def _relocate(src, dst):
    """Rename on disk, then point MediaFile records at the new path.

    QuerySet.update() is used on purpose: saving the records would fire the
    pre_save signal that deletes a replaced file.
    """
    from .models import MediaFile
    src_abs, dst_abs = absolute(src), absolute(dst)
    if os.path.exists(dst_abs):
        raise FileManagerError('A file or folder with this name already exists.', '已存在同名的文件或文件夹。')
    is_dir = os.path.isdir(src_abs)
    os.rename(src_abs, dst_abs)
    now = timezone.now()
    if is_dir:
        for record in MediaFile.objects.filter(file__startswith=src + '/'):
            MediaFile.objects.filter(pk=record.pk).update(file=dst + record.file.name[len(src):], updated_at=now)
    else:
        MediaFile.objects.filter(file=src).update(file=dst, updated_at=now)
    return dst


def _check_links(rel, index, force, action_en, action_zh):
    """Direct /media/<path> links in text break when a file moves or disappears."""
    if os.path.isdir(absolute(rel)):
        refs = []
        for entry in walk_files(rel):
            refs.extend(r for r in index.references(entry.path) if r.via == 'path')
    else:
        refs = [r for r in index.references(rel) if r.via == 'path']
    if refs and not force:
        raise FileManagerError(
            'Content links to this file by its path; {} it will break those links.'.format(action_en),
            '有内容通过路径直接链接了此文件，{}后这些链接会失效。'.format(action_zh),
            code='needs_confirm', references=refs,
        )


def rename(rel, new_name, index, force=False):
    rel = normalize(rel)
    _require_editable(rel)
    src_abs = absolute(rel)
    if not os.path.exists(src_abs):
        raise FileManagerError('File not found.', '文件不存在。')
    is_file = os.path.isfile(src_abs)
    name = _clean_name(new_name, is_file=is_file)
    parent = rel.rsplit('/', 1)[0]
    dst = '{}/{}'.format(parent, name)
    if dst == rel:
        return rel
    _check_links(rel, index, force, 'renaming', '重命名')
    return _relocate(rel, dst)


def move(rel, dest_folder, index, force=False):
    rel = normalize(rel)
    dest_folder = normalize(dest_folder)
    _require_editable(rel)
    _require_editable(dest_folder, allow_root=True)
    if not os.path.exists(absolute(rel)):
        raise FileManagerError('File not found.', '文件不存在。')
    if not os.path.isdir(absolute(dest_folder)):
        raise FileManagerError('Target folder not found.', '目标文件夹不存在。')
    if dest_folder == rel or dest_folder.startswith(rel + '/'):
        raise FileManagerError('A folder cannot be moved into itself.', '不能把文件夹移动到它自身里面。')
    dst = '{}/{}'.format(dest_folder, rel.rsplit('/', 1)[-1])
    if dst == rel:
        return rel
    _check_links(rel, index, force, 'moving', '移动')
    return _relocate(rel, dst)


def delete(rel, index, force=False):
    """Delete a file, or an empty folder of the upload area."""
    from .models import MediaFile
    rel = normalize(rel)
    if not rel or '/' not in rel:
        raise FileManagerError('Top-level folders cannot be deleted.', '顶层文件夹不能删除。')
    path = absolute(rel)
    if os.path.isdir(path):
        _require_editable(rel)
        if walk_files(rel):
            raise FileManagerError('Only empty folders can be deleted.', '只能删除空文件夹。')
        shutil.rmtree(path)
        return
    if not os.path.isfile(path):
        raise FileManagerError('File not found.', '文件不存在。')
    refs = index.references(rel)
    owners = [r for r in refs if r.via == 'field']
    if owners:
        raise FileManagerError(
            'This file is still used by a record; replace or remove it there first.',
            '此文件仍被内容记录使用，请先在对应记录中替换或移除。',
            code='in_use', references=owners,
        )
    if refs and not force:
        raise FileManagerError(
            'Content still links to this file; deleting it will break those links.',
            '仍有内容链接到此文件，删除后这些链接会失效。',
            code='needs_confirm', references=refs,
        )
    os.remove(path)
    # Records go too; their post_delete signal finds the file already gone.
    for record in MediaFile.objects.filter(file=rel):
        record.delete()


def update_meta(rel, index, name='', title='', is_active=True, is_draft=False, force=False):
    """Edit a file of the upload area: file name plus its record's title / flags."""
    from .models import MediaFile
    rel = normalize(rel)
    _require_editable(rel)
    if not os.path.isfile(absolute(rel)):
        raise FileManagerError('File not found.', '文件不存在。')
    name = str(name or '').strip()
    if name and name != rel.rsplit('/', 1)[-1]:
        rel = rename(rel, name, index, force)
    record = MediaFile.objects.filter(file=rel).first() or register(rel)
    record.title = (str(title or '').strip() or os.path.splitext(rel.rsplit('/', 1)[-1])[0])[:200]
    record.is_active = bool(is_active)
    record.is_draft = bool(is_draft)
    record.save(update_fields=['title', 'is_active', 'is_draft', 'updated_at'])
    return rel


def register(rel):
    """Create the MediaFile record for a file of the upload area that has none."""
    from .models import MediaFile
    rel = normalize(rel)
    _require_editable(rel)
    if not os.path.isfile(absolute(rel)):
        raise FileManagerError('File not found.', '文件不存在。')
    if MediaFile.objects.filter(file=rel).exists():
        return MediaFile.objects.filter(file=rel).first()
    name = rel.rsplit('/', 1)[-1]
    record = MediaFile(title=os.path.splitext(name)[0][:200], file=rel, is_active=True, is_draft=False)
    record.save()
    return record
