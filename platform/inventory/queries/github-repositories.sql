-- every repository the App installation can see: id is the full name, the same string a
-- github_repository resource in the OpenTofu state would carry as its id
select 'repository' as type, name_with_owner as id, name_with_owner as name
from github_my_repository
order by name_with_owner;
