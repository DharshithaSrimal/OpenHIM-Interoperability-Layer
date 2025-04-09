from dotenv import load_dotenv, dotenv_values
import os
import json
import requests
from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth
from dhis2 import Api
# 9.18
tei_id, org_unit = "", ""
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

#FHIR Location
FACILITY = "PKT0010413"
# Orgunit
ORGUNIT = "DG1qjOGmxzl"
# #FHIR Location
# FACILITY = "PKT0010322"
# # Orgunit
# ORGUNIT = "WoFlqQmqtSR"

# Date range to loop over (2022-09-15 to 2022-09-30)
start_date_range = datetime(2000, 1, 1)
end_date_range = datetime(2020, 1, 1)
LOG_FILE_PATH = "gonaduwa_event_errors.log"
# LOG_FILE_PATH = "baduraliya_hv_event_errors.log"

def log_error(message):
    with open(LOG_FILE_PATH, "a") as log_file:
        log_file.write(f"{datetime.now()} - {message}\n")
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

# Loop over each day in the date range 16.50
# current_date = start_date_range  03:05
# START_DATE = current_date.strftime("%Y-%m-%dT00:00:00Z")
# END_DATE = (current_date + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
START_DATE = "2017-12-20T00:00:00"
END_DATE = "2025-03-23T23:59:00"
# START_DATE = "2024-08-28T00:00:00"
# END_DATE = "2024-10-28T00:00:00"
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
f"{FHIR_SERVER_URL}/fhir/Encounter?type=184047000,facility_visit,FOLLOWUP&_count=0&date=ge{START_DATE}&date=le{END_DATE}&_tag={FACILITY}&subject=c3e7d6ab-079f-4818-9ccc-dc5ee70d8b68,71725535-f8f4-4ac2-8d5c-5eb7796a0fa8,d6703fd8-2f5b-4d75-8ea6-0c6f6e8f0702,abfba34a-6eb1-4bf1-a4d8-1eb4c45d9b8c,e111f8d3-109d-4319-b12d-e3359fdb544a,eef4604e-47f1-40be-b317-19a815b99b73,013d9ca5-98ca-4964-85c0-89cd6216bc80,b041a441-f03d-437a-b71f-451f91050ff9,d64d2285-7a5a-420d-9b00-2a768865465e,83730f6c-b678-4c5d-ab22-e004a6ef163d,154dc1a0-0f74-4974-8254-6450d23faffc,dc591201-3f46-497a-870e-62f0fb60268b",
headers={"Authorization": f"Bearer {ACCESS_TOKEN}"})
encounter_count = encounters.json().get("total")
print("Count: ", encounter_count)
# FHIR encounters
encounter_response = requests.get(
    f"{FHIR_SERVER_URL}/fhir/Encounter?type=184047000,facility_visit,FOLLOWUP&date=ge{START_DATE}&date=le{END_DATE}&_count={encounter_count}&_tag={FACILITY}&_sort=date&subject=c3e7d6ab-079f-4818-9ccc-dc5ee70d8b68,71725535-f8f4-4ac2-8d5c-5eb7796a0fa8,d6703fd8-2f5b-4d75-8ea6-0c6f6e8f0702,abfba34a-6eb1-4bf1-a4d8-1eb4c45d9b8c,e111f8d3-109d-4319-b12d-e3359fdb544a,eef4604e-47f1-40be-b317-19a815b99b73,013d9ca5-98ca-4964-85c0-89cd6216bc80,b041a441-f03d-437a-b71f-451f91050ff9,d64d2285-7a5a-420d-9b00-2a768865465e,83730f6c-b678-4c5d-ab22-e004a6ef163d,154dc1a0-0f74-4974-8254-6450d23faffc,dc591201-3f46-497a-870e-62f0fb60268b",
    headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
)

encounter_response_data = encounter_response.json()
encounter_response_bundle = encounter_response_data.get("entry", [])

for encounter_info in encounter_response_bundle:
        patient_id = encounter_info["resource"]["subject"]["reference"].split('/')[-1]
        encounter_id = encounter_info["resource"]["id"]
        # Extract encounter date and set time range
        encounter_start_date = encounter_info["resource"]["period"]["start"].split('T')[0].strip()
        print(encounter_start_date)
        encounter_date = f"{encounter_start_date}T00:00:00".strip()
        encounter_dayend = f"{encounter_start_date}T23:59:59".strip()
        print("start: ", encounter_date, " end: ", encounter_dayend)

        diabetes_present, hypertension_present = "false", "false"
        blood_pressure_systolic, blood_pressure_diastolic= "", ""
        blood_sugar_value,  rbg_value = "", ""
        foot_complication, ophthalmic_disorder = "", ""
        ckd_value1, ckd_value2, ckd_value3 = "", "", "" 
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
            cnt = tei_response_json
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
                                'ou': ORGUNIT,
                                'trackedEntityInstance': tei_id
                }
                tei_enrollment = api.get('enrollments', params=params)
                tei_enrollment_json = tei_enrollment.json()
                # Get TEI and org unit id
                if tei_enrollment_json['enrollments']:
                    enrollment = tei_enrollment_json['enrollments'][0]['enrollment']
                    print(enrollment)
                       
        except Exception as e:
            print(f"TEI Fetch Failed: {str(e)}")

        # if tei_id is None and org_unit is None:
        payload = {
                "resourceType": "Bundle",
                "type": "batch",
                "entry": [
                    {"request": {"method": "GET", "url": f"Observation?subject=Patient/{patient_id}&date=ge{encounter_date}&date=le{encounter_dayend}&_tag={FACILITY}&code=271062006,75367002,36228007,284384005,709044004,foot_complication"}},
                    {"request": {"method": "GET", "url": f"Condition?subject=Patient/{patient_id}&date=ge{encounter_date}&date=le{encounter_dayend}&_tag={FACILITY}"}}
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

        params_range = {
                    'ou': ORGUNIT,
                    'trackedEntityInstance': tei_id,
                    'startDate': encounter_start_date,
                    'endDate': encounter_dayend
                }
        event_exist = api.get('events', params=params_range)
        event_exist_json = event_exist.json()
        events_range = ""
        if event_exist_json['events']:
            events_range = event_exist_json['events']
        # Check if the response contains RiskAssessment resources and extract values
        if "entry" in bundle and tei_id and enrollment and not events_range:
            for entry_ in bundle["entry"]:
                
                # print("test_", entry_)
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
                            rbg_code = "271061004" #Random Blood Sugar
                            for component in observation_resource.get("component", []):
                                if component.get("code", {}).get("coding", [{}])[0].get("code") == blood_sugar_code:
                                    blood_sugar_value = component.get("valueQuantity", {}).get("value")
                                    blood_sugar_value = round(blood_sugar_value)
                                if component.get("code", {}).get("coding", [{}])[0].get("code") == rbg_code:
                                    rbg_value = component.get("valueQuantity", {}).get("value")
                                    rbg_value = round(rbg_value)
                            if observation_resource.get("code", {}).get("coding", [{}])[0].get("code") == blood_sugar_code:
                                    blood_sugar_value = observation_resource.get("valueQuantity", {}).get("value")
                                    blood_sugar_value = round(blood_sugar_value)
                            if observation_resource.get("code", {}).get("coding", [{}])[0].get("code") == rbg_code:
                                    rbg_value = observation_resource.get("valueQuantity", {}).get("value")
                                    rbg_value = round(rbg_value)

                            # Blood Pressure Value - usually involves systolic and diastolic measurements
                            
                            systolic_blood_pressure_code = "271649006"  # LOINC code for blood pressure, replace with relevant code
                            diastolic_blood_pressure_code = "271650006"
                            ophthalmic_disorder_code = "36228007"
                            foot_complication_code = "284384005"
                            ckd_code = "709044004"

                            for component in observation_resource.get("component", []):
                                if component.get("code", {}).get("coding", [{}])[0].get("code") == systolic_blood_pressure_code:
                                    blood_pressure_systolic = component.get("valueQuantity", {}).get("value")
                                    blood_pressure_systolic = round(blood_pressure_systolic)
                                if component.get("code", {}).get("coding", [{}])[0].get("code") == diastolic_blood_pressure_code:
                                    blood_pressure_diastolic = component.get("valueQuantity", {}).get("value")
                                    blood_pressure_diastolic = round(blood_pressure_diastolic)
                                if component.get("code", {}).get("coding", [{}])[0].get("code") == ophthalmic_disorder_code:
                                    ophthalmic_disorder = component.get("valueCodeableConcept", {}).get("coding", [{}][0]).get("code")
                                    if ophthalmic_disorder == "no":
                                        ophthalmic_disorder = "false"
                                    elif ophthalmic_disorder == "yes":
                                        ophthalmic_disorder = "true"
                                    else:
                                        ophthalmic_disorder = ""
                                if component.get("code", {}).get("coding", [{}])[0].get("code") == foot_complication_code:
                                    foot_complication = component.get("valueCodeableConcept", {}).get("coding", [{}][0]).get("code")
                                    if foot_complication == "no":
                                        foot_complication = "false"
                                    elif foot_complication == "yes":
                                        foot_complication = "true"
                                    else:
                                        foot_complication = ""
                                if component.get("code", {}).get("coding", [{}])[0].get("code") == "foot_complication":
                                    foot_complication = component.get("valueString")
                                    if foot_complication == "no":
                                        foot_complication = "false"
                                    elif foot_complication == "yes":
                                        foot_complication = "true"
                                    else:
                                        foot_complication = ""
                                if component.get("code", {}).get("coding", [{}])[0].get("code") == ckd_code:
                                    ckd_value1 = component.get("valueQuantity", {}).get("value")
                            if observation_resource.get("code", {}).get("coding", [{}])[0].get("code") == systolic_blood_pressure_code:
                                    blood_pressure_systolic = observation_resource.get("valueQuantity", {}).get("value")
                                    blood_pressure_systolic = round(blood_pressure_systolic)
                            if observation_resource.get("code", {}).get("coding", [{}])[0].get("code") == diastolic_blood_pressure_code:
                                    blood_pressure_diastolic = observation_resource.get("valueQuantity", {}).get("value")
                                    blood_pressure_diastolic = round(blood_pressure_diastolic)

                            # Eye complications
                            if observation_resource.get("code", {}).get("coding", [{}])[0].get("code") == ophthalmic_disorder_code:
                                    ophthalmic_disorder = observation_resource.get("valueCodeableConcept", {}).get("coding", [{}][0]).get("code")
                                    if ophthalmic_disorder == "no":
                                        ophthalmic_disorder = "false"
                                    elif ophthalmic_disorder == "yes":
                                        ophthalmic_disorder = "true"
                                    else:
                                        ophthalmic_disorder = ""

                            # Foot complications
                            if observation_resource.get("code", {}).get("coding", [{}])[0].get("code") == foot_complication_code:
                                    foot_complication = observation_resource.get("valueCodeableConcept", {}).get("coding", [{}][0]).get("code")
                                    if foot_complication == "no":
                                        foot_complication = "false"
                                    elif foot_complication == "yes":
                                        foot_complication = "true"
                                    else:
                                        foot_complication = ""
                            if observation_resource.get("code", {}).get("coding", [{}])[0].get("code") == "foot_complication":
                                    foot_complication = observation_resource.get("valueString")
                                    if foot_complication == "no":
                                        foot_complication = "false"
                                    elif foot_complication == "yes":
                                        foot_complication = "true"
                                    else:
                                        foot_complication = ""

                            # CKD
                            if ckd_value1 == "":
                                if observation_resource.get("code", {}).get("coding", [{}])[0].get("code") == ckd_code:
                                    ckd_value1 = observation_resource.get("valueQuantity", {}).get("value")
                            elif ckd_value2 == "":
                                if observation_resource.get("code", {}).get("coding", [{}])[0].get("code") == ckd_code:
                                    ckd_value2 = observation_resource.get("valueQuantity", {}).get("value")
                            elif ckd_value3 == "":
                                if observation_resource.get("code", {}).get("coding", [{}])[0].get("code") == ckd_code:
                                    ckd_value3 = observation_resource.get("valueQuantity", {}).get("value")
                            # Output the results
                            # if blood_sugar_value:
                            #     print(f"Blood Sugar Value: {blood_sugar_value}")
                            # if blood_pressure_systolic and blood_pressure_diastolic:
                            #     print(f"Blood Pressure: {blood_pressure_systolic}/{blood_pressure_diastolic}")

        
            if (tei_id and enrollment):
                event_payload = {
                                    
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
                                        },
                                        {
                                        "dataElement": "y2lq4lD55KQ",
                                        "value": ophthalmic_disorder
                                        },
                                        {
                                        "dataElement": "OeKL5OwuM5T",
                                        "value": foot_complication
                                        },
                                        {
                                        "dataElement": "ZH64mqMBDkS",
                                        "value": ckd_value1
                                        },
                                        {
                                        "dataElement": "q4mxgnjB2Dy",
                                        "value": ckd_value2
                                        },
                                        {
                                        "dataElement": "UhG7KvnsQBS",
                                        "value": ckd_value3
                                        },
                                        {
                                        "dataElement": "akdaaNwuAWT",
                                        "value": ckd_value3
                                        }
                                    ],

                                        "eventDate": encounter_start_date,
                                        "programStage": "Qpuicl4a94s",
                                        "program": "jwn5nGdUepW",
                                        "status": "COMPLETED",
                                        "completedDate": encounter_start_date,
                                        "dueDate": encounter_start_date,
                                        "orgUnit": ORGUNIT,
                                        "trackedEntityInstance": tei_id
                                    
                            }
                                
                try:
                    print(event_payload)
                    res = api.post('events', json=event_payload)
                    if res.status_code == 200:
                         print("Event creation successful")
                    if res.status_code != 200:
                        error_message = f"HLC screening, Followup events creation failed : {res.json()}, Encounter: {encounter_id}"
                        log_error(error_message)
                        print(error_message)
                except Exception as e:
                    error_message = f"Community screening event failed: : {str(e)}, Encounter: {encounter_id}"
                    print(f"Community screening event create failed: {str(e)}")
                                     
                                    

    