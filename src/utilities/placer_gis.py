import requests
from flask import current_app
import logging

OUTSIDE_JURISDICTION = 0
WITHIN_JURISDICTION = 1

UNINCORPORATED = "UNINCORPORATED"

url_sample = "?f=json&searchText=13141%20Athena%20way&contains=true&returnGeometry=true&returnHighlights=false&returnIdsOnly=false&returnCountOnly=false&envelope=-13526820.29436793%2C4631421.509117115%2C-13337867.960447064%2C4811507.147756904&outSR=%7B%22wkid%22%3A102100%7D&maxResults=100&layers=LIS_Base-36(include%3A0)&dojo.preventCache=153920346476"

SEARCH_URL = (
    "http://maps.testing.ca.gov/Geocortex/Essentials/REST/sites/LIS_Public/search"
)


SEARCH_PARAMS = {
    "f": "json",
    "searchText": "13141 Athena way",
    "contains": True,
    "returnGeometry": True,
    "returnHighlights": False,
    "returnIdsonly": False,
    "returnCounOnly": False,
    "envelope": "-13526820.29436793,4631421.509117115,-13337867.960447064,4811507.147756904",
    "outSr": '{"wkid":102100}',
    "maxResults": 100,
    "layers": "LIS_Base-36(include:0)",
    # "dojo.preventCache":153920346476
}


def get_search_params(address):
    params = SEARCH_PARAMS.copy()
    params["searchText"] = address
    return params


def submitSearch(address):
    current_app.logger.debug(f"Searching address {address}")
    params = get_search_params(address)
    resp = requests.get(SEARCH_URL, params=params)
    resp.raise_for_status()
    return resp.json()


def jurisdiction_for_data(data):
    current_app.logger.debug("getting jurisdiction from gis_response")

    if data.get("features") is None:
        return OUTSIDE_JURISDICTION
    elif len(data["features"]) == 0:
        return OUTSIDE_JURISDICTION

    f = data["features"][0]

    if f.get("attributes") is None:
        return OUTSIDE_JURISDICTION

    city_name = f["attributes"].get("CityName")
    if city_name is None:
        return OUTSIDE_JURISDICTION
    elif city_name.upper() == UNINCORPORATED:
        return UNINCORPORATED
    else:
        return WITHIN_JURISDICTION


def zoning_for_data(data):
    zoning_info = {}
    jurisdiction = jurisdiction_for_data(data)

    if jurisdiction == OUTSIDE_JURISDICTION:
        current_app.logger.info("No zone info because outside of jurisdiction")
        return OUTSIDE_JURISDICTION, zoning_info

    else:
        current_app.logger.info("Address in jurisdiction, getting zone data")
        a = data["features"][0]["attributes"]
        zoning_info = {
            "code": a.get("ZONING"),
            "url": a.get("ZONINGLINK"),
            "overflight": a.get("OVERFLIGHT_ZONE"),
            "tahoe_zoning": a.get("ZONING_TAHOE"),
            "bkpg_url": a.get("BkPg_Url"),
        }
        current_app.logger.debug(zoning_info)
        return jurisdiction, zoning_info


def get_jurisdiction(address):
    current_app.logger.debug(f"getting jurisdiction for address {address}")
    params = get_search_params(address)
    resp = requests.get(SEARCH_URL, params=params, timeout=3.0)
    resp.raise_for_status()
    data = resp.json()
    return jurisdiction_for_data(data)


def get_zoning(address):
    current_app.logger.info(f"Getting zoning info for {address}")
    params = get_search_params(address)
    resp = requests.get(SEARCH_URL, params=params, timeout=0.3)
    resp.raise_for_status()
    data = resp.json()
    return zoning_for_data(data)
