from src.utilities.testing_gis import (
    UNINCORPORATED,
    WITHIN_JURISDICTION,
    OUTSIDE_JURISDICTION,
    get_jurisdiction,
    jurisdiction_for_data,
)


def test_address_unincorporated_within_jurisdiction(
    within_jurisdiction_unincorporated_address, app
):

    assert (
        get_jurisdiction(within_jurisdiction_unincorporated_address) == UNINCORPORATED
    )


def test_address_outside_jurisdiction(outside_county_outside_jurisdiction_address, app):
    assert (
        get_jurisdiction(outside_county_outside_jurisdiction_address)
        == OUTSIDE_JURISDICTION
    )


def test_addresses_within_county_outside_jurisdiction(
    within_county_outside_jurisdiction_incorporated_address, app
):
    assert (
        get_jurisdiction(within_county_outside_jurisdiction_incorporated_address)
        == OUTSIDE_JURISDICTION
    )


def test_search_sample_returns_within_jurisdiction(search_result_sample, app):
    assert jurisdiction_for_data(search_result_sample) == UNINCORPORATED
