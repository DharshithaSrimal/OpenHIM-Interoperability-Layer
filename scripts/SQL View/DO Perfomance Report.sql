--CREATE VIEW view_do_performance AS
SELECT
	ou.name AS ORG_UNIT,
    CONCAT(ui.firstname, ' ', ui.surname) AS FULL_NAME,
	COUNT(DISTINCT CASE WHEN (psi.status = 'ACTIVE' AND ps.name = 'Screening at the community' AND date_trunc('day', CURRENT_DATE) > psi.duedate) THEN psi.uid ELSE NULL END) AS SCREENINGS_DUE,
    COUNT(DISTINCT CASE WHEN (psi.status = 'COMPLETED' AND ps.name = 'Screening at the community') THEN psi.uid ELSE NULL END) AS CLIENTS_SCREENED,
    COUNT(DISTINCT CASE WHEN psi.eventdatavalues->'igk7wHUjNoY'->>'value' = 'false' THEN psi.uid ELSE NULL END) AS CLIENTS_NOT_CONSENT_TO_SCREENING,
    COUNT(DISTINCT CASE WHEN psi.eventdatavalues->'H96DVMnlKbi'->>'value' IS NOT NULL THEN psi.uid ELSE NULL END) AS CLIENTS_REFERRED,
	COUNT(DISTINCT CASE WHEN (psi.status = 'COMPLETED' AND ps.name = 'Screening at the community' AND date_trunc('day', CURRENT_DATE) <= psi.duedate) THEN psi.uid ELSE NULL END) AS PHONE_CALLS_DUE,
	COUNT(DISTINCT CASE WHEN (psi.status = 'COMPLETED' AND ps.name = 'Screening at the community' AND date_trunc('day', CURRENT_DATE) > psi.duedate) THEN psi.uid ELSE NULL END) AS PHONE_CALLS_OVERDUE,
	COUNT(DISTINCT CASE WHEN (psi.eventdatavalues != '{}' AND psi.eventdatavalues->'TASK_STATUS'->>'value' = 'PHONE_CALL_COMPLETED' AND ps.name = 'Screening at the community' AND psi.status = 'COMPLETED') THEN psi.uid ELSE NULL END) AS PHONE_CALLS_COMPLETED,
	COUNT(DISTINCT CASE WHEN (psi.eventdatavalues != '{}' AND psi.eventdatavalues->'TASK_STATUS'->>'value' = 'PHONE_CALL_COMPLETED' AND ps.name = 'Screening at the community' AND psi.status = 'COMPLETED' AND date_trunc('day', CURRENT_DATE) <= psi.duedate) THEN psi.uid ELSE NULL END) AS HOME_VISITS_DUE,
	COUNT(DISTINCT CASE WHEN (psi.eventdatavalues != '{}' AND psi.eventdatavalues->'TASK_STATUS'->>'value' = 'PHONE_CALL_COMPLETED' AND ps.name = 'Screening at the community' AND psi.status = 'COMPLETED' AND date_trunc('day', CURRENT_DATE) > psi.duedate) THEN psi.uid ELSE NULL END) AS HOME_VISITS_OVERDUE,
	COUNT(DISTINCT CASE WHEN (psi.eventdatavalues != '{}' AND psi.eventdatavalues->'TASK_STATUS'->>'value' = 'HOME_COMPLETED' AND ps.name = 'Screening at the community' AND psi.status = 'COMPLETED' AND date_trunc('day', CURRENT_DATE) > psi.duedate) THEN psi.uid ELSE NULL END) AS HOME_COMPLETED,
	DATE_TRUNC('day', psi.created) AS CREATED_DATE,
	ur.name AS USER_ROLE
	--tei.createdbyuserinfo->>'username' AS created_by_code
FROM
    trackedentityinstance AS tei
INNER JOIN userinfo AS ui ON ui.username = tei.createdbyuserinfo->>'username'
LEFT JOIN programstageinstance AS psi ON ui.username = psi.createdbyuserinfo->>'username'
INNER JOIN programstage AS ps ON ps.programstageid = ps.programstageid
INNER JOIN userrolemembers AS urm ON urm.userid = ui.userinfoid
INNER JOIN userrole AS ur ON urm.userroleid = ur.userroleid
INNER JOIN organisationunit AS ou ON ou.organisationunitid = tei.organisationunitid  
WHERE ur.name = 'Development Officer' 
AND tei.deleted = false
AND ps.name = 'Screening at the community'
GROUP BY
    ou.name, ui.surname, ui.firstname, tei.createdbyuserinfo->>'username', ur.name, DATE_TRUNC('day', psi.created);
