from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_delete, pre_save
from django.core.signals import got_request_exception
from django.dispatch import receiver
from django.utils import timezone

from .models import MediaFile, News, Profile, Publication, PublicationFile, Research
from .security import identity_digest, sign_identity


@receiver(user_logged_in)
def set_login_session_signature(sender, request, user, **kwargs):
    digest = identity_digest(user)
    request.session["auth_sig"] = sign_identity(digest)
    request.session["auth_ts"] = int(timezone.now().timestamp())


@receiver(got_request_exception)
def audit_server_error(sender, request=None, **kwargs):
    """Unhandled exception (HTTP 500) -> audit log "Anomaly / Server error"."""
    import sys
    from .security_monitor import report_exception
    report_exception(request, sys.exc_info()[1])


@receiver(post_delete, sender=MediaFile)
def delete_media_file_asset(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)


@receiver(pre_save, sender=MediaFile)
def delete_replaced_media_file_asset(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        existing = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    if existing.file and existing.file != instance.file:
        existing.file.delete(save=False)


@receiver(post_delete, sender=Publication)
def delete_publication_image_file(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)


@receiver(pre_save, sender=Publication)
def delete_replaced_publication_image_file(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        existing = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    if existing.image and existing.image != instance.image:
        existing.image.delete(save=False)


@receiver(post_delete, sender=PublicationFile)
def delete_publication_attached_file(sender, instance, **kwargs):
    _delete_file_field(instance.file)


@receiver(pre_save, sender=PublicationFile)
def delete_replaced_publication_attached_file(sender, instance, **kwargs):
    _delete_replaced_file(sender, instance, 'file')


def _delete_file_field(file_field):
    if file_field:
        file_field.delete(save=False)


def _delete_replaced_file(sender, instance, field_name):
    if not instance.pk:
        return

    try:
        existing = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    old_file = getattr(existing, field_name, None)
    new_file = getattr(instance, field_name, None)
    if old_file and old_file != new_file:
        old_file.delete(save=False)


@receiver(post_delete, sender=Profile)
def delete_profile_image_file(sender, instance, **kwargs):
    _delete_file_field(instance.profile_image)


@receiver(pre_save, sender=Profile)
def delete_replaced_profile_image_file(sender, instance, **kwargs):
    _delete_replaced_file(sender, instance, 'profile_image')


@receiver(post_delete, sender=Research)
def delete_research_image_file(sender, instance, **kwargs):
    _delete_file_field(instance.image)


@receiver(pre_save, sender=Research)
def delete_replaced_research_image_file(sender, instance, **kwargs):
    _delete_replaced_file(sender, instance, 'image')


@receiver(post_delete, sender=News)
def delete_news_image_file(sender, instance, **kwargs):
    _delete_file_field(instance.image)


@receiver(pre_save, sender=News)
def delete_replaced_news_image_file(sender, instance, **kwargs):
    _delete_replaced_file(sender, instance, 'image')


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry  # noqa: E402
from django.contrib.auth.signals import user_logged_out, user_login_failed  # noqa: E402
from django.db.models.signals import post_save  # noqa: E402

from . import audit  # noqa: E402


@receiver(user_logged_in)
def audit_login_success(sender, request, user, **kwargs):
    audit.record('login_success', user=user, request=request)


@receiver(user_login_failed)
def audit_login_failed(sender, credentials, request=None, **kwargs):
    username = (credentials or {}).get('username', '') if isinstance(credentials, dict) else ''
    audit.record('login_failed', status='failure', username=username, request=request,
                 message='Invalid username or password.')


@receiver(user_logged_out)
def audit_logout(sender, request, user, **kwargs):
    if user is not None:
        audit.record('logout', user=user, request=request)


_LOGENTRY_ACTIONS = {ADDITION: 'object_add', CHANGE: 'object_change', DELETION: 'object_delete'}


@receiver(post_save, sender=LogEntry)
def audit_admin_change(sender, instance, created, **kwargs):
    """Mirror every Django admin add/change/delete into the audit trail."""
    # raw=True means fixture loading (e.g. a backup restore re-inserting old LogEntry
    # rows): those are history, not new actions.
    if not created or kwargs.get('raw'):
        return
    action = _LOGENTRY_ACTIONS.get(instance.action_flag)
    if not action:
        return
    model = instance.content_type.model_class() if instance.content_type_id else None
    model_name = str(model._meta.verbose_name) if model is not None else (
        instance.content_type.model if instance.content_type_id else '')
    target = '{}: {}'.format(model_name, instance.object_repr) if model_name else instance.object_repr
    audit.record(action, user=instance.user, object_repr=target,
                 message=instance.get_change_message() or '')
