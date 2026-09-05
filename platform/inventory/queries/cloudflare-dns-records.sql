select 'dns_record' as type, r.id, r.name || ' ' || r.type as name
from cloudflare_dns_record r
join cloudflare_zone z on z.id = r.zone_id
order by r.name;
