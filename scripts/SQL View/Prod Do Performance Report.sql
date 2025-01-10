CREATE VIEW view_do_performance AS
 SELECT ou.name AS org_unit,
    concat(ui.firstname, ' ', ui.surname) AS full_name,
    count(DISTINCT pi.uid) AS clients_registered,
    count(DISTINCT
        CASE
            WHEN psi.status::text = 'ACTIVE'::text AND ps.name::text = 'Follow - up Status'::text AND ((psi.eventdatavalues -> 'VCQ4bYBggPB'::text) ->> 'value'::text) = 'Registration_Completed'::text AND (pi.enrollmentdate + '7 days'::interval) > date_trunc('day'::text, CURRENT_DATE::timestamp with time zone) THEN psi.uid
            ELSE NULL::character varying
        END) AS screenings_due,
    count(DISTINCT
        CASE
            WHEN psi.status::text = 'ACTIVE'::text AND ps.name::text = 'Follow - up Status'::text AND ((psi.eventdatavalues -> 'VCQ4bYBggPB'::text) ->> 'value'::text) = 'Registration_Completed'::text AND (pi.enrollmentdate + '7 days'::interval) <= date_trunc('day'::text, CURRENT_DATE::timestamp with time zone) THEN psi.uid
            ELSE NULL::character varying
        END) AS screenings_overdue,
    count(DISTINCT
        CASE
            WHEN ps.name::text = 'Screening at the community'::text AND ((psi.eventdatavalues -> 'igk7wHUjNoY'::text) ->> 'value'::text) = 'false'::text THEN psi.uid
            ELSE NULL::character varying
        END) AS clients_not_consent_to_screening,
    count(DISTINCT
        CASE
            WHEN ps.name::text = 'Screening at the community'::text AND ((psi.eventdatavalues -> 'vjABPom3WZD'::text) ->> 'value'::text) = 'false'::text THEN psi.uid
            ELSE NULL::character varying
        END) AS screening_not_required,
    count(DISTINCT
        CASE
            WHEN ps.name::text = 'Screening at the community'::text AND ((psi.eventdatavalues -> 'igk7wHUjNoY'::text) ->> 'value'::text) = 'true'::text AND ((psi.eventdatavalues -> 'vjABPom3WZD'::text) ->> 'value'::text) = 'true'::text THEN psi.uid
            ELSE NULL::character varying
        END) AS clients_screened,
    count(DISTINCT
        CASE
            WHEN ((psi.eventdatavalues -> 'mPxpSPjgwkI'::text) ->> 'value'::text) = 'true'::text AND psi.status::text = 'COMPLETED'::text AND ps.name::text = 'Screening at the community'::text THEN psi.uid
            ELSE NULL::character varying
        END) AS clients_referred,
    count(DISTINCT
        CASE
            WHEN ((psi.eventdatavalues -> 'mPxpSPjgwkI'::text) ->> 'value'::text) = 'false'::text AND psi.status::text = 'COMPLETED'::text AND ps.name::text = 'Screening at the community'::text THEN psi.uid
            ELSE NULL::character varying
        END) AS clients_not_referred,
    count(DISTINCT
        CASE
            WHEN ps.name::text = 'Screening at the HLC'::text AND psi.status::text = 'COMPLLETED'::text THEN psi.uid
            ELSE NULL::character varying
        END) AS client_visits,
    count(DISTINCT
        CASE
            WHEN psi.status::text = 'ACTIVE'::text AND ps.name::text = 'Follow - up Status'::text AND ((psi.eventdatavalues -> 'VCQ4bYBggPB'::text) ->> 'value'::text) = 'Screening_Completed'::text AND (psi.executiondate + '14 days'::interval) < date_trunc('day'::text, CURRENT_DATE::timestamp with time zone) AND (psi.executiondate + '30 days'::interval) >= date_trunc('day'::text, CURRENT_DATE::timestamp with time zone) THEN psi.uid
            ELSE NULL::character varying
        END) AS phone_calls_due,
    count(DISTINCT
        CASE
            WHEN psi.status::text = 'ACTIVE'::text AND ps.name::text = 'Follow - up Status'::text AND ((psi.eventdatavalues -> 'VCQ4bYBggPB'::text) ->> 'value'::text) = 'Screening_Completed'::text AND (psi.executiondate + '30 days'::interval) < date_trunc('day'::text, CURRENT_DATE::timestamp with time zone) THEN psi.uid
            ELSE NULL::character varying
        END) AS phone_calls_overdue,
    count(DISTINCT
        CASE
            WHEN psi.status::text = 'ACTIVE'::text AND ps.name::text = 'Follow - up Status'::text AND ((psi.eventdatavalues -> 'VCQ4bYBggPB'::text) ->> 'value'::text) = 'Phone_Calls_Completed'::text AND (psi.executiondate + '14 days'::interval) < date_trunc('day'::text, CURRENT_DATE::timestamp with time zone) AND (psi.executiondate + '21 days'::interval) >= date_trunc('day'::text, CURRENT_DATE::timestamp with time zone) THEN psi.uid
            ELSE NULL::character varying
        END) AS home_visits_due,
    count(DISTINCT
        CASE
            WHEN psi.status::text = 'ACTIVE'::text AND ps.name::text = 'Follow - up Status'::text AND ((psi.eventdatavalues -> 'VCQ4bYBggPB'::text) ->> 'value'::text) = 'Phone_Calls_Completed'::text AND (psi.executiondate + '21 days'::interval) < date_trunc('day'::text, CURRENT_DATE::timestamp with time zone) THEN psi.uid
            ELSE NULL::character varying
        END) AS home_visits_overdue,
    date_trunc('day'::text, pi.incidentdate) AS created_date,
    ur.name AS user_role,
    oug.name AS dsd
   FROM programstageinstance psi
     JOIN programinstance pi ON pi.programinstanceid = psi.programinstanceid
     JOIN trackedentityinstance tei ON tei.trackedentityinstanceid = pi.trackedentityinstanceid
     JOIN trackedentityattributevalue tv ON tv.trackedentityinstanceid = tei.trackedentityinstanceid
     JOIN userinfo ui ON tv.value::text = ui.username::text
     JOIN programstage ps ON ps.programstageid = psi.programstageid
     JOIN userrolemembers urm ON urm.userid = ui.userinfoid
     JOIN userrole ur ON urm.userroleid = ur.userroleid
     JOIN organisationunit ou ON ou.organisationunitid = tei.organisationunitid
     JOIN orgunitgroupmembers oum ON oum.organisationunitid = ou.organisationunitid
     JOIN orgunitgroup oug ON oug.orgunitgroupid = oum.orgunitgroupid
  WHERE (ur.name::text = 'Development Officer'::text OR ur.name::text = 'Public Health Midwife'::text) AND tei.deleted = false
  GROUP BY ou.name, ui.surname, ui.firstname, (tei.createdbyuserinfo ->> 'username'::text), ur.name, (date_trunc('day'::text, pi.incidentdate)), oug.name;