# OpenHIM-Integration

## FHIR-DHIS2 Mapping
This project provides a comprehensive mapping between FHIR (Fast Healthcare Interoperability Resources) and DHIS2 (District Health Information System 2), enabling seamless data exchange between these two widely used healthcare platforms. The mapping encompasses the conversion of various FHIR resources into human-readable intermediate formats and the transformation of FHIR bundles into a format compatible with the DHIS2 REST API.

### Key Features
* Comprehensive FHIR-DHIS2 mapping for data interoperability
* Conversion of FHIR resources into human-readable intermediate formats
* Transformation of FHIR bundles into DHIS2 REST API-compatible format
* Data transformation 
* Data validation

### Usage
* Utilize the mapping to convert FHIR resources into human-readable intermediate formats for easier interpretation and analysis.
* Employ the transformation functionality to convert FHIR bundles into a format compatible with the DHIS2 REST API, enabling data submission to DHIS2.
* Leverage the mapping to establish seamless data exchange between FHIR and DHIS2, fostering interoperability and data utilization.

## How to run the solution
* Run docker-compose -f docker-compose.mongo.yml up -d
* Run docker-compose -f docker-compose.openhim.yml up -d
* Post the mappers to {url}:5001/endpoints
* Post the FHIR data to {url}:5001/defined-url
