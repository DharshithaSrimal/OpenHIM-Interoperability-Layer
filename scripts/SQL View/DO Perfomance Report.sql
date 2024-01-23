SELECT
    tei.createdbyuserinfo->>'username' AS created_by_code,
    COUNT(DISTINCT tei.*) AS CLIENTS_REGISTERED,
	COUNT(DISTINCT CASE WHEN psi.eventdatavalues->'caq1Rf8wDx7'->>'value' != 'lowrisk' THEN 1 ELSE NULL END) AS CLIENTS_AT_RISK,
	COUNT(DISTINCT CASE WHEN psi.eventdatavalues->'caq1Rf8wDx7'->>'value' = 'lowrisk' THEN 1 ELSE NULL END) AS CLIENTS_NOT_AT_RISK,
    COUNT(DISTINCT CASE WHEN psi.eventdatavalues->'igk7wHUjNoY'->>'value' = 'false' THEN 1 ELSE NULL END) AS CLIENTS_NOT_CONSENT_TO_SCREENING,
	COUNT(DISTINCT CASE WHEN psi.eventdatavalues->'H96DVMnlKbi'->>'value' != NULL THEN 1 ELSE 0 END) AS CLIENTS_REFERRED,
	COUNT(DISTINCT CASE WHEN psi.eventdatavalues->'H96DVMnlKbi'->>'value' = NULL THEN 1 ELSE 0 END) AS CLIENTS_NOT_REFERRED
FROM
    trackedentityinstance AS tei
INNER JOIN userinfo AS ui ON ui.username = tei.createdbyuserinfo->>'username'
INNER JOIN programstageinstance AS psi ON ui.username = psi.createdbyuserinfo->>'username'
GROUP BY
    tei.createdbyuserinfo->>'username';

