import graphene
from django.conf import settings
from django.db.models import CharField, Value
from django.db.models.functions import Concat
from django.utils.translation import override
from django.utils.translation import ugettext_lazy as _
from django_filters import CharFilter, FilterSet, OrderingFilter
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType
from graphene_federation import key
from graphql import GraphQLError
from graphql_jwt.decorators import login_required
from munigeo.models import AdministrativeDivision
from thesaurus.models import Concept

from profiles.decorators import staff_required
from services.consts import SERVICE_TYPES
from services.models import Service, ServiceConnection
from services.schema import AllowedServiceType, ServiceConnectionType

from .consts import ADDRESS_TYPES, EMAIL_TYPES, PHONE_TYPES
from .models import Address, Contact, Email, Phone, Profile
from .utils import create_nested, delete_nested, update_nested


class ConceptType(DjangoObjectType):
    class Meta:
        model = Concept
        fields = ("code",)

    vocabulary = graphene.String()
    label = graphene.String()

    def resolve_vocabulary(self, info, **kwargs):
        return self.vocabulary.prefix


class AdministrativeDivisionType(DjangoObjectType):
    class Meta:
        model = AdministrativeDivision
        fields = ("children", "origin_id", "ocd_id", "municipality")

    type = graphene.String()
    name = graphene.String()

    def resolve_children(self, info, **kwargs):
        return self.children.filter(type__type="sub_district")

    def resolve_type(self, info, **kwargs):
        return self.type.type


with override("en"):
    Language = graphene.Enum(
        "Language", [(l[1].upper(), l[0]) for l in settings.LANGUAGES]
    )
    ContactMethod = graphene.Enum(
        "ContactMethod", [(cm[1].upper(), cm[0]) for cm in settings.CONTACT_METHODS]
    )


class ProfilesConnection(graphene.Connection):
    class Meta:
        abstract = True

    count = graphene.Int()
    total_count = graphene.Int()

    def resolve_count(self, info):
        return self.length

    def resolve_total_count(self, info):
        return self.iterable.model.objects.filter(
            serviceconnection__service__service_type=SERVICE_TYPES[1][0]
        ).count()


class ProfileFilter(FilterSet):
    class Meta:
        model = Profile
        fields = ("first_name", "last_name", "nickname", "email", "phone", "language")

    first_name = CharFilter(lookup_expr="icontains")
    last_name = CharFilter(lookup_expr="icontains")
    nickname = CharFilter(lookup_expr="icontains")
    email = CharFilter(lookup_expr="icontains")
    phone = CharFilter(lookup_expr="icontains")
    language = CharFilter()
    order_by = OrderingFilter(
        fields=(
            ("first_name", "firstName"),
            ("last_name", "lastName"),
            ("nickname", "nickname"),
            ("email", "email"),
            ("phone", "phone"),
            ("language", "language"),
        )
    )


class ContactType(DjangoObjectType):
    class Meta:
        model = Contact
        fields = ("primary",)
        filter_fields = []
        interfaces = (relay.Node,)


class EmailType(ContactType):
    class Meta:
        model = Email
        fields = ("id", "email_type", "primary", "email")
        filter_fields = []
        interfaces = (relay.Node,)


class PhoneType(ContactType):
    class Meta:
        model = Phone
        fields = ("id", "phone_type", "primary", "phone")
        filter_fields = []
        interfaces = (relay.Node,)


class AddressType(ContactType):
    class Meta:
        model = Address
        fields = (
            "id",
            "address_type",
            "primary",
            "address",
            "postal_code",
            "city",
            "country_code",
        )
        filter_fields = []
        interfaces = (relay.Node,)


@key(fields="id")
class ProfileNode(DjangoObjectType):
    class Meta:
        model = Profile
        fields = ("first_name", "last_name", "nickname", "image", "language")
        interfaces = (relay.Node,)
        connection_class = ProfilesConnection
        filterset_class = ProfileFilter

    primary_email = graphene.Field(EmailType)
    primary_phone = graphene.Field(PhoneType)
    primary_address = graphene.Field(AddressType)
    emails = DjangoFilterConnectionField(EmailType)
    phones = DjangoFilterConnectionField(PhoneType)
    addresses = DjangoFilterConnectionField(AddressType)
    language = Language()
    contact_method = ContactMethod()
    service_connections = DjangoFilterConnectionField(ServiceConnectionType)
    concepts_of_interest = graphene.List(ConceptType)
    divisions_of_interest = graphene.List(AdministrativeDivisionType)

    def resolve_service_connections(self, info, **kwargs):
        return ServiceConnection.objects.filter(profile=self)

    def resolve_primary_email(self, info, **kwargs):
        return Email.objects.filter(profile=self, primary=True).first()

    def resolve_primary_phone(self, info, **kwargs):
        return Phone.objects.filter(profile=self, primary=True).first()

    def resolve_primary_address(self, info, **kwargs):
        return Address.objects.filter(profile=self, primary=True).first()

    def resolve_emails(self, info, **kwargs):
        return Email.objects.filter(profile=self)

    def resolve_phones(self, info, **kwargs):
        return Phone.objects.filter(profile=self)

    def resolve_addresses(self, info, **kwargs):
        return Address.objects.filter(profile=self)

    def resolve_concepts_of_interest(self, info, **kwargs):
        return self.concepts_of_interest.all()

    def resolve_divisions_of_interest(self, info, **kwargs):
        return self.divisions_of_interest.all()


AllowedEmailType = graphene.Enum(
    "emailType", [(st[0].upper(), st[0]) for st in EMAIL_TYPES]
)


class EmailInput(graphene.InputObjectType):
    id = graphene.ID()
    email = graphene.String(description="Email address.")
    email_type = AllowedEmailType(description="Email address type.")
    primary = graphene.Boolean(description="Is this primary mail address.")


AllowedPhoneType = graphene.Enum(
    "phoneType", [(st[0].upper(), st[0]) for st in PHONE_TYPES]
)


class PhoneInput(graphene.InputObjectType):
    id = graphene.ID()
    phone = graphene.String(description="Phone number.")
    phone_type = AllowedPhoneType(description="Phone number type.")
    primary = graphene.Boolean(description="Is this primary phone number.")


AllowedAddressType = graphene.Enum(
    "addressType", [(st[0].upper(), st[0]) for st in ADDRESS_TYPES]
)


class AddressInput(graphene.InputObjectType):
    id = graphene.ID()
    address = graphene.String(description="Street address.")
    postal_code = graphene.String(description="Postal code.")
    city = graphene.String(description="City.")
    country_code = graphene.String(description="Country code")
    address_type = AllowedAddressType(description="Address type.")
    primary = graphene.Boolean(description="Is this primary address.")


class ProfileInput(graphene.InputObjectType):
    first_name = graphene.String(description="First name.")
    last_name = graphene.String(description="Last name.")
    nickname = graphene.String(description="Nickname.")
    image = graphene.String(description="Profile image.")
    language = Language(description="Language.")
    contact_method = ContactMethod(description="Contact method.")
    concepts_of_interest = graphene.List(
        graphene.String, description="Concepts of interest."
    )
    divisions_of_interest = graphene.List(
        graphene.String, description="Divisions of interest."
    )
    add_emails = graphene.List(EmailInput, description="Add emails to profile.")
    update_emails = graphene.List(EmailInput, description="Update profile emails.")
    remove_emails = graphene.List(
        graphene.ID, description="Remove emails from profile."
    )
    add_phones = graphene.List(PhoneInput, description="Add phone numbers to profile.")
    update_phones = graphene.List(
        PhoneInput, description="Update profile phone numbers."
    )
    remove_phones = graphene.List(
        graphene.ID, description="Remove phone numbers from profile."
    )
    add_addresses = graphene.List(AddressInput, description="Add addresses to profile.")
    update_addresses = graphene.List(
        AddressInput, description="Update profile addresses."
    )
    remove_addresses = graphene.List(
        graphene.ID, description="Remove addresses from profile."
    )


class CreateProfile(graphene.Mutation):
    class Arguments:
        profile = ProfileInput(required=True)

    profile = graphene.Field(ProfileNode)

    @login_required
    def mutate(self, info, **kwargs):
        profile_data = kwargs.pop("profile")
        concepts_of_interest = profile_data.pop("concepts_of_interest", [])
        divisions_of_interest = profile_data.pop("divisions_of_interest", [])
        nested_to_create = [
            (Email, profile_data.pop("add_emails", [])),
            (Phone, profile_data.pop("add_phones", [])),
            (Address, profile_data.pop("add_addresses", [])),
        ]

        profile = Profile.objects.create(user=info.context.user)
        for field, value in profile_data.items():
            setattr(profile, field, value)
        profile.save()

        for model, data in nested_to_create:
            create_nested(model, profile, data)

        cois = Concept.objects.annotate(
            identifier=Concat(
                "vocabulary__prefix", Value(":"), "code", output_field=CharField()
            )
        ).filter(identifier__in=concepts_of_interest)
        profile.concepts_of_interest.set(cois)
        ads = AdministrativeDivision.objects.filter(ocd_id__in=divisions_of_interest)
        profile.divisions_of_interest.set(ads)

        return CreateProfile(profile=profile)


class UpdateProfile(graphene.Mutation):
    class Arguments:
        profile = ProfileInput(required=True)

    profile = graphene.Field(ProfileNode)

    @login_required
    def mutate(self, info, **kwargs):
        profile_data = kwargs.pop("profile")
        concepts_of_interest = profile_data.pop("concepts_of_interest", [])
        divisions_of_interest = profile_data.pop("divisions_of_interest", [])
        nested_to_create = [
            (Email, profile_data.pop("add_emails", [])),
            (Phone, profile_data.pop("add_phones", [])),
            (Address, profile_data.pop("add_addresses", [])),
        ]
        nested_to_update = [
            (Email, profile_data.pop("update_emails", [])),
            (Phone, profile_data.pop("update_phones", [])),
            (Address, profile_data.pop("update_addresses", [])),
        ]
        nested_to_delete = [
            (Email, profile_data.pop("remove_emails", [])),
            (Phone, profile_data.pop("remove_phones", [])),
            (Address, profile_data.pop("remove_addresses", [])),
        ]

        profile = Profile.objects.get(user=info.context.user)
        for field, value in profile_data.items():
            setattr(profile, field, value)
        profile.save()

        for model, data in nested_to_create:
            create_nested(model, profile, data)

        for model, data in nested_to_update:
            update_nested(model, profile, data)

        for model, data in nested_to_delete:
            delete_nested(model, profile, data)

        cois = Concept.objects.annotate(
            identifier=Concat(
                "vocabulary__prefix", Value(":"), "code", output_field=CharField()
            )
        ).filter(identifier__in=concepts_of_interest)
        profile.concepts_of_interest.set(cois)
        ads = AdministrativeDivision.objects.filter(ocd_id__in=divisions_of_interest)
        profile.divisions_of_interest.set(ads)

        return UpdateProfile(profile=profile)


class Query(graphene.ObjectType):
    profile = graphene.Field(
        ProfileNode,
        id=graphene.Argument(graphene.ID, required=True),
        serviceType=graphene.Argument(AllowedServiceType, required=True),
    )
    my_profile = graphene.Field(ProfileNode)
    concepts_of_interest = graphene.List(ConceptType)
    divisions_of_interest = graphene.List(AdministrativeDivisionType)
    profiles = DjangoFilterConnectionField(
        ProfileNode, serviceType=graphene.Argument(AllowedServiceType, required=True)
    )

    @staff_required(required_permission="view")
    def resolve_profile(self, info, **kwargs):
        try:
            service = Service.objects.get(service_type=kwargs["serviceType"])
            return (
                Profile.objects.filter(serviceconnection__service=service)
                .prefetch_related("concepts_of_interest", "divisions_of_interest")
                .get(pk=relay.Node.from_global_id(kwargs["id"])[1])
            )
        except Profile.DoesNotExist:
            raise GraphQLError(_("Profile not found!"))
        except Service.DoesNotExist:
            raise GraphQLError(_("Service not found!"))

    @login_required
    def resolve_my_profile(self, info, **kwargs):
        return (
            Profile.objects.filter(user=info.context.user)
            .prefetch_related("concepts_of_interest", "divisions_of_interest")
            .first()
        )

    def resolve_concepts_of_interest(self, info, **kwargs):
        return Concept.objects.all()

    def resolve_divisions_of_interest(self, info, **kwargs):
        return AdministrativeDivision.objects.filter(division_of_interest__isnull=False)

    @staff_required(required_permission="view")
    def resolve_profiles(self, info, **kwargs):
        return Profile.objects.filter(
            serviceconnection__service__service_type=kwargs["serviceType"]
        )


class Mutation(graphene.ObjectType):
    create_profile = CreateProfile.Field()
    update_profile = UpdateProfile.Field()
