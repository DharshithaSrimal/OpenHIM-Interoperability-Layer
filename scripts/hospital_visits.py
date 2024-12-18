from dotenv import load_dotenv, dotenv_values
import os
import json
import requests
from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth
from dhis2 import Api

tei_id, org_unit = None, None

config = {
    **dotenv_values(".env.shared")
}

load_dotenv()  # Load environment variables from .env file

# Keycloak
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
GRANT_TYPE = os.getenv("GRANT_TYPE")
# FHIR
FHIR_SERVER_URL = os.getenv("FHIR_SERVER_URL")

# DHIS2
DHIS2_USER = os.getenv("DHIS2_USER")
DHIS2_PASS = os.getenv("DHIS2_PASS")
DHIS2_SERVER_URL = os.getenv("DHIS2_SERVER_URL")
api = Api(DHIS2_SERVER_URL, DHIS2_USER, DHIS2_PASS)

# Metadata
UNIQUE_ID = config["UNIQUE_ID"]
TRACKED_ENTITY_TYPE = config["TRACKED_ENTITY_TYPE"]
TEI_ATTR_PHN = config['TEI_ATTR_PHN']
screening_phn = None
# Program Stages
HLC_SCREENING = config["HLC_SCREENING"]
FOLLOWUP = config["FOLLOWUP"]
tei_event_followup = ("Phone_Calls_Completed", "Home_Visits_Completed", "HLC_Visit_Completed")

# Date range to loop over (2022-09-15 to 2022-09-30)
start_date_range = datetime(2022, 9, 15)
end_date_range = datetime(2022, 9, 30)

# Safely extract the value with nested dictionaries and lists
def get_nested_value(data, keys, default=None):
    for key in keys:
        if isinstance(data, list):
            # Ensure we're within bounds
            data = data[key] if len(data) > key else None
        elif isinstance(data, dict):
            data = data.get(key)
        if data is None:
            return default
    return data

# Loop over each day in the date range
current_date = start_date_range
while current_date <= end_date_range:
    START_DATE = current_date.strftime("%Y-%m-%dT00:00:00Z")
    END_DATE = (current_date + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
    print(f"Processing date range: {START_DATE} to {END_DATE}")
    
    # Get Keycloak token
    token_response = requests.post(KEYCLOAK_URL, data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": GRANT_TYPE
    })
    ACCESS_TOKEN = token_response.json().get("access_token")

    # Encounters count
    encounters = requests.get(
    f"{FHIR_SERVER_URL}/fhir/Encounter?type=facility_visit&_count=0&_lastUpdated=ge{START_DATE}&_lastUpdated=le{END_DATE}",
    headers={"Authorization": f"Bearer {ACCESS_TOKEN}"})
    encounter_count = encounters.json().get("total")

    # FHIR encounters
    encounter_response = requests.get(
        f"{FHIR_SERVER_URL}/fhir/Encounter?type=facility_visit&_lastUpdated=ge{START_DATE}&_lastUpdated=le{END_DATE}&_sort=_lastUpdated&_count={encounter_count}",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
    )

    encounter_response_data = encounter_response.json()
    encounter_response_bundle = encounter_response_data.get("entry", [])

    for encounter_info in encounter_response_bundle:
        patient_id = encounter_info["resource"]["subject"]["reference"].split('/')[-1]
        print(patient_id)
        patient = None
        if patient_id:
            patient = requests.get(
                f"{FHIR_SERVER_URL}/fhir/Patient/{patient_id}",
                headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
            )

        # Get TEI
        params = {
            'fields': 'trackedEntityInstance,attributes[attribute,value],orgUnit',
            'ouMode': 'ACCESSIBLE',
            'trackedEntityType': TRACKED_ENTITY_TYPE,
            'filter': UNIQUE_ID + ':eq:' + patient_id
        }

        tei_id, org_unit = None, None
        try:
            tei_response = api.get('trackedEntityInstances', params=params)
            tei_response_json = tei_response.json()
            # Get TEI and org unit id
            if tei_response_json['trackedEntityInstances']:
                tei_id = tei_response_json['trackedEntityInstances'][0]['trackedEntityInstance']
                org_unit = tei_response_json['trackedEntityInstances'][0]['orgUnit']
            else:
                tei_id, org_unit = None, None
        except Exception as e:
            print(f"TEI Fetch Failed: {str(e)}")

        # if tei_id is None and org_unit is None:
        payload = {
                "resourceType": "Bundle",
                "type": "batch",
                "entry": [
                    {"request": {"method": "GET", "url": f"Patient/{patient_id}"}},
                    {"request": {"method": "GET", "url": f"Encounter?subject=Patient/{patient_id}&_lastUpdated=ge{START_DATE}&_lastUpdated=le{END_DATE}"}},
                    {"request": {"method": "GET", "url": f"Observation?subject=Patient/{patient_id}&_lastUpdated=ge{START_DATE}&_lastUpdated=le{END_DATE}"}},
                    {"request": {"method": "GET", "url": f"Condition?subject=Patient/{patient_id}&_lastUpdated=ge{START_DATE}&_lastUpdated=le{END_DATE}"}}
                ]
            }
        # Send the POST request
        post_response = requests.post(
            f"{FHIR_SERVER_URL}/fhir",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ACCESS_TOKEN}"
            }
        )

        bundle = post_response.json()

        # Check if the response contains RiskAssessment resources and extract values
        if "entry" in bundle:
            for entry in bundle["entry"]:
                # Extract RiskAssessment resource
                if entry["resource"]["resourceType"] == "Encounter":
                    encounter_resource = entry["resource"]
                    event_date = encounter_resource.get("period").get("start")

                if entry["resource"]["resourceType"] == "Patient":   
                    patient_response = entry["resource"] 
                    screening_phn = None
                    # Define the keys for the nested extraction
                    screening_phn_keys = ["identifier", 0, "value"]
                    # Extract the screening phn
                    screening_phn = get_nested_value(patient_response, screening_phn_keys, default="N/A")
                    params = {
                        'fields': 'trackedEntityInstance,attributes[attribute,value]',
                        'ouMode': 'ACCESSIBLE',
                        'trackedEntityType': TRACKED_ENTITY_TYPE,
                        'filter': TEI_ATTR_PHN + ':eq:' + screening_phn
                    }
                    tei_response = api.get('trackedEntityInstances', params=params)
                    # Extract the Practitioner Location code
                    location_keys = ["meta", "tag", 4, "code"]
                    location_code = get_nested_value(patient_response, location_keys, default="N/A")
                if entry["resource"]["resourceType"] == "Condition":   
                    patient_response = entry["resource"] 
                    # Define the keys for the nested extraction
                    screening_phn_keys = ["identifier", 0, "value"]
                    # Extract the screening phn
                    screening_phn = get_nested_value(patient_response, screening_phn_keys, default="N/A")
                    # Extract the Practitioner Location code
                    location_keys = ["meta", "tag", 4, "code"]
                    location_code = get_nested_value(patient_response, location_keys, default="N/A")
                if entry["resource"]["resourceType"] == "Observation":   
                    patient_response = entry["resource"] 
                    # Define the keys for the nested extraction
                    screening_phn_keys = ["identifier", 0, "value"]
                    # Extract the screening phn
                    screening_phn = get_nested_value(patient_response, screening_phn_keys, default="N/A")
                    # Extract the Practitioner Location code
                    location_keys = ["meta", "tag", 4, "code"]
                    location_code = get_nested_value(patient_response, location_keys, default="N/A")
           
        # Fetch TEI
        params = {
            'fields': 'trackedEntityInstance,attributes[attribute,value],orgUnit',
            'ouMode': 'ACCESSIBLE',
            'trackedEntityType': config[TRACKED_ENTITY_TYPE],
            'filter': config[TEI_ATTR_PHN] + ':eq:' + screening_phn
        }
        tei_response = api.get('trackedEntityInstances', params=params)
        tei_response_json = tei_response.json()

        # Get TEI and org unit id
        if tei_response_json['trackedEntityInstances']:
            tei_id = tei_response_json['trackedEntityInstances'][0]['trackedEntityInstance']
            org_unit = tei_response_json['trackedEntityInstances'][0]['orgUnit']
        else:
            tei_id = ""
            org_unit = ""
    # Move to the next day
    current_date += timedelta(days=1)
