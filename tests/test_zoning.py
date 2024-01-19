from random import choice


def test_zoning_by_address_no_address(make_request):
    fulfill = make_request("Zoning-by-address", {"location": ""})
    assert "Can I have the street address" in fulfill["text"]


def test_zoning_missing_number(make_request):
    fulfill = make_request(
        "Zoning-by-address", {"location": {"street-address": "bell road"}}
    )
    assert "I'll need the full street address" in fulfill["text"]


def test_zoning_address_in_jurisdiction(make_request):
    addresses = [
        {"street-address": "2700 bell road"},
        {"street-address": "9469 Burns court"},
    ]

    fulfill = make_request("Zoning-by-address", {"location": choice(addresses)})
    assert "This address appears to fall within the" in fulfill["text"]
    assert "basicCard" in fulfill["msgs"]


def test_zoning_address_multiple_zones(make_request):
    addresses = [
        {"street-address": "3091 County Center Drive"},
        {"street-address": "2455 Black Oak Rd"},
    ]
    fulfill = make_request("Zoning-by-address", {"location": choice(addresses)})
    assert "This address appears to fall under the" in fulfill["text"]
    assert "listSelect" in fulfill["msgs"]


def test_zoning_address_tahoe_zone(make_request):
    addresses = [{"street-address": "251 N Lake Blvd"}]
    fulfill = make_request("Zoning-by-address", {"location": choice(addresses)})
    assert "This address appears to fall under Tahoe" in fulfill["text"]
    assert "basicCard" in fulfill["msgs"]


def test_zoning_address_outside_jurisdiction(make_request):
    addresses = [
        {"street-address": "10685 Northwoods Blvd"},
        {"street-address": "6529 Pony Express Trail"},
        {"street-address": "1 Red Hawk Pkwy"},
    ]

    fulfill = make_request("Zoning-by-address", {"location": choice(addresses)})
    assert "because it appears to be outside of Plasir jurisdiction" in fulfill["text"]
