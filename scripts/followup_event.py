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

status = ("ready", "active", "completed")

# DHIS2 
DHIS2_USER = os.getenv("DHIS2_USER")
DHIS2_PASS = os.getenv("DHIS2_PASS")
DHIS2_SERVER_URL = os.getenv("DHIS2_SERVER_URL")
api = Api(DHIS2_SERVER_URL, DHIS2_USER, DHIS2_PASS)

# Metadata
UNIQUE_ID = config["UNIQUE_ID"]
TRACKED_ENTITY_TYPE = config["TRACKED_ENTITY_TYPE"]
# Program Stages
HLC_SCREENING = config["HLC_SCREENING"]
FOLLOWUP = config["FOLLOWUP"]
tei_event_followup = ("Phone_Calls_Completed","Home_Visits_Completed","HLC_Visit_Completed") 
FOLLOWUP_STATUS = config["FOLLOWUP_STATUS"]
followup_events = ("Screening_Completed", "Phone_Calls_Completed", "Home_Visits_Completed")
# START_DATE = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
# END_DATE = datetime.now().strftime("%Y-%m-%dT00:00:00Z")
START_DATE = "2024-12-24T00:00:00Z"
END_DATE = "2025-01-06T00:00:00Z"

# Get Keycloak token
token_response = requests.post(KEYCLOAK_URL, data={
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "grant_type": GRANT_TYPE
})
ACCESS_TOKEN = token_response.json()["access_token"]

#### Defs
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


##### FHIR Service Request setup #####
# Service Request count
service_request = requests.get(
    f"{FHIR_SERVER_URL}/fhir/ServiceRequest?status={status[2]}&_count=0&",
    headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
)
service_request_count = service_request.json().get("total")
if (service_request_count > 0):
    # Send FHIR request to get all Service requests and process it in a loop
    service_request_response = requests.get(
        f"{FHIR_SERVER_URL}/fhir/ServiceRequest?status=completed&_count={service_request_count}&",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
    )

    service_request_data = service_request_response.json()
    service_request_bundle = service_request_data.get("entry", [])


    for service_request_info in service_request_bundle:
        patient_id = service_request_info["resource"]["for"]["reference"].split('/')[-1]
        patient = None
        if(patient_id):
            # Get TEI
            tei_id, org_unit = None, None 
            try:
                tei_id, org_unit = get_tracked_entity_instance(patient_id)
            except Exception as e:
                    print(f"TEI Fetch Failed: {str(e)}")

        if (tei_id != None and org_unit != None):
            event_params = {
                            'fields': 'event, orgUnit, trackedEntityInstance, status, eventDate, programStage, program, dataValues[dataElement,value]',
                            'ouMode': 'ACCESSIBLE',
                            'trackedEntityInstance': tei_id,
                            'programStage': FOLLOWUP
                        }
            try:
                tei_event_response = api.get('events', params=event_params)
                hlc_event = tei_event_response.json()['events'][0]
                post_response = requests.post(
                    'http://localhost:5001/hlc-screening',
                    json=hlc_event,
                    auth=HTTPBasicAuth("DC Client", "Asdf1234"),
                    headers={"Content-Type": "application/json"},
                )
                screening_event_json = post_response.json()
                if(screening_event_json):
                    event_id = screening_event_json['event']
                    try:
                        tei_event_response = api.put('events/' + event_id, json=screening_event_json)
                    except Exception as e:
                        print(f"HLC Event Update Failed: {str(e)}")
            except Exception as e:
                    print(f"HLC Event Fetch Failed: {str(e)}")

tasks = requests.get(
    f"{FHIR_SERVER_URL}/fhir/Task?status={status[2]}&_count=0&identifier=phone_call_follow_up",
    headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
)
tasks_count = tasks.json().get("total")
if (tasks_count > 0):
    # Send FHIR request to get all Service requests and process it in a loop
    task_response = requests.get(
        # status={status[2]}&
        f"{FHIR_SERVER_URL}/fhir/Task?_count={tasks_count}&identifier=phone_call_follow_up&",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
    )

    task_data = task_response.json()
    task_bundle = task_data.get("entry", [])

    for task_info in task_bundle:
        patient_id, event_date = None, None
        patient_id = task_info["resource"]["for"]["reference"].split('/')[-1]
        # event_date = task_info["resource"]["lastModified"]
        patient = None
        if(patient_id):
            # Get TEI
            tei_id, org_unit = None, None 
            try:
                tei_id, org_unit = get_tracked_entity_instance(patient_id)
            except Exception as e:
                print(f"TEI Fetch Failed: {str(e)}")

        if (tei_id != None and org_unit != None):
            event_params = {
                            'fields': 'event, orgUnit, trackedEntityInstance, status, eventDate, programStage, program, dataValues[dataElement,value]',
                            'ouMode': 'ACCESSIBLE',
                            'trackedEntityInstance': tei_id,
                            'programStage': FOLLOWUP,
                            'order': 'order=eventDate:desc'
                        }
            try:
                tei_event = api.get('events', params=event_params)
                tei_event_response = tei_event.json()
                followup_event = tei_event_response['events'][0]
                followup_event["eventDate"] = event_date
                if followup_event["dataValues"][0]["value"] == followup_events[0]:
                    followup_event["dataValues"][0]["value"] = followup_events[1]
                # elif followup_event["dataValues"][0]["value"] == followup_events[1]:
                #     followup_event["dataValues"][0]["value"] = followup_events[2]
                event_id = followup_event['event']
                try:
                    tei_event_response = api.put('events/' + event_id, json=followup_event)
                except Exception as e:
                    print(f"Phone Call Event Update Failed: {str(e)}")
            except Exception as e:
                print(f"Phone Call Event Fetch Failed: {str(e)}")

