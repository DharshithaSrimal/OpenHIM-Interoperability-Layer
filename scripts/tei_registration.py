from dotenv import load_dotenv, dotenv_values
import os
import json
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth 
# Install External Libraries
import subprocess
import sys

### Defs  
def install_package(package):
    """Installs the specified package using pip."""
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def check_and_install_requirements():
    """Reads requirements.txt, checks installed packages, and installs missing ones."""
    try:
        with open("requirements.txt", "r") as f:
            requirements = f.readlines()
    except FileNotFoundError:
        print("requirements.txt not found. Please ensure the file exists.")
        sys.exit(1)

    for requirement in requirements:
        package = requirement.strip()
        if package:
            try:
                __import__(package.split("==")[0])
            except ImportError:
                print(f"Package {package} is not installed. Installing...")
                # install_package(package)
            else:
                print(f"Package {package} is already installed.")

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

if __name__ == "__main__":
    check_and_install_requirements()
# End of installing External Libraries
from dhis2 import Api
load_dotenv()  # Load environment variables from .env file

# FHIR
FHIR_SERVER_URL = os.getenv("FHIR_SERVER_URL")

# Keycloak
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
GRANT_TYPE = os.getenv("GRANT_TYPE")

# START_DATE = datetime.now().strftime("%Y-%m-%dT00:00:00Z")
# END_DATE = datetime.now().strftime("%Y-%m-%dT23:59:59Z")
START_DATE = "2024-12-24T00:00:00Z"
END_DATE = "2024-12-25T00:00:00Z"

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

patients_response = requests.get(
    f"{FHIR_SERVER_URL}/fhir/Patient?_count=1000&_lastUpdated=ge{START_DATE}&_lastUpdated=le{END_DATE}",
    headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
)
patients_data = patients_response.json()
patients_bundle = patients_data.get("entry", [])

for patient_info in patients_bundle:

    patient_id = patient_info["resource"]["id"]
    patient_resource = patient_info["resource"]

    # Extract the Practitioner Location code
    practitioner_location_code = next((tag["code"] for tag in patient_resource["meta"]["tag"] if tag["system"] == "https://smartregister.org/location-tag-id"), None)
    
    # Fetch the location
    ou_params = {
        'filter': 'code' + ':eq:' + practitioner_location_code
    }
    ou_response = api.get('organisationUnits', params=ou_params)
    ou_response_json = ou_response.json()
    ou_id = ou_response_json['organisationUnits'][0]['id']
    
    # Calculate age from birthday
    birth_date = patient_resource["birthDate"]
    current_year = datetime.now().year
    birth_year = datetime.strptime(birth_date, "%Y-%m-%d").year
    age = current_year - birth_year

    # Extract the Practitioner code
    practitioner_code = next((tag["code"] for tag in patient_resource["meta"]["tag"] if tag["system"] == "https://smartregister.org/practitioner-tag-id"), None)
    if not practitioner_code:
        print("Practitioner code not found.")
        continue

    # Extract the Patient origin
    patient_origin = next((tag["code"] for tag in patient_resource["meta"]["tag"] if tag["system"] == "https://smartregister.org/app-version"), None)
    
    # Construct the updated patient resource - set ouid
    patient_resource["meta"]["tag"] = [{"system": "https://smartregister.org/location-tag-id", "code": ou_id}]
    app_version = next((tag["code"] for tag in patient_resource["meta"]["tag"] if tag["system"] == "https://smartregister.org/app-version"), None)

    # Send the updated patient resource to the OpenHIM Mapping Mediator
    mapping_response = requests.post(
        "http://localhost:5001/fhir-to-tei",
        headers={"Content-Type": "application/json"},
        auth=HTTPBasicAuth(OPENHIM_CLIENT, OPENHIM_CLIENT_PASS),
        json=patient_resource
    )
    if patient_origin == "2.0.0-diabetesCompass":
        data_origin = "Community_Screening_App"
    else:
        data_origin = "Clinic_App"

    mapping_result = mapping_response.json()
    if mapping_response.status_code == 200:
        # Update the age attribute in the mapping result
        age_group = "Ageless45" if age < 45 else "45to54" if age < 55 else "55to64" if age < 65 else "65orAbove"
        mapping_result["attributes"].append({"attribute": "QUS2rM78s6F", "value": str(age)})
        mapping_result["attributes"].append({"attribute": "cTFwAAW0and", "value": age_group})
        mapping_result["attributes"].append({"attribute": "Nymn5TH8GRu", "value": patient_resource["gender"].capitalize()})
        mapping_result["attributes"].append({"attribute": "QmkJzDbUkSC", "value": data_origin})
        mapping_result["attributes"].append({"attribute": "Y3wfrP5h7Uw", "value": practitioner_code})

        # Add orgUnit to enrollments
        ou = mapping_result.get("orgUnit")
        mapping_result["enrollments"][0]["orgUnit"] = ou
        # Add incidentDate to enrollments
        mapping_result["enrollments"][0]["incidentDate"] = mapping_result["enrollments"][0]["enrollmentDate"]
        phn = mapping_result["attributes"][1]["value"]
    else:
        print(f"Error: {mapping_response.status_code}, {mapping_response.text}")
    
    params = {
        'fields': 'trackedEntityInstance,attributes[attribute,value]',
        'ou': ou,
        'trackedEntityType': TRACKED_ENTITY_TYPE,
        'filter': TEI_ATTR_PHN + ':eq:' + phn
    }
    tei_response = api.get('trackedEntityInstances', params=params)
    tei_response_json = tei_response.json()
    
    if not tei_response_json['trackedEntityInstances']:
        tei_post_response = ''
        try:
            tei_post_response = api.post('trackedEntityInstances', json=mapping_result)
            if tei_post_response.status_code != 200:
                print(f"TEI Registration failed: ", tei_post_response.json())
        except Exception as e:
            print(f"TEI Registration Failed: {str(e)}")
                        
        current_date = patient_info["resource"]["meta"]["lastUpdated"]
        if tei_post_response and tei_post_response.status_code == 200:
            # Parse the JSON string into a dictionary
            response_dict = tei_post_response.json()
            # Navigate through the dictionary to get the 'href' value
            tei_id = response_dict['response']['importSummaries'][0]['reference']
            # HLC screening, Followup events
            hlc_event_data = {
                "events": [{
                    "trackedEntityInstance": tei_id,
                    "status": "ACTIVE",
                    "eventDate": current_date,
                    "programStage": program_stage[0],
                    "program": "jwn5nGdUepW",
                    "orgUnit": ou
            },
            {
                    "trackedEntityInstance": tei_id,
                    "status": "ACTIVE",
                    "eventDate": current_date,
                    "programStage": program_stage[1],
                    "program": "jwn5nGdUepW",
                    "orgUnit": ou,
                    "dataValues":[{"dataElement":"VCQ4bYBggPB","value": tei_event_followup[0]}]
            }]}
            
            # hlc_event_data_json = hlc_event_data.json()
            res = api.post('events', json=hlc_event_data)
            if res.status_code != 200:
                print("HLC screening, Followup events creation failed ", res)

            # mapping__ = requests.post(
            #     "http://localhost:5001/dhis2",
            #     headers={"Content-Type": "application/json"},
            #     auth=HTTPBasicAuth("admin", "district"),
            #     json=hlc_event_data
            # )
            
    else:
        # Send PATCH request to update the existing TEI
        tei_id = tei_response_json['trackedEntityInstances'][0]['trackedEntityInstance']
        patch_endpoint = "trackedEntityInstances/" + tei_id
        # patch_response = api.put(patch_endpoint, json=mapping_result)

# List to hold the tracked entity instances
tracked_entity_instances = []
facility_id = ''
referral_ou_id = ''
refer = None
### Community Screening ###
questionnaireResponse = requests.get(
    f"{FHIR_SERVER_URL}/fhir/QuestionnaireResponse?_count=1000&_lastUpdated=ge{START_DATE}&_lastUpdated=le{END_DATE}&questionnaire=dc-diabetes-screening",
    headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
)

# Check for successful response
if questionnaireResponse.status_code == 200:
    qr_data = questionnaireResponse.json()
    qr_bundle = qr_data.get("entry", [])

    # Process each QuestionnaireResponse
    for entry in qr_bundle:
        resource = entry.get('resource', {})
        questionnaire_response_id = resource.get('id')
        patient_reference = resource.get('subject', {}).get('reference')

        if patient_reference:
            patient_id = patient_reference.split('/')[-1]

        # Extract RiskAssessment references from the contained List
        risk_assessment_ids = []
        contained_resources = resource.get('contained', [])
        for contained in contained_resources:
            if contained.get('resourceType') == 'List':
                for item in contained.get('entry', []):
                    reference = item.get('item', {}).get('reference', '')
                    if reference.startswith('RiskAssessment/'):
                        risk_assessment_id = reference.split('/')[-1]
                        risk_assessment_ids.append(risk_assessment_id)
                        

        # Prepare the payload based on available resources
        payload = {
            "resourceType": "Bundle",
            "type": "batch",
            "entry": [
                {
                    "request": {
                        "method": "GET",
                        "url": f"Patient/{patient_id}"
                    }
                },
                {
                    "request": {
                        "method": "GET",
                        "url": f"QuestionnaireResponse/{questionnaire_response_id}"
                    }
                }
            ]
        }

        for risk_assessment_id in risk_assessment_ids:
            payload["entry"].append({
                "request": {
                    "method": "GET",
                    "url": f"RiskAssessment/{risk_assessment_id}"
                }
            })
        # Clear risk_assessment_ids for the next iteration
        risk_assessment_ids.clear()
        # Send the POST request to localhost:5001
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
                if entry["resource"]["resourceType"] == "RiskAssessment":
                    risk_assessment = entry["resource"]
                    code = risk_assessment.get("code").get("coding", [{}])[0].get("code")
                    risk = risk_assessment.get("prediction", [{}])[0].get("qualitativeRisk").get("text")
                    if(code == "772788006"):
                        dm_risk = risk
                    if(code == "268607006"):
                        htn_risk = risk
                # Extract QuestionnaireResponse resource
                if entry["resource"]["resourceType"] == "QuestionnaireResponse":
                    questionnaire_response = entry["resource"]
                    # Define the keys for the nested extraction
                    concent_keys = ["item", 0, "item", 1, "answer", 0, "valueCoding", "display"]

                    # Extract the consent safely
                    consent = get_nested_value(questionnaire_response, concent_keys, default="N/A")
                    # Extract the Patient origin
                    if(consent == "I consent to participating in this screening"):
                        consent = "true"
                    else:
                        consent = "false"
                                         
                    # Define the keys for the nested extraction
                    refer, page_3_data, page_5_data = None, None, None
                    for item in questionnaire_response['item']:
                        if item['linkId'] == "page-5":
                            page_5_data = item
                        if item['linkId'] == "page-3":
                            page_3_data = item

                    if page_5_data:
                        for sub_item in page_5_data['item']:
                            if sub_item['linkId'] == "refer-client-choice":
                                refer_answer = sub_item['answer'][0]['valueCoding']['code']
                                if refer_answer == 'yes':
                                    refer = "true"
                                elif refer_answer == 'no':
                                    refer = "false"
                                break

                    # Get the value of "continue-screening-choice"
                    screening_required = None
                    if page_3_data:
                        for sub_item in page_3_data['item']:
                            if sub_item['linkId'] == "continue-screening-choice":
                                screening_required = str(sub_item['answer'][0]['valueBoolean']).lower()
                           
                    # Define the keys for the nested extraction
                    page5 = next((tag["item"] for tag in questionnaire_response["item"] if tag["linkId"] == "page-5"), None)

                    facility_id = ''
                    referral_ou_id = ''
                    if page5 is not None:
                        for item in page5:
                            if item.get("linkId") == "health-facility-choice":
                                reference = item["answer"][0]["valueReference"]["reference"] 
                                facility_id = reference.split('/')[-1]
                                referral_ou_params = {
                                    'filter': 'code' + ':eq:' + facility_id
                                }
                                try:
                                    referral_ou_response = api.get('organisationUnits', params=referral_ou_params)
                                    referral_ou_response_json = ou_response.json()
                                    referral_ou_id = ou_response_json['organisationUnits'][0]['id']
                                except Exception as e:
                                    print(f"An error occurred: {str(e)}")

                if entry["resource"]["resourceType"] == "Patient":   
                    patient_response = entry["resource"] 
                    # Define the keys for the nested extraction
                    screening_phn_keys = ["identifier", 0, "value"]
                    # Extract the screening phn
                    screening_phn = get_nested_value(patient_response, screening_phn_keys, default="N/A")
                    # Extract the Practitioner Location code
                    location_keys = ["meta", "tag", 4, "code"]
                    location_code = get_nested_value(patient_response, location_keys, default="N/A")
                    
        risk = None
        if (dm_risk != None and dm_risk != None):
            if (dm_risk == high and htn_risk == high):
                risk = "High riskofdbthtn"
            if (dm_risk == high and htn_risk == low): 
                risk = "highrisk" 
            if (dm_risk == low and htn_risk == high):  
                risk = "Highriskhtn"
            if (dm_risk == low and htn_risk == low):
                risk = "lowrisk"

        if(screening_required == None and risk != None ):
            screening_required = "true"
        elif(screening_required == "false"):
            screening_required = "false"
        else:
            screening_required = "true"
        # Fetch TEI
        params = {
            'fields': 'trackedEntityInstance,attributes[attribute,value],orgUnit',
            'ouMode': 'ACCESSIBLE',
            'trackedEntityType': TRACKED_ENTITY_TYPE,
            'filter': TEI_ATTR_PHN + ':eq:' + screening_phn
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

        post_response = requests.post(
            'http://localhost:5001/community-screening',
            json=bundle,
            auth=HTTPBasicAuth(OPENHIM_CLIENT, OPENHIM_CLIENT_PASS),
            headers={"Content-Type": "application/json"},
        )

        # Post screening event if the TEI is available
        if tei_id and post_response.status_code == 200:

            screening_event = post_response.json()
            # Update the age attribute in the mapping result
            screening_event["trackedEntityInstance"] = tei_id
            screening_event["orgUnit"] = org_unit    
            if (consent):
                screening_event["dataValues"].append({"dataElement": "igk7wHUjNoY", "value": str(consent)})
            if (risk != None):
                screening_event["dataValues"].append({"dataElement": "caq1Rf8wDx7", "value": str(risk)})
            if(screening_required != None ): 
                screening_event["dataValues"].append({"dataElement": "vjABPom3WZD", "value": str(screening_required)})
            if (referral_ou_id):
                screening_event["dataValues"].append({"dataElement": "rRh555ufFsW", "value": str(referral_ou_id)})
            if (refer != None):
                screening_event["dataValues"].append({"dataElement": "mPxpSPjgwkI", "value": str(refer)})
            if(consent == "false" or screening_required == "false" or risk == "lowrisk"):
                # # Feth the followup event and make it completes
                # print(screening_event["status"])
                # Fetch Event
                event_params = {
                    'fields': 'event, orgUnit, trackedEntityInstance, status, eventDate, programStage, program, dataValues[dataElement,value]',
                    'orgUnit': org_unit,
                    'trackedEntityInstance': tei_id,
                    'programStage': program_stage[1]
                }
                try:
                    tei_event_response = api.get('events', params=event_params)
                    followup_events = tei_event_response.json()
                    followup_event = tei_event_response_json['events'][0]
                    followup_event["status"] = status[1]
                    event_id = followup_event['event']
                    tei_event_response = api.put('events/' + event_id, json=followup_event)
                except Exception as e:
                    print(f"Followup event fetch failed: {str(e)}")
            # Create community screening event
            try:
                res = api.post('events', json=screening_event)
                print(f"Community screening event creation successful")
            except Exception as e:
                print(f"Community screening event create failed: {str(e)}")
            print("Code: ", res.status_code)
            if res.status_code == 200:
                # Fetch Event
                event_params = {
                    'fields': 'event, orgUnit, trackedEntityInstance, status, eventDate, programStage, program, dataValues[dataElement,value]',
                    'ouMode': 'ACCESSIBLE',
                    'trackedEntityInstance': tei_id,
                    'programStage': program_stage[1]
                }
                try:
                    tei_event_response = api.get('events', params=event_params)
                except Exception as e:
                    print(f"Followup event fetch failed: {str(e)}")
                # 
                if(tei_event_response.status_code == 200):
                    tei_event_response_json = tei_event_response.json()
                    try:
                        followup_event = tei_event_response_json['events'][0]
                        followup_event['dataValues'][0]['value'] = tei_event_followup[1]
                        event_id = followup_event['event']
                        tei_event_response = api.put('events/' + event_id, json=followup_event)
                        if tei_event_response.status_code == 200:
                            print("Followup events update successful")
                    except Exception as e:
                        print(f"Followup event update failed: {str(e)}")
            
        else:
            print("Post request failed:", post_response.status_code, post_response.text)

        


 