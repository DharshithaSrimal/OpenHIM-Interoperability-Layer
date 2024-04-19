CREATE VIEW view_orgunitgroup_with_users AS
SELECT orgunitgroup.name, orgunitgroup.sharing                       
FROM orgunitgroup                                                                  
WHERE (EXISTS ( SELECT 1 FROM jsonb_object_keys((orgunitgroup.sharing -> 'users'::text)) key(key)));