from dotenv import load_dotenv, dotenv_values
import os
import json
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth 
# Install External Libraries
import subprocess
import sys

def get_tracked_entity_instance(patient_id):
    print("tei data", patient_id)
    params = {
        'fields': 'trackedEntityInstance,attributes[attribute,value],orgUnit',
        'ouMode': 'ACCESSIBLE',
        'trackedEntityType': TRACKED_ENTITY_TYPE,
        'filter': f"{UNIQUE_ID}:eq:{patient_id}"
    }
    try:
        response = api.get('trackedEntityInstances', params=params)
        tei_data = response.json().get('trackedEntityInstances', [])
        if tei_data:
            return tei_data[0]["trackedEntityInstance"], tei_data[0]["orgUnit"]
    except Exception as e:
        print(f"TEI Fetch Failed: {str(e)}")
    return None, None

# End of installing External Libraries
from dhis2 import Api
load_dotenv()  # Load environment variables from .env file
LOG_FILE_PATH = "tei_errors.log"
# FHIR
FHIR_SERVER_URL = os.getenv("FHIR_SERVER_URL")

# Keycloak
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
GRANT_TYPE = os.getenv("GRANT_TYPE")

# START_DATE = datetime.now().strftime("%Y-%m-%dT00:00:00Z")
# END_DATE = datetime.now().strftime("%Y-%m-%dT23:59:59Z")"

# END_DATE = "2022-02-10T00:00:00"
# START_DATE = "2020-05-30T00:00:00"
# END_DATE = "2021-01-01T00:00:00"
# START_DATE = "2022-02-28T00:00:00"
# END_DATE = "2022-04-30T00:00:00"
START_DATE = "2022-04-30T00:00:00"
END_DATE = "2022-05-30T00:00:00"

# DHIS2
DHIS2_USER = os.getenv("DHIS2_USER")
DHIS2_PASS = os.getenv("DHIS2_PASS")
DHIS2_SERVER_URL = os.getenv("DHIS2_SERVER_URL")

# OpenHIM
OPENHIM_CLIENT = os.getenv("OPENHIM_CLIENT_ID")
OPENHIM_CLIENT_PASS = os.getenv("OPENHIM_CLIENT_PASS")

locationArray = {}
MAPPING_RESULTS = {}
count = 0

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

def log_error(message):
    with open(LOG_FILE_PATH, "a") as log_file:
        log_file.write(f"{datetime.now()} - {message}\n")

# Intermediate
config = {
    **dotenv_values(".env.shared")
}
dm_risk, htn_risk = None, None
high = "High"
low = "Low"
risk = ""
consent = None
screening_required = None
referral_place = ""
TRACKED_ENTITY_TYPE = config["TRACKED_ENTITY_TYPE"]
TEI_ATTR_PHN = config["TEI_ATTR_PHN"]
tei_id = ""
tei_ou = ""
tei_event_followup = ("Registration_Completed","Screening_Completed") 
HLC_SCREENING = config["HLC_SCREENING"]
FOLLOWUP = config["FOLLOWUP"]
program_stage = (HLC_SCREENING, FOLLOWUP)
ou_id = ""
status = ("ACTIVE", "COMPLETED")
UNIQUE_ID = config["UNIQUE_ID"]

api = Api(DHIS2_SERVER_URL, DHIS2_USER, DHIS2_PASS)
screening_phn = ""
org_unit = ""

# Get Keycloak token
token_response = requests.post(KEYCLOAK_URL, data={
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "grant_type": GRANT_TYPE
})
ACCESS_TOKEN = token_response.json()["access_token"]
##### FHIR Location setup #####

# Send FHIR request to get all locations and process it in a loop
locations_response = requests.get(
    f"{FHIR_SERVER_URL}/fhir/Location?_count=100",
    headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
)
locations_data = locations_response.json()["entry"]
for location_info in locations_data:
    location_id = location_info["resource"]["id"]
    location_name = location_info["resource"]["name"]
    locationArray[location_id] = location_name

##### End FHIR Location setup #####

##### Org units #####

with open("orgunits.json") as f:
    orgunits = json.load(f)

##### End org units #####

##### Patient setup #####

encounters = requests.get(
    f"{FHIR_SERVER_URL}/fhir/Encounter?_count=400000&date=ge{START_DATE}&date=le{END_DATE}&type=facility_visit",
    headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
)
encounters_data = encounters.json()
encounters_bundle = encounters_data.get("entry", [])

for encounter_info in encounters_bundle:

    encounter_id = encounter_info["resource"]["id"]
    patient_id = encounter_info["resource"]["subject"]["reference"].split('/')[-1]

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

        tei_id, org_unit = "", ""
        try:
            tei_response = api.get('trackedEntityInstances', params=params)
            tei_response_json = tei_response.json()
            # Get TEI and org unit id
            if tei_response_json['trackedEntityInstances']:
                tei_id = tei_response_json['trackedEntityInstances'][0]['trackedEntityInstance']
                org_unit = tei_response_json['trackedEntityInstances'][0]['orgUnit']
            else:
                tei_id, org_unit = "", ""
        except Exception as e:
            print(f"TEI Fetch Failed: {str(e)}")

    patient_ = requests.get(
    f"{FHIR_SERVER_URL}/fhir/Patient/{patient_id}",
    headers={"Authorization": f"Bearer {ACCESS_TOKEN}"})
    patient_resource = patient_.json()
    
    # patient_location = next((tag["code"] for tag in patient_resource["meta"]["tag"] if tag["system"] == "https://smartregister.org/location-tag-id"), None)
    if tei_id == "":
        # Calculate age from birthday
        birth_date = patient_resource["birthDate"]
        current_year = datetime.now().year
        birth_year = datetime.strptime(birth_date, "%Y-%m-%d").year
        age = current_year - birth_year

        # Extract the Patient origin
        patient_origin = next((tag["code"] for tag in patient_resource["meta"]["tag"] if tag["system"] == "https://smartregister.org/app-version"), None)
        
        # Construct the updated patient resource - set ouid
        patient_resource["meta"]["tag"] = [{"system": "https://smartregister.org/location-tag-id", "code": ou_id}]
        app_version = next((tag["code"] for tag in patient_resource["meta"]["tag"] if tag["system"] == "https://smartregister.org/app-version"), None)
        phn = None
        try:
        # Send the updated patient resource to the OpenHIM Mapping Mediator
            mapping_response = requests.post(
                "http://localhost:5001/fhir-to-tei",
                headers={"Content-Type": "application/json"},
                auth=HTTPBasicAuth(OPENHIM_CLIENT, OPENHIM_CLIENT_PASS),
                json=patient_resource
            )
            if patient_origin == "2.0.0-diabetesCompass":
                data_origin = "Community_Screening_App"
            elif patient_origin == "Not defined":
                data_origin = "Clinic_App"
            
                mapping_result = mapping_response.json()
                if mapping_response.status_code == 200:
                    # Update the age attribute in the mapping result
                    age_group = "Ageless45" if age < 45 else "45to54" if age < 55 else "55to64" if age < 65 else "65orAbove"
                    mapping_result["attributes"].append({"attribute": "QUS2rM78s6F", "value": str(age)})
                    mapping_result["attributes"].append({"attribute": "cTFwAAW0and", "value": age_group})
                    mapping_result["attributes"].append({"attribute": "Nymn5TH8GRu", "value": patient_resource["gender"].capitalize()})
                    mapping_result["attributes"].append({"attribute": "QmkJzDbUkSC", "value": data_origin})
                    current_date = encounter_info["resource"]["period"]["start"]
                    # Add orgUnit to enrollments
                    # ou = mapping_result.get("orgUnit")
                    ou = "EF5pbiM7RSX"
                    mapping_result["orgUnit"] = ou
                    mapping_result["enrollments"][0]["orgUnit"] = ou
                    # Add incidentDate to enrollments
                    mapping_result["enrollments"][0]["enrollmentDate"] = current_date
                    mapping_result["enrollments"][0]["incidentDate"] = current_date
                    try:
                        phn = mapping_result["attributes"][1]["value"]
                        if not phn:
                            print("PHN value is missing in the attributes list.")
                    except (IndexError, KeyError) as e:
                        print(f"Error: Could not extract PHN - {str(e)}")
                        log_error(f"Error: Resource id {mapping_result["attributes"][0]["value"]}")
                        phn = None
                else:
                    print(f"Error: {mapping_response.status_code}, {mapping_response.text}")
                
                if phn != None:
                    params = {
                        'fields': 'trackedEntityInstance,attributes[attribute,value]',
                        'ouMode': 'ACCESSIBLE',
                        'trackedEntityType': TRACKED_ENTITY_TYPE,
                        'filter': TEI_ATTR_PHN + ':eq:' + phn
                    }
                    tei_response = api.get('trackedEntityInstances', params=params)
                    tei_response_json = tei_response.json()
                
                    if not tei_response_json['trackedEntityInstances']:
                        try:
                            tei_post_response = api.post('trackedEntityInstances', json=mapping_result)
                            if tei_post_response.status_code != 200:
                                print(f"TEI Registration failed: ", tei_post_response.json(), " Encounter: ", encounter_id)
                            else:
                                print("Success")
                        except Exception as e:
                            print(f"TEI Registration Failed: {str(e)}")
                            error_message = f"TEI Registration Failed: {str(e)}, Encounter: {encounter_id}"
                            log_error(error_message)
        
        except Exception as e:
                            print(f"OpenHIM Failed: {encounter_id}")
                            error_message = f"OpenHIM Failed: Encounter: {encounter_id}"
                            log_error(error_message)
print(" Done!")
