import os
import json
import requests
from datetime import datetime
import base64 

# Replace these values with your Keycloak and FHIR server details
KEYCLOAK_URL = "https://keycloak.diabetescompass.health.gov.lk:4443/realms/dc_community/protocol/openid-connect/token"
FHIR_SERVER_URL = "https://fhir.diabetescompass.health.gov.lk:4443"

CLIENT_ID = "dc-interoperability"
CLIENT_SECRET = "pZ6EKIhWCtqAaCiB5Atmmj6ULlcc0FG1"
GRANT_TYPE = "client_credentials"

# START_DATE = datetime.now().strftime("%Y-%m-%dT00:00:00Z")
# END_DATE = datetime.now().strftime("%Y-%m-%dT23:59:59Z")
START_DATE = "2024-06-15T00:00:00Z"
END_DATE = "2024-08-10T00:00:00Z"

# DHIS2
DHIS2_SERVER_URL = "http://localhost:8084/dhis/api"
USERNAME = "admin"
PASSWORD = "Admin@Asd1"

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
dm_risk = ""
htn_risk = ""
high = "High"
low = "Low"
risk = ""
consent = ""
screening_required = ""
referral_place = ""


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
    f"{FHIR_SERVER_URL}/fhir/Patient?_lastUpdated=ge{START_DATE}&_lastUpdated=le{END_DATE}",
    headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
)
patients_data = patients_response.json()
patients_bundle = patients_data.get("entry", [])

for patient_info in patients_bundle:
    patient_id = patient_info["resource"]["id"]
    patient_resource = patient_info["resource"]
    
    # Extract the Practitioner Location code
    practitioner_location_code = next((tag["code"] for tag in patient_resource["meta"]["tag"] if tag["system"] == "https://smartregister.org/location-tag-id"), None)
    location_name = locationArray.get(practitioner_location_code)

    if not location_name:
        # print(f"Location name not found for code: {practitioner_location_code}")
        continue

    if not any(org["displayName"] == location_name for org in orgunits):
        print(f"Location name does not exist in orgunits.json: {location_name}")
        continue

    # Get the location ID for the matching location name
    location_id = next((org["id"] for org in orgunits if org["displayName"] == location_name), None)
    print(location_id)
    if not location_id:
        continue

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

    # Construct the updated patient resource
    patient_resource["meta"]["tag"] = [{"system": "https://smartregister.org/location-tag-id", "code": location_id}]
    
    # Send the updated patient resource to the OpenHIM Mapping Mediator
    mapping_response = requests.post(
        "http://localhost:5001/fhir-to-tei",
        headers={"Content-Type": "application/json"},
        json=patient_resource
    )
    mapping_result = mapping_response.json()
    data_origin = "Community Screening App"
    # Update the age attribute in the mapping result
    age_group = "Ageless45" if age < 45 else "45to54" if age < 55 else "55to64" if age < 65 else "65orAbove"
    mapping_result["attributes"].append({"attribute": "QUS2rM78s6F", "value": str(age)})
    mapping_result["attributes"].append({"attribute": "cTFwAAW0and", "value": age_group})
    mapping_result["attributes"].append({"attribute": "Nymn5TH8GRu", "value": patient_resource["gender"].capitalize()})
    mapping_result["attributes"].append({"attribute": "QmkJzDbUkSC", "value": data_origin})

    # Add orgUnit to enrollments
    mapping_result["enrollments"][0]["orgUnit"] = mapping_result.get("orgUnit")
    # Add incidentDate to enrollments
    mapping_result["enrollments"][0]["incidentDate"] = mapping_result["enrollments"][0]["enrollmentDate"]

    # # Send the payload to DHIS2 trackedEntityInstances
    # response = requests.post(
    #     f"{DHIS2_SERVER_URL}/trackedEntityInstances",
    #     headers={
    #         "Content-Type": "application/json",
    #         "Authorization": "Basic " + base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
    #     },
    #     json=mapping_result
    # )
    # print(response)
    # Save the mapping result
# Send to openhim ##############
    mapping_ = requests.post(
        "http://localhost:5001/patient-risk-test",
        headers={"Content-Type": "application/json"},
        json=mapping_result
    )

# List to hold the tracked entity instances
tracked_entity_instances = []

# Loop through the mapping results and append them to the tracked entity instances list
# for key, result in MAPPING_RESULTS.items():
#     tracked_entity_instances.append(result)

# Create the payload
# payload = {
#     "trackedEntityInstances": tracked_entity_instances
# }

# print(payload)

# mapping_ = requests.post(
#         "http://localhost:5001/patient-risk-test",
#         headers={"Content-Type": "application/json"},
#         json=payload
#     )

# Send the payload to DHIS2 trackedEntityInstances
# response = requests.post(
#     f"{DHIS2_SERVER_URL}/trackedEntityInstances",
#     headers={
#         "Content-Type": "application/json",
#         "Authorization": "Basic " + base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
#     },
#     json=payload
# )

# Print the response
# print(response.text)

### Community Screening ###
questionnaireResponse = requests.get(
    f"{FHIR_SERVER_URL}/fhir/QuestionnaireResponse?_lastUpdated=ge{START_DATE}&_lastUpdated=le{END_DATE}&questionnaire=dc-diabetes-screening",
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
        # bundle = patients_data.get("entry", [])

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
                elif entry["resource"]["resourceType"] == "QuestionnaireResponse":
                    questionnaire_response = entry["resource"]
                    # consent = questionnaire_response.get("item", [{}])[0].get("item", [{}])[1].get("answer", [{}])[0].get("valueCoding").get("display")
                    
                    # Define the keys for the nested extraction
                    concent_keys = ["item", 0, "item", 1, "answer", 0, "valueCoding", "display"]

                    # Extract the consent safely
                    consent = get_nested_value(questionnaire_response, concent_keys, default="N/A")
                    
                    if(consent == "I consent to participating in this screening"):
                        consent = "true"
                    else:
                        consent = "false"
                    
                    # Define the keys for the nested extraction
                    screening_required_keys = ["item", 3, "item", 0, "text"]

                    # Extract the screening required
                    screening_required = get_nested_value(questionnaire_response, screening_required_keys, default="N/A")
                    
                    # screening_required = questionnaire_response.get("item", [{}])[3].get("item", [{}])[0].get("text")
                    if (screening_required == "Results"):
                        screening_required = "true"
                    else:
                        screening_required = "false"

                    # Define the keys for the nested extraction
                    keys = ["item", 3, "item", 5, "answer", 0, "valueReference", "display"]

                    # Extract the referral place safely
                    referral_place = get_nested_value(questionnaire_response, keys, default="N/A")

                    print("Place:", referral_place)
                    # referral_place = questionnaire_response.get("item", [{}])[3].get("item", [{}])[5].get("answer", [{}])[0].get("valueReference").get("display")
                    # print("Place: ", referral_place)
        if (dm_risk == high and htn_risk == high):
            risk = "High risk of diabetes and hypertension"
        if (dm_risk == high and htn_risk == low): 
            risk = "High risk of diabetes" 
        if (dm_risk == low and htn_risk == high):  
            risk = "High risk of hypertension"
        if (dm_risk == low and htn_risk == low):
            risk = "Low Risk"

        post_response = requests.post(
            'http://localhost:5001/community-screening',
            json=bundle,
            headers={"Content-Type": "application/json"},
        )

        if post_response.status_code == 200:
            # print("Post request successful:", post_response.json())
            screening_event = post_response.json()
            # Update the age attribute in the mapping result
            screening_event["dataValues"].append({"dataElement": "vjABPom3WZD", "value": str(screening_required)})
            screening_event["dataValues"].append({"dataElement": "igk7wHUjNoY", "value": str(consent)})
            screening_event["dataValues"].append({"dataElement": "rRh555ufFsW", "value": str(referral_place)})
            screening_event["dataValues"].append({"dataElement": "caq1Rf8wDx7", "value": str(risk)})
            screening_event["dataValues"].append({"dataElement": "v96qvNbmSIz", "value": str(practitioner_code)})
            print(screening_event)
        else:
            print("Post request failed:", post_response.status_code, post_response.text)

        mapping_a = requests.post(
        "http://localhost:5001/patient-risk-test",
        headers={"Content-Type": "application/json"},
        json=screening_event
        )


 