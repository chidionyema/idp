-- every workflow on every visible repository; a scheduled workflow is a promise the drill
-- catalogue must hold (memory: GitHub cron drops schedules). github_workflow requires
-- repository_full_name as a key column; a join pushes it down, a sub-select does not.
select 'workflow' as type, w.repository_full_name || ':' || w.path as id, w.name
from github_my_repository r
join github_workflow w on w.repository_full_name = r.name_with_owner
order by 2;
