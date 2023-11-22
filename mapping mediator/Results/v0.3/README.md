# DHIS2 Facility data to FHIR Bundle
This sample endpoint requests FHIR patient and risk assesment bundle data sets and converts it into an intermediate format

## Features
Validation - Ensure that the incoming lookup request data contains the required fields, and that they are in the correct format
Requests - The requests here orchestrate data for this transaction. The lookup requests gather the required data. The response request send that finalised output data to a DHIS2 instance
Mapping - Create data to transfer to DHIS2 instance
Constants - Contains all the static values required for constructing intermediate format