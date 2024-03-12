#!/bin/bash

# Replace these values with your Keycloak and FHIR server details
KEYCLOAK_URL="http://188.166.213.172:8081/realms/wdf_stage/protocol/openid-connect/token"
FHIR_SERVER_URL="http://188.166.213.172:8082"

CLIENT_ID="cHIMS Client"
CLIENT_SECRET="lvUTECeWLcHfyj0UZ5AI0q0t4X67vOaS"
GRANT_TYPE="client_credentials"

START_DATE=$(date +"%Y-%m-%dT00:00:00Z")
END_DATE=$(date +"%Y-%m-%dT23:59:59Z")

# DHIS2 
DHIS2_SERVER_URL="http://localhost:8084/dhis/api"
USERNAME="admin"
PASSWORD="district"

declare -A locationArray  # Define locationArray here

# Get Keycloak token
TOKEN_RESPONSE=$(curl -s -X POST \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "grant_type=$GRANT_TYPE" \
  $KEYCLOAK_URL)

# Extract access token from the response
ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')

##### FHIR Location setup #####

# Send FHIR request to get all locations and process it in a loop
while IFS= read -r location_info; do
  # Split the location_info into ID and name
  location_id=$(echo "$location_info" | awk '{print $1}')
  location_name=$(echo "$location_info" | awk '{$1=""; print $0}' | xargs)
  # Save locations to an array
  locationArray[$location_id]="$location_name"
done < <(curl -s -X GET \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  "$FHIR_SERVER_URL/fhir/Location" | jq -r '.entry[] | .resource | "\(.id) \(.name)"')

##### End FHIR Location setup #####

##### Org units #####

orgunits=$(cat orgunits.json)
# Loop through each org unit and print its display name and ID
#echo "${orgunits}" | jq -r '.[] | "Display Name: \(.displayName)\nID: \(.id)\n"'

##### End org units #####

##### Patient setup #####

# Send FHIR request to get clients registered per the day
CLIENTS_REGISTERED=$(curl -s -X GET \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  $FHIR_SERVER_URL/fhir/Patient?_lastUpdated=ge2023-07-20T00:00:00Z&_lastUpdated=le2023-10-11T00:00:00)

# Save FHIR response to a temporary file
PATIENT_TMP_FILE=$(mktemp)
echo "$CLIENTS_REGISTERED" > "$PATIENT_TMP_FILE"

# Loop through each patient ID and fetch patient resource
jq -r '.entry[].resource.id' "$PATIENT_TMP_FILE" | while IFS= read -r patient_id; do
  # Remove leading/trailing whitespaces if any
  patient_id=$(echo "$patient_id" | xargs)

  # Send request to get patient resource
  PATIENT_RESOURCE=$(curl -s -X GET \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    "$FHIR_SERVER_URL/fhir/Patient/$patient_id")

  # Check if the patient resource is empty or contains an error message
  if [ -z "$PATIENT_RESOURCE" ] || [ "$(echo "$PATIENT_RESOURCE" | jq -r '.issue')" != "null" ]; then
    echo "Error fetching patient resource for ID $patient_id"
  else
    # Extract the Practitioner Location code
    practitioner_location_code=$(echo "$PATIENT_RESOURCE" | jq -r '.meta.tag[] | select(.system == "https://smartregister.org/location-tag-id") | .code')
    
    # Remove leading/trailing whitespaces if any
    practitioner_location_code=$(echo "$practitioner_location_code" | xargs)
    
    # Use locationArray inside the loop
    location_name=${locationArray[$practitioner_location_code]}
    
    if [ -z "$location_name" ]; then
      echo "Location name not found for code: $practitioner_location_code"
    else
       # Check if the location name exists in the orgunits.json file
      if jq -e '.[] | select(.displayName == "'"$location_name"'")' orgunits.json > /dev/null; then
        # Get the location ID for the matching location name
        location_id=$(jq -r '.[] | select(.displayName == "'"$location_name"'") | .id' orgunits.json)
        PATIENT_RESOURCE=$(echo "$PATIENT_RESOURCE" | jq --arg loc_id "$location_id" '.meta.tag |= map(if .system == "https://smartregister.org/location-tag-id" then .code = $loc_id else . end)')
        
        # Print the updated patient resource
        echo "Updated Patient Resource:"
        echo "$PATIENT_RESOURCE"
      
      else
        echo "Location name does not exist in orgunits.json: $location_name"
      fi
    fi
  fi
done

# Remove temporary files
rm "$PATIENT_TMP_FILE"

echo $CLIENTS_IDS
