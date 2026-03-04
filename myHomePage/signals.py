from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import MediaFile, Publication
from .security import encrypt_identity, identity_digest


@receiver(user_logged_in)
def set_login_session_signature(sender, request, user, **kwargs):
    digest = identity_digest(user)
    request.session["auth_sig"] = encrypt_identity(digest)
    request.session["auth_ts"] = int(timezone.now().timestamp())


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
