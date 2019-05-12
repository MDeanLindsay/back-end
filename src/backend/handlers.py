import logging
from calendar import timegm
from datetime import datetime

from django.conf import settings
from django.dispatch import receiver
from allauth.account.models import EmailConfirmation
from django.contrib.auth.models import User as AuthUser
from allauth.account.signals import user_signed_up, email_confirmed

from backend.tasks import send_slack_invite_job, add_user_to_mailing_list

logger = logging.getLogger(__name__)


# noinspection PyUnresolvedReferences
def custom_jwt_payload_handler(user: AuthUser) -> dict:
    """
    Overrides the default jwt_payload_handler to embed
    extra data into the JWT
    """
    user_info = user.userinfo

    payload = {
        "email": user.username,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "zipcode": user_info.zip,
        "isMentor": user_info.mentor,
        "exp": datetime.utcnow() + settings.JWT_AUTH["JWT_EXPIRATION_DELTA"],
        "orig_iat": timegm(datetime.utcnow().utctimetuple()),
    }

    return payload


def get_username_from_jwt(payload: dict) -> str:
    """
    Overrides the default payload handler to use
    "email" instead of "username"
    :param payload:
    """
    return payload.get("email")


@receiver(user_signed_up)
def registration_callback(user: AuthUser, **kwargs) -> None:
    """
    Listens for the `user_signed_up` signal and adds a background task to
    send the slack invite
    """
    logger.info(f"Received user_signed_up signal for {user}")
    send_slack_invite_job(user.email)


@receiver(email_confirmed)
def email_confirmed_callback(email_address: EmailConfirmation, **kwargs) -> None:
    """
    Listens for the `email_confirmed` signal and adds a background task to
    add the user to the mailing list
    """
    logger.info(f"Received email_confirmed signal for {email_address.email}")
    add_user_to_mailing_list(email_address.email)
