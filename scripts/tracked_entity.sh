#!/bin/bash

# Replace these values with your Keycloak and FHIR server details
KEYCLOAK_URL="http://188.166.213.172:8081/realms/wdf_stage/protocol/openid-connect/token"
FHIR_SERVER_URL="http://188.166.213.172:8082"

CLIENT_ID="cHIMS Client"
CLIENT_SECRET="lvUTECeWLcHfyj0UZ5AI0q0t4X67vOaS"
GRANT_TYPE="client_credentials"

START_DATE=`date +"%Y-%m-%dT00:00:00Z"`
END_DATE=`date +"%Y-%m-%dT23:59:59Z"`

#PROGRAM
#PROGRAM STAGES

# Get Keycloak token
TOKEN_RESPONSE=$(curl -X POST \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "grant_type=$GRANT_TYPE" \
  $KEYCLOAK_URL)

# Extract access token from the response
ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')


########## Locations Setup ##########

declare -A locationArray

#Send FHIR request to get all locations
LOCATIONS=$(curl -s -X GET \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  "$FHIR_SERVER_URL/fhir/Location")

# Save FHIR response to a temporary file
LOCATION_TMP_FILE=$(mktemp)
echo "$LOCATIONS" > "$LOCATION_TMP_FILE"

# Loop through each location and store the resource ID as the key and the name as the value
jq -r '.entry[] | .resource | "\(.id) \(.name)"' "$LOCATION_TMP_FILE" | while IFS= read -r location_info; do
  # Split the location_info into ID and name
  location_id=$(echo "$location_info" | awk '{print $1}')
  echo $location_id
  location_name=$(echo "$location_info" | awk '{$1=""; print $2; print $3; print $4}' | xargs)
  echo $location_name
  #Save locations to an array

done

########## End Locations Setup ##########


########## Patrients Setup ##########

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

  # Print information for debugging
  #echo "$PATIENT_RESOURCE"

  # Check if the patient resource is empty or contains an error message
  if [ -z "$PATIENT_RESOURCE" ] || [ "$(echo "$PATIENT_RESOURCE" | jq -r '.issue')" != "null" ]; then
    echo "Error fetching patient resource for ID $patient_id"
  else
    # Process the patient resource as needed (you can print or manipulate it)
    
    #echo "$PATIENT_RESOURCE"

    # Extract the Practitioner Location code
    practitioner_location_code=$(echo "$PATIENT_RESOURCE" | jq -r '.meta.tag[] | select(.system == "https://smartregister.org/location-tag-id") | .code')
    
    # Remove leading/trailing whitespaces if any
    practitioner_location_code=$(echo "$practitioner_location_code" | xargs)

    # Print the Practitioner Location code
    #echo "Practitioner Location Code: $practitioner_location_code"
    
  fi
done

# Remove temporary file
rm "$PATIENT_TMP_FILE"

########## End Patients Setup ##########
# Array to store locations



echo $CLIENTS_IDS