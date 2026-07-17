from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import MediaFile, News, Profile, Publication, Research
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
