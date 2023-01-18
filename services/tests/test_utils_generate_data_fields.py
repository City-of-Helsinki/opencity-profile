import pytest

from services.models import AllowedDataField
from services.utils import generate_data_fields


def _get_initial_spec():
    return [
        {
            "field_name": "name",
            "translations": [
                {"code": "fi", "label": "Nimi"},
                {"code": "sv", "label": "Namn"},
            ],
        },
        {
            "field_name": "email",
            "translations": [
                {"code": "en", "label": "Email"},
                {"code": "fi", "label": "Sähköposti"},
                {"code": "sv", "label": "Epost"},
            ],
        },
    ]


def _test_changed_spec(new_spec):
    for spec in _get_initial_spec(), new_spec:
        generate_data_fields(spec)

        allowed_data_fields = AllowedDataField.objects.all()
        assert len(allowed_data_fields) == len(spec)

        previous_order = -1

        for value in spec:
            field = allowed_data_fields.filter(field_name=value["field_name"]).first()
            assert field is not None

            assert field.order > previous_order
            previous_order = field.order

            for translation in value["translations"]:
                field.set_current_language(translation["code"])
                assert field.label == translation["label"]

            expected_lang_codes = {tr["code"] for tr in value["translations"]}
            actual_lang_codes = set(field.get_available_languages())
            assert expected_lang_codes == actual_lang_codes


def test_unchanged_configuration_changes_nothing():
    _test_changed_spec(_get_initial_spec())


def test_adding_a_new_field():
    new_spec = _get_initial_spec() + [
        {
            "field_name": "address",
            "translations": [
                {"code": "en", "label": "Address"},
                {"code": "fi", "label": "Osoite"},
                {"code": "sv", "label": "Adress"},
            ],
        }
    ]

    _test_changed_spec(new_spec)


@pytest.mark.parametrize("num_removed", [1, 2])
def test_removing_a_field(num_removed):
    new_spec = _get_initial_spec()[num_removed:]

    _test_changed_spec(new_spec)


def test_add_new_translations_to_an_existing_field():
    new_spec = _get_initial_spec()
    new_spec[0]["translations"].append({"code": "en", "label": "Name"})
    new_spec[0]["translations"].append({"code": "no", "label": "Navn"})

    _test_changed_spec(new_spec)


def test_update_translations_for_an_existing_field():
    new_spec = _get_initial_spec()
    new_spec[0]["translations"][0].update({"label": "Uusi nimi"})
    new_spec[0]["translations"][1].update({"label": "Ny namn"})

    _test_changed_spec(new_spec)


def test_remove_translations_from_an_existing_field():
    new_spec = _get_initial_spec()
    new_spec[1]["translations"].pop(2)
    new_spec[1]["translations"].pop(0)

    _test_changed_spec(new_spec)


def test_change_order_of_fields():
    new_spec = _get_initial_spec()
    new_spec.reverse()

    _test_changed_spec(new_spec)
