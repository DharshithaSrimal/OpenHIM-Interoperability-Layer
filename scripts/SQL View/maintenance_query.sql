SELECT
	ORG_UNIT,
	FULL_NAME,
    SUM(clients_registered) AS total_clients_registered,
    SUM(screening_not_required) AS total_screening_not_required,
    SUM(screenings_due) AS total_screenings_due,
    SUM(clients_screened) AS total_clients_screened,
    SUM(clients_not_consent_to_screening) AS total_clients_not_consent_to_screening,
    SUM(clients_referred) AS total_clients_referred,
    SUM(phone_calls_due) AS total_phone_calls_due,
    SUM(phone_calls_overdue) AS total_phone_calls_overdue,
    SUM(phone_calls_completed) AS total_phone_calls_completed,
    SUM(home_visits_due) AS total_home_visits_due,
    SUM(home_visits_overdue) AS total_home_visits_overdue,
    SUM(home_completed) AS total_home_completed,
	CREATED_DATE,
	USER_ROLE,
	DSD
FROM view_do_performance2
GROUP BY ORG_UNIT, FULL_NAME, CREATED_DATE, USER_ROLE, DSD;