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

declare -A locationArray
declare -A MAPPING_RESULTS
count=0

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
  "$FHIR_SERVER_URL/fhir/Location?_count=100" | jq -r '.entry[] | .resource | "\(.id) \(.name)"')

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
  $FHIR_SERVER_URL/fhir/Patient?_lastUpdated=ge2024-03-15T00:00:00Z&_lastUpdated=le2024-03-15T23:59:59)


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
  echo "$PATIENT_RESOURCE"
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
        
        # Calculate age from birthday
        birth_date=$(echo "$PATIENT_RESOURCE" | jq -r '.birthDate')
        current_year=$(date +"%Y")
        birth_year=$(date -d "$birth_date" +"%Y")
        age=$((current_year - birth_year))
        
        # Send the updated patient resource to the OpenHIM Mapping Mediator
        MAPPING_RESULT=$(curl -s -X POST \
          -H "Content-Type: application/json" \
          -d "$PATIENT_RESOURCE" \
          "http://localhost:5001/fhir-to-tei")

        # Update the age attribute in the mapping result
        MAPPING_RESULT=$(echo "$MAPPING_RESULT" | jq '.attributes |= map(if .attribute == "QUS2rM78s6F" then .value = "'"$age"'" else . end)')

        # Update the age attribute in the mapping result
        case $age in
          [1-44])
            age_group="Ageless45"
            ;;
          45|4[6-9])
            age_group="45to54"
            ;;
          5[0-9]|6[0-4])
            age_group="55to64"
            ;;
          *)
            age_group="65orAbove"
            ;;
        esac

        # Update the age attribute in the mapping result
        MAPPING_RESULT=$(echo "$MAPPING_RESULT" | jq '.attributes |= map(if .attribute == "cTFwAAW0and" then .value = "'"$age_group"'" else . end)')
        
        # Update the gender attribute in the mapping result
        gender=$(echo "$PATIENT_RESOURCE" | jq -r '.gender' | awk '{print toupper(substr($0, 1, 1)) tolower(substr($0, 2))}')
        MAPPING_RESULT=$(echo "$MAPPING_RESULT" | jq '.attributes |= map(if .attribute == "Nymn5TH8GRu" then .value = "'"$gender"'" else . end)')

        # Save the mapping result to another variable
        # echo "Mapping Result:"
        echo "$MAPPING_RESULT"
        # MAPPING_RESULTS[$count]="$MAPPING_RESULT"
        # echo "$MAPPING_RESULTS[0]"
        # echo "$MAPPING_RESULTS"
         # Send the mapped result to DHIS2 trackedEntityInstances
        # RESULT=$(curl -X POST \
        #   -H "Content-Type: application/json" \
        #   -H "Authorization: Basic $(echo -n "$USERNAME:$PASSWORD" | base64)" \
        #   -d "$MAPPING_RESULT" \
        #   "$DHIS2_SERVER_URL/trackedEntityInstances")

        # echo $RESULT
      else
        echo "Location name does not exist in orgunits.json: $location_name"
      fi
    fi
  fi
  ((count++))
done


echo $SCREENED_CLIENTS
# Remove temporary files
rm "$PATIENT_TMP_FILE"

echo $CLIENTS_IDS
