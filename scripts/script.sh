#!/bin/bash

# Replace these values with your Keycloak and FHIR server details
KEYCLOAK_URL="http://188.166.213.172:8081/realms/wdf_stage/protocol/openid-connect/token"
FHIR_SERVER_URL="http://188.166.213.172:8082"

CLIENT_ID="cHIMS Client"
CLIENT_SECRET="lvUTECeWLcHfyj0UZ5AI0q0t4X67vOaS"
GRANT_TYPE="client_credentials"

START_DATE=`date +"%Y-%m-%dT00:00:00Z"`
END_DATE=`date +"%Y-%m-%dT23:59:59Z"`

# Get Keycloak token
TOKEN_RESPONSE=$(curl -X POST \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "grant_type=$GRANT_TYPE" \
  $KEYCLOAK_URL)

# Extract access token from the response
ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')

# Send FHIR request to get clients registered per the day
CLIENTS_REGISTERED=$(curl -s -X GET \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  $FHIR_SERVER_URL/fhir/Patient?_lastUpdated=ge2023-07-20T00:00:00Z&_lastUpdated=le2023-10-11T00:00:00)

# Save FHIR response to a temporary file
TMP_FILE=$(mktemp)
echo "$CLIENTS_REGISTERED" > "$TMP_FILE"

# Loop through each patient ID and fetch patient resource
jq -r '.entry[].resource.id' "$TMP_FILE" | while IFS= read -r patient_id; do
  # Remove leading/trailing whitespaces if any
  patient_id=$(echo "$patient_id" | xargs)

  # Send request to get patient resource
  PATIENT_RESOURCE=$(curl -s -X GET \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    "$FHIR_SERVER_URL/fhir/Patient/$patient_id")

  # Print information for debugging
  echo "$PATIENT_RESOURCE"

  # Check if the patient resource is empty or contains an error message
  if [ -z "$PATIENT_RESOURCE" ] || [ "$(echo "$PATIENT_RESOURCE" | jq -r '.issue')" != "null" ]; then
    echo "Error fetching patient resource for ID $patient_id"
  else
    # Process the patient resource as needed (you can print or manipulate it)
    echo "Patient Resource for ID $patient_id:"
    echo "$PATIENT_RESOURCE"
  fi
done

# Remove temporary file
rm "$TMP_FILE"

echo $CLIENTS_IDS