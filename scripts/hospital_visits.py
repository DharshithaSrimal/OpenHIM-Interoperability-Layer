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
start_date_range = datetime(2000, 1, 1)
end_date_range = datetime(2020, 1, 1)

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
# current_date = start_date_range
# START_DATE = current_date.strftime("%Y-%m-%dT00:00:00Z")
# END_DATE = (current_date + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
START_DATE = "2000-01-01T00:00:00"
END_DATE = "2022-05-10T00:00:00"
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
f"{FHIR_SERVER_URL}/fhir/Encounter?type=facility_visit&_count=0&date=ge{START_DATE}&date=le{END_DATE}&_tag=PKT0010397",
headers={"Authorization": f"Bearer {ACCESS_TOKEN}"})
encounter_count = encounters.json().get("total")
print("Count: ", encounter_count)
# FHIR encounters
encounter_response = requests.get(
    f"{FHIR_SERVER_URL}/fhir/Encounter?type=facility_visit&date=ge{START_DATE}&date=le{END_DATE}&_count={encounter_count}&_tag=PKT0010397&_sort=date",
    headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
)

encounter_response_data = encounter_response.json()
encounter_response_bundle = encounter_response_data.get("entry", [])

for encounter_info in encounter_response_bundle:
        patient_id = encounter_info["resource"]["subject"]["reference"].split('/')[-1]
        print(patient_id)
        
        # Extract encounter date and set time range
        encounter_start_date = encounter_info["resource"]["period"]["start"].split('T')[0].strip()
        print(encounter_start_date)
        encounter_date = f"{encounter_start_date}T00:00:00".strip()
        encounter_dayend = f"{encounter_start_date}T23:59:59".strip()
        print("start: ", encounter_date, " end: ", encounter_dayend)
        # encounter_end = encounter_info["resource"]["period"]["end"].split('T')
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

        tei_id, org_unit,enrollment = "", "", ""
        try:
            tei_response = api.get('trackedEntityInstances', params=params)
            tei_response_json = tei_response.json()
            # Get TEI and org unit id
            if tei_response_json['trackedEntityInstances']:
                tei_id = tei_response_json['trackedEntityInstances'][0]['trackedEntityInstance']
                org_unit = tei_response_json['trackedEntityInstances'][0]['orgUnit']
            else:
                tei_id, org_unit = "", ""
            if (tei_id):
                # Fetch TEI
                params = {
                                'fields': 'trackedEntityInstance,enrollment,orgUnit',
                                'ou': 'EF5pbiM7RSX',
                                'trackedEntityInstance': tei_id
                }
                tei_enrollment = api.get('enrollments', params=params)
                tei_enrollment_json = tei_enrollment.json()
                # Get TEI and org unit id
                if tei_enrollment_json['enrollments']:
                    enrollment = tei_enrollment_json['enrollments'][0]['enrollment']
                       
        except Exception as e:
            print(f"TEI Fetch Failed: {str(e)}")

        # if tei_id is None and org_unit is None:
        payload = {
                "resourceType": "Bundle",
                "type": "batch",
                "entry": [
                    {"request": {"method": "GET", "url": f"Observation?subject=Patient/{patient_id}&date=ge{encounter_date}&date=le{encounter_dayend}&_tag=PKT0010397&code=271062006,75367002"}},
                    {"request": {"method": "GET", "url": f"Condition?subject=Patient/{patient_id}&_tag=PKT0010397"}}
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
        if "entry" in bundle and tei_id and enrollment:
            count = 0
            for entry_ in bundle["entry"]:
            
                diabetes_present, hypertension_present = "false", "false"
                blood_pressure_systolic, blood_pressure_diastolic, blood_sugar_value = "", "", ""
                
                if "entry" in entry_["resource"]:
                    
                    for entry in entry_["resource"]["entry"]:  
                        if entry["resource"]["resourceType"] == "Condition":   
                            condition_resource = entry.get("resource", {})
                            condition_code = condition_resource.get("code", {}).get("coding", [{}])[0].get("code", "")
                            if condition_code == "diabetes":
                                diabetes_present = "true"
                            if condition_code == "38341003" or condition_code == "hypertension":  # SNOMED code for hypertension
                                hypertension_present = "true"

                        if entry["resource"]["resourceType"] == "Observation":   
                            observation_resource = entry.get("resource", {})
                            # Blood Sugar Value - you may need to adjust the code based on the LOINC code or system you're using
                            blood_sugar_code = "271062006"  # LOINC code for blood glucose measurement, replace with relevant code
                            for component in observation_resource.get("component", []):
                                if component.get("code", {}).get("coding", [{}])[0].get("code") == blood_sugar_code:
                                    blood_sugar_value = component.get("valueQuantity", {}).get("value")
                            
                            if observation_resource.get("code", {}).get("coding", [{}])[0].get("code") == blood_sugar_code:
                                    blood_sugar_value = observation_resource.get("valueQuantity", {}).get("value")
                            # Blood Pressure Value - usually involves systolic and diastolic measurements
                            
                            systolic_blood_pressure_code = "271649006"  # LOINC code for blood pressure, replace with relevant code
                            diastolic_blood_pressure_code = "271650006"
                            for component in observation_resource.get("component", []):
                                if component.get("code", {}).get("coding", [{}])[0].get("code") == systolic_blood_pressure_code:
                                    blood_pressure_systolic = component.get("valueQuantity", {}).get("value")
                                if component.get("code", {}).get("coding", [{}])[0].get("code") == diastolic_blood_pressure_code:
                                    blood_pressure_diastolic = component.get("valueQuantity", {}).get("value")
                            if observation_resource.get("code", {}).get("coding", [{}])[0].get("code") == systolic_blood_pressure_code:
                                    blood_pressure_systolic = observation_resource.get("valueQuantity", {}).get("value")
                            if observation_resource.get("code", {}).get("coding", [{}])[0].get("code") == diastolic_blood_pressure_code:
                                    blood_pressure_diastolic = observation_resource.get("valueQuantity", {}).get("value")
                            # Output the results
                            # if blood_sugar_value:
                            #     print(f"Blood Sugar Value: {blood_sugar_value}")
                            # if blood_pressure_systolic and blood_pressure_diastolic:
                            #     print(f"Blood Pressure: {blood_pressure_systolic}/{blood_pressure_diastolic}")

                        if (tei_id and enrollment):
                            event_payload = {
                                "events": [
                                    {
                                        "dataValues": [
                                        {
                                        "dataElement": "oipjzjylb5j",
                                        "value": blood_pressure_diastolic
                                        },
                                        {
                                        "dataElement": "lX3Mr4fDzt7",
                                        "value": blood_sugar_value
                                        },
                                        {
                                        "dataElement": "akdaaNwuAWT"
                                        },
                                        {
                                        "dataElement": "ooWz0VBNypG",
                                        "value": blood_pressure_systolic
                                        },
                                        {
                                        "dataElement": "rW9y580Zer8",
                                        "value": hypertension_present
                                        },
                                        {
                                        "dataElement": "p1Jx0zlriQr",
                                        "value": hypertension_present
                                        }
                                    ],

                                        "occurredAt": encounter_start_date,
                                        "programStage": "Qpuicl4a94s",
                                        "program": "jwn5nGdUepW",
                                        "status": "COMPLETED",
                                        "completedDate": encounter_start_date,
                                        "orgUnit": "EF5pbiM7RSX",
                                        "enrollment": enrollment,
                                        "trackedEntity": tei_id
                                    }
                                ]
                            }
                                
                            try:
                                res = api.post('tracker', json=event_payload)
                                print(f"Event creation successful", res.json())
                            except Exception as e:
                                print(f"Community screening event create failed: {str(e)}")
                                     
                                    

    