import uuid

import graphene
from django.db import transaction
from django.utils import timezone
from django.utils.translation import override
from django.utils.translation import ugettext_lazy as _
from django_ilmoitin.utils import send_notification
from graphene_django.types import DjangoObjectType
from graphql import GraphQLError
from graphql_jwt.decorators import login_required

from profiles.models import Profile

from .enums import NotificationType, YouthLanguage
from .models import YouthProfile

with override("en"):
    LanguageAtHome = graphene.Enum.from_enum(
        YouthLanguage, description=lambda e: e.label if e else ""
    )


class YouthProfileType(DjangoObjectType):
    membership_number = graphene.String(
        source="membership_number", description="Youth's membership number"
    )

    language_at_home = LanguageAtHome(
        source="language_at_home",
        description="The language which is spoken in the youth's home.",
    )

    class Meta:
        model = YouthProfile
        exclude = ("id", "approval_token", "language_at_home")


# Abstract base fields
class YouthProfileFields(graphene.InputObjectType):
    school_name = graphene.String(description="The youth's school name.")
    school_class = graphene.String(description="The youth's school class.")
    language_at_home = LanguageAtHome(
        description="The language which is spoken in the youth's home."
    )
    approver_first_name = graphene.String(
        description="The youth's (supposed) guardian's first name."
    )
    approver_last_name = graphene.String(
        description="The youth's (supposed) guardian's last name."
    )
    approver_phone = graphene.String(
        description="The youth's (supposed) guardian's phone number."
    )
    approver_email = graphene.String(
        description="The youth's (supposed) guardian's email address which will be used to send approval requests."
    )
    birth_date = graphene.Date(
        required=False,
        description="The youth's birth date. This is used for example to calculate if the youth is a minor or not.",
    )


# Subset of abstract fields are required for creation
class CreateMyYouthProfileInput(YouthProfileFields):
    approver_email = graphene.String(required=True)
    birth_date = graphene.Date(
        required=True,
        description="The youth's birth date. This is used for example to calculate if the youth is a minor or not.",
    )


class CreateMyYouthProfile(graphene.Mutation):
    class Arguments:
        youth_profile = CreateMyYouthProfileInput(required=True)

    youth_profile = graphene.Field(YouthProfileType)

    @login_required
    @transaction.atomic
    def mutate(self, info, **kwargs):
        input_data = kwargs.get("youth_profile")

        profile = Profile.objects.get(user=info.context.user)

        youth_profile, created = YouthProfile.objects.get_or_create(
            profile=profile, defaults=input_data
        )

        youth_profile.approval_token = uuid.uuid4()
        send_notification(
            email=youth_profile.approver_email,
            notification_type=NotificationType.YOUTH_PROFILE_CONFIRMATION_NEEDED.value,
            context={"youth_profile": youth_profile},
        )
        youth_profile.approval_notification_timestamp = timezone.now()
        youth_profile.save()

        return CreateMyYouthProfile(youth_profile=youth_profile)


class UpdateYouthProfileInput(YouthProfileFields):
    resend_request_notification = graphene.Boolean()


class UpdateMyYouthProfile(graphene.Mutation):
    class Arguments:
        youth_profile = UpdateYouthProfileInput(required=True)

    youth_profile = graphene.Field(YouthProfileType)

    @login_required
    @transaction.atomic
    def mutate(self, info, **kwargs):
        input_data = kwargs.get("youth_profile")
        resend_request_notification = input_data.pop(
            "resend_request_notification", False
        )

        profile = Profile.objects.get(user=info.context.user)
        youth_profile, created = YouthProfile.objects.get_or_create(profile=profile)

        for field, value in input_data.items():
            setattr(youth_profile, field, value)
        youth_profile.save()

        if resend_request_notification:
            youth_profile.approval_token = uuid.uuid4()
            send_notification(
                email=youth_profile.approver_email,
                notification_type=NotificationType.YOUTH_PROFILE_CONFIRMATION_NEEDED.value,
                context={"youth_profile": youth_profile},
            )
            youth_profile.approval_notification_timestamp = timezone.now()
            youth_profile.save()

        return UpdateMyYouthProfile(youth_profile=youth_profile)


class ApproveYouthProfileInput(YouthProfileFields):
    # TODO: Photo usage needs to be present also in Create/Modify, but it cannot be given, if the youth is under 15
    photo_usage_approved = graphene.Boolean()


class ApproveYouthProfile(graphene.Mutation):
    class Arguments:
        approval_token = graphene.String(required=True)
        approval_data = ApproveYouthProfileInput(required=True)

    youth_profile = graphene.Field(YouthProfileType)

    @transaction.atomic
    def mutate(self, info, **kwargs):
        youth_data = kwargs.get("approval_data")
        token = kwargs.get("approval_token")

        youth_profile = YouthProfile.objects.get(approval_token=token)

        for field, value in youth_data.items():
            setattr(youth_profile, field, value)

        youth_profile.approved_time = timezone.now()
        youth_profile.approval_token = ""  # invalidate
        youth_profile.save()
        send_notification(
            email=youth_profile.profile.get_default_email,
            notification_type=NotificationType.YOUTH_PROFILE_CONFIRMED.value,
            context={"youth_profile": youth_profile},
        )
        return ApproveYouthProfile(youth_profile=youth_profile)


class Query(graphene.ObjectType):
    youth_profile = graphene.Field(YouthProfileType, profile_id=graphene.UUID())

    youth_profile_by_approval_token = graphene.Field(
        YouthProfileType, token=graphene.String()
    )

    @login_required
    def resolve_youth_profile(self, info, **kwargs):
        profile_id = kwargs.get("profile_id")

        if profile_id is not None and not info.context.user.is_superuser:
            raise GraphQLError(_("Query by id not allowed for regular users."))

        if info.context.user.is_superuser:
            return YouthProfile.objects.get(profile_id=profile_id)
        return YouthProfile.objects.get(profile__user=info.context.user)

    def resolve_youth_profile_by_approval_token(self, info, **kwargs):
        return YouthProfile.objects.get(approval_token=kwargs.get("token"))


class Mutation(graphene.ObjectType):
    create_my_youth_profile = CreateMyYouthProfile.Field()
    update_my_youth_profile = UpdateMyYouthProfile.Field()
    approve_youth_profile = ApproveYouthProfile.Field()
