import pytest
import random
import json
import uuid
from base64 import b64encode
from src.app import create_app
from src.settings import DevConfig
from src.assistant import ds


@pytest.fixture
def app():
    app = create_app(config_object=DevConfig)
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    app.config["TESTING"] = True
    client = app.test_client()

    yield client


@pytest.fixture(scope="session")
def webhook_creds():
    creds_key = ds.key("Credentials", "WebhookCredentials")
    creds_entity = ds.get(creds_key)
    return creds_entity


@pytest.fixture()
def session_path(app):
    project_id = app.config["PROJECT_ID"]
    session_id = uuid.uuid4()
    session_path = f"projects/{project_id}/agent/sessions/{session_id}"
    return session_path


@pytest.fixture
def request_payload(session_path):
    def make_request_payload(intent, params=None, contexts=None, missing=None):
        if params is None:
            params = {}

        context_payload = []

        if contexts is not None:
            for name, params in contexts.items():
                context_payload.append(
                    {
                        "name": session_path + f"/contexts/{name}",
                        "lifespan": 2,
                        "parameters": params,
                    }
                )

        return {
            "session": session_path,
            "queryResult": {
                "queryText": "",
                "parameters": params,
                "allRequiredParamsPresent": (missing is None),
                "intent": {"displayName": intent},
                "outputContexts": context_payload,
            },
            "originalDetectIntentRequest": {},
        }

    return make_request_payload


@pytest.fixture
def make_request(client, request_payload, parse_response, webhook_creds):
    username, pwd = webhook_creds["username"], webhook_creds["password"]
    auth_string = f"{username}:{pwd}"
    auth_bytes = auth_string.encode()
    encoded_auth = b64encode(auth_bytes).decode("ascii")
    headers = {"Authorization": f"Basic {encoded_auth}"}

    def make_fa_request(intent, params=None, contexts=None, missing=None):
        payload = request_payload(intent, params, contexts, missing)
        resp = client.post("/assist", data=json.dumps(payload), headers=headers)
        fulfillment_text = parse_response(resp)
        return fulfillment_text

    return make_fa_request


@pytest.fixture
def parse_response():
    def parse_ful_text(response):
        data = response.json
        response_types = ["basicCard", "listSelect", "suggestions", "linkOutSuggestion"]

        summary = {}
        summary["text"] = data["fulfillmentText"]
        msgs = []
        for m in data["fulfillmentMessages"]:
            for r in response_types:
                if r in list(m.keys()):
                    msgs.append(r)
            # if m.get("platform"):
            #     m.pop("platform")
            # msgs.append(list(m.keys())[0])

        summary["msgs"] = msgs

        context_names = []
        for c in data["outputContexts"]:
            context_names.append(c["name"].split("contexts/")[1])

        summary["contexts"] = context_names
        summary["event"] = data["followupEventInput"]
        return summary

    return parse_ful_text


@pytest.fixture
def fallback_responses():
    return [
        "What was that?",
        "I didn't quite catch that.",
        "Sorry, I didn't get that. Can you rephrase?",
        "Sorry, what was that?",
        "I missed that, say that again?",
        "Sorry I missed what you said",
        "Sorry, I missed that. Mind rephrasing your question?",
        "I missed that, one more time?",
    ]


# NOTE: testing's GIS search returns no results when either
# 1. The city is included
# 2. The zip code is provided, but not the state

# Search results are returned only for the street address portion
# as well if the state or state + zip code are included

# works:
# 2455 Black Oak Rd
# 2455 Black Oak Rd, CA
# 2455 Black Oak Rd, CA 95602

# doesn't work
# 2455 Black Oak Rd, Auburn, CA 95602
# 2455 Black Oak Rd, Auburn, CA
# 2455 Black Oak Rd, Auburn
# 2455 Black Oak Rd, 95602


@pytest.fixture
def within_jurisdiction_unincorporated_address():
    # In County jurisdiction, unincorporated:
    return random.choice(
        [
            "3091 County Center Dr",  # "", Auburn, CA 95603",
            "2455 Black Oak Rd",  # ", Auburn" #", CA 95602",
            "251 N Lake Blvd",  # ", Tahoe City, CA 96145", # Tahoe zoning
        ]
    )


@pytest.fixture
def within_county_outside_jurisdiction_incorporated_address():
    # Within County, outside county jurisdiction within incorporated cities
    return random.choice(
        [
            "2620 Sunset Blvd #1",  # ", Rocklin, CA 95677",
            "1600 Eureka Rd",  # , Roseville, CA 95661',
            "948 Lincoln Way suite a",  # , Auburn, CA 95603',
        ]
    )


@pytest.fixture
def outside_county_outside_jurisdiction_address():
    # Outside County Jurisdiction, outside testing County:
    return random.choice(
        [
            "10685 Northwoods Blvd",  # , Truckee, CA 96161',
            "6529 Pony Express Trail",  # , Pollock Pines, CA 95726',
            "1 Red Hawk Pkwy",  # , testingville, CA 95667',
        ]
    )


@pytest.fixture
def search_result_sample():
    search_sample = {
        "count": 1,
        "duration": 5.0003,
        "features": [
            {
                "mapServiceId": "LIS_Base-36",
                "geometry": {
                    "rings": [
                        [
                            [-13_477_780.316_628_227, 4_712_478.955_769_758],
                            [-13_477_780.010_062_069, 4_712_478.697_192_721],
                            [-13_477_803.721_896_98, 4_712_457.905_819_176],
                            [-13_477_809.661_206_372, 4_712_452.696_791_911_5],
                            [-13_477_826.478_767_019, 4_712_437.874_893_189],
                            [-13_477_861.149_794_96, 4_712_477.156_342_102],
                            [-13_477_820.249_928_21, 4_712_512.636_416_955],
                            [-13_477_780.316_628_227, 4_712_478.955_769_758],
                        ]
                    ],
                    "spatialReference": {"wkid": 102_100},
                },
                "highlights": {},
                "score": 30,
                "layerId": "0",
                "attributes": {
                    "OWNER1": "HOFFMAN VELANDA & HOFFMAN ORRIN P",
                    "FULLSTREET": "13141 ATHENA WAY",
                    "OWNER2": None,
                    "STR_SQFT": 2304,
                    "SUBAREA": None,
                    "LANDVALUE": 124_848,
                    "CityName": "Unincorporated",
                    "TOWNCENTER": None,
                    "NEIGHBORHOODCODE": "4050",
                    "OVERFLIGHT_ZONE": "Y",
                    "Assessment": "https://common1.mptsweb.com/MegabyteCommonSite/(S(d4zejk0noyscio3llstxual4))/PublicInquiry/Inquiry.aspx?CN=testing&SITE=Public&DEPT=Asr&PG=AsrMain&Asmt=052-172-015-000",
                    "ADR1": "13141 ATHENA WAY",
                    "PAS_NAME": None,
                    "ADR2": "AUBURN CA 95603",
                    "OBJECTID": 131_456,
                    "ASMT": "052172015000",
                    "FID_AO": 1,
                    "ZONINGLINK": "http://qcode.us/codes/testingcounty/view.php?topic=17-2-iv-17_50-17_50_010&frames=on",
                    "COMMUNITY": "Auburn",
                    "FIRE": "NORTH AUBURN/OPHIR FIRE (CSA 28 ZONE 193)",
                    "TTC": "https://common3.mptsweb.com/MBC/testing/tax/main/052172015000/2018/0000",
                    "APN": "052-172-015-000",
                    "MAC_DESC": "North Auburn Municipal Advisory Council",
                    "BOS": "SUPERVISORIAL DISTRICT 5",
                    "APPRAISERID": "DAD",
                    "DISTRICT_1": None,
                    "ZIP": "95603",
                    "OVERLAY": None,
                    "TRA": "056041",
                    "SPECIALAREA": None,
                    "HS_DIST": "testing UNION HIGH SCHOOL DISTRICT",
                    "GIS_ACRES": 0.4519,
                    "STATE": "CA",
                    "ZONING_TAHOE": None,
                    "LU_DESIGNATION": "Low Medium Density Residential 2 - 5 DU/Ac.",
                    "COMMUNITY_PLAN_AREA": "Auburn/Bowman Community Plan",
                    "ZONING": "RS-AG-AO",
                    "CITY": "AUBURN",
                    "SCHOOL": "AUBURN UNION SCHOOL DISTRICT",
                    "TrafficFeeDistrict": "Auburn / Bowman",
                    "ASMT_DESC": "PAR 2 PMOR 34-156",
                    "USE_CD_N": "SINGLE FAM RES, HALF PLEX",
                    "COLLEGE": "SIERRA COLLEGE",
                    "OVERLAY2": None,
                    "BkPg_Url": "http://www.testing.ca.gov/ASR/Maps/052/052-17.pdf",
                    "STRUCTURE": 523_210,
                },
                "id": "131456",
            }
        ],
    }
    return search_sample
