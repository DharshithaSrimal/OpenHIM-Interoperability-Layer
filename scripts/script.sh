#!/bin/bash

# Replace these values with your Keycloak and FHIR server details
KEYCLOAK_URL="http://188.166.213.172:8081/realms/wdf_stage/protocol/openid-connect/token"
FHIR_SERVER_URL="http://188.166.213.172:8082"

CLIENT_ID="cHIMS Client"
CLIENT_SECRET="lvUTECeWLcHfyj0UZ5AI0q0t4X67vOaS"
GRANT_TYPE="client_credentials"
PASSWORD="your-password"

CURRENTDATE=`date +"%Y-%m-%d %T"`
echo $CURRENTDATE
END_DATE=$(date)

# Get Keycloak token
TOKEN_RESPONSE=$(curl -X POST \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "grant_type=$GRANT_TYPE" \
  $KEYCLOAK_URL)

# Extract access token from the response
ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')

# Send FHIR request using the obtained token
FHIR_RESPONSE=$(curl -s -X GET \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  $FHIR_SERVER_URL/fhir/_lastUpdated:gt=2023-07-05T00:00:00.000Z&_lastUpdated:lt=2023-09-07T00:00:00.000Z)

# Print FHIR response
echo $FHIR_RESPONSE
