from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone

from .security import encrypt_identity, identity_digest


@receiver(user_logged_in)
def set_login_session_signature(sender, request, user, **kwargs):
    digest = identity_digest(user)
    request.session["auth_sig"] = encrypt_identity(digest)
    request.session["auth_ts"] = int(timezone.now().timestamp())
