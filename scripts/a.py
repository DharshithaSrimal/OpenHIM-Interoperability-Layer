import os
import json
import requests
from datetime import datetime
import base64 

# Replace these values with your Keycloak and FHIR server details
KEYCLOAK_URL = "http://188.166.213.172:8081/realms/wdf_stage/protocol/openid-connect/token"
FHIR_SERVER_URL = "http://188.166.213.172:8082"

CLIENT_ID = "cHIMS Client"
CLIENT_SECRET = "lvUTECeWLcHfyj0UZ5AI0q0t4X67vOaS"
GRANT_TYPE = "client_credentials"

# START_DATE = datetime.now().strftime("%Y-%m-%dT00:00:00Z")
# END_DATE = datetime.now().strftime("%Y-%m-%dT23:59:59Z")
START_DATE = "2024-03-26T00:00:00Z"
END_DATE = "2024-03-31T23:59:59Z"

# DHIS2
DHIS2_SERVER_URL = "http://localhost:8084/dhis/api"
USERNAME = "admin"
PASSWORD = "Admin@Asd1"

locationArray = {}
MAPPING_RESULTS = {}
count = 0

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
        print(f"Location name not found for code: {practitioner_location_code}")
        continue

    if not any(org["displayName"] == location_name for org in orgunits):
        print(f"Location name does not exist in orgunits.json: {location_name}")
        continue

    # Get the location ID for the matching location name
    location_id = next((org["id"] for org in orgunits if org["displayName"] == location_name), None)
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
    print(practitioner_code)
    # Construct the updated patient resource
    patient_resource["meta"]["tag"] = [{"system": "https://smartregister.org/location-tag-id", "code": location_id}]
    
    # Send the updated patient resource to the OpenHIM Mapping Mediator
    mapping_response = requests.post(
        "http://localhost:5001/fhir-to-tei",
        headers={"Content-Type": "application/json"},
        json=patient_resource
    )
    mapping_result = mapping_response.json()

    # Update the age attribute in the mapping result
    age_group = "Ageless45" if age < 45 else "45to54" if age < 55 else "55to64" if age < 65 else "65orAbove"
    mapping_result["attributes"].append({"attribute": "QUS2rM78s6F", "value": str(age)})
    mapping_result["attributes"].append({"attribute": "cTFwAAW0and", "value": age_group})
    mapping_result["attributes"].append({"attribute": "Nymn5TH8GRu", "value": patient_resource["gender"].capitalize()})

     # Add orgUnit to enrollments
    mapping_result["enrollments"][0]["orgUnit"] = mapping_result.get("orgUnit")

    # Send the payload to DHIS2 trackedEntityInstances
    response = requests.post(
        f"{DHIS2_SERVER_URL}/trackedEntityInstances",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Basic " + base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
        },
        json=mapping_result
    )
    print(response)
    # print(mapping_result)
    # Save the mapping result

    mapping_ = requests.post(
        "http://localhost:5001/patient-risk-test",
        headers={"Content-Type": "application/json"},
        json=mapping_result
    )
    # MAPPING_RESULTS[count] = mapping_result
    # count += 1

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

