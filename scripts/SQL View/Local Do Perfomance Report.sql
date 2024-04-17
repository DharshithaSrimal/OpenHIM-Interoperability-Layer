--CREATE VIEW view_do_performance AS
SELECT 
	ou.name AS ORG_UNIT,
    CONCAT(ui.firstname, ' ', ui.surname) AS FULL_NAME,
	COUNT(DISTINCT pi.uid) AS CLIENTS_REGISTERED,
	COUNT(DISTINCT CASE WHEN (psi.eventdatavalues->'Ar3IhGHG171'->>'value' = 'false' AND psi.status = 'COMPLETED' AND ps.name = 'Screening at the community') THEN psi.uid ELSE NULL END) AS SCREENING_NOT_REQUIRED,
	COUNT(DISTINCT CASE WHEN (psi.eventdatavalues->'igk7wHUjNoY'->>'value' = 'true' AND psi.status = 'ACTIVE' AND ps.name = 'Screening at the community' AND date_trunc('day', CURRENT_DATE) > psi.duedate) THEN psi.uid ELSE NULL END) AS SCREENINGS_DUE,
    COUNT(DISTINCT CASE WHEN (psi.eventdatavalues->'Ar3IhGHG171'->>'value' = 'true' AND psi.eventdatavalues->'igk7wHUjNoY'->>'value' = 'true' AND psi.status = 'COMPLETED' AND ps.name = 'Screening at the community' AND psi.eventdatavalues != '{}') THEN psi.uid ELSE NULL END) AS CLIENTS_SCREENED,
    COUNT(DISTINCT CASE WHEN (psi.eventdatavalues->'igk7wHUjNoY'->>'value' = 'false') THEN psi.uid ELSE NULL END) AS CLIENTS_NOT_CONSENT_TO_SCREENING,
    COUNT(DISTINCT CASE WHEN (psi.eventdatavalues->'H96DVMnlKbi'->>'value' IS NOT NULL) THEN psi.uid ELSE NULL END) AS CLIENTS_REFERRED,
	COUNT(DISTINCT CASE WHEN (psi.status = 'COMPLETED' AND ps.name = 'Follow-up' AND date_trunc('day', CURRENT_DATE) <= psi.duedate) THEN psi.uid ELSE NULL END) AS PHONE_CALLS_DUE,
	COUNT(DISTINCT CASE WHEN (psi.status = 'COMPLETED' AND ps.name = 'Follow-up' AND date_trunc('day', CURRENT_DATE) > psi.duedate) THEN psi.uid ELSE NULL END) AS PHONE_CALLS_OVERDUE,
	COUNT(DISTINCT CASE WHEN (psi.eventdatavalues->'igk7wHUjNoY'->>'value' = 'true' AND psi.eventdatavalues != '{}' AND psi.eventdatavalues->'TASK_STATUS'->>'value' = 'PHONE_CALL_COMPLETED' AND ps.name = 'Follow-up' AND psi.status = 'COMPLETED') THEN psi.uid ELSE NULL END) AS PHONE_CALLS_COMPLETED,
	COUNT(DISTINCT CASE WHEN (psi.eventdatavalues->'igk7wHUjNoY'->>'value' = 'true' AND psi.eventdatavalues != '{}' AND psi.eventdatavalues->'TASK_STATUS'->>'value' = 'PHONE_CALL_COMPLETED' AND ps.name = 'Follow-up' AND psi.status = 'COMPLETED' AND date_trunc('day', CURRENT_DATE) <= psi.duedate) THEN psi.uid ELSE NULL END) AS HOME_VISITS_DUE,
	COUNT(DISTINCT CASE WHEN (psi.eventdatavalues->'igk7wHUjNoY'->>'value' = 'true' AND psi.eventdatavalues != '{}' AND psi.eventdatavalues->'TASK_STATUS'->>'value' = 'PHONE_CALL_COMPLETED' AND ps.name = 'Follow-up' AND psi.status = 'COMPLETED' AND date_trunc('day', CURRENT_DATE) > psi.duedate) THEN psi.uid ELSE NULL END) AS HOME_VISITS_OVERDUE,
	COUNT(DISTINCT CASE WHEN (psi.eventdatavalues->'igk7wHUjNoY'->>'value' = 'true' AND psi.eventdatavalues != '{}' AND psi.eventdatavalues->'TASK_STATUS'->>'value' = 'HOME_COMPLETED' AND ps.name = 'Follow-up' AND psi.status = 'COMPLETED' AND date_trunc('day', CURRENT_DATE) > psi.duedate) THEN psi.uid ELSE NULL END) AS HOME_COMPLETED,
	DATE_TRUNC('day', pi.incidentdate) AS CREATED_DATE,
	ur.name AS USER_ROLE,
	oug.name AS DSD
FROM programstageinstance AS psi
INNER JOIN programinstance AS pi ON pi.programinstanceid = psi.programinstanceid
INNER JOIN trackedentityinstance AS tei ON tei.trackedentityinstanceid = pi.trackedentityinstanceid
INNER JOIN userinfo AS ui ON ui.userinfoid = tei.lastupdatedby
INNER JOIN programstage AS ps ON ps.programstageid = psi.programstageid
INNER JOIN userrolemembers AS urm ON urm.userid = ui.userinfoid
INNER JOIN userrole AS ur ON urm.userroleid = ur.userroleid
INNER JOIN organisationunit AS ou ON ou.organisationunitid = tei.organisationunitid 
INNER JOIN orgunitgroupmembers AS oum ON oum.organisationunitid = ou.organisationunitid
INNER JOIN orgunitgroup AS oug ON oug.orgunitgroupid = oum.orgunitgroupid
WHERE 
ur.name = 'Development Officer' 
AND tei.deleted = false
GROUP BY
    ou.name, ui.surname, ui.firstname, tei.createdbyuserinfo->>'username', ur.name, DATE_TRUNC('day', pi.incidentdate), oug.name;