-- every workflow on every visible repository; a scheduled workflow is a promise the drill
-- catalogue must hold (memory: GitHub cron drops schedules)
select 'workflow' as type, repository_full_name || ':' || path as id, name
from github_workflow
where repository_full_name in (select name_with_owner from github_my_repository)
order by 2;
