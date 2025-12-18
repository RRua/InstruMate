create view vw_scored_exception_sites as
select * from hc_iteration_exception_sites where score*1.0>0.0 and iteration*1.0 > 0
order by iteration*1.0 desc;


create view vw_scored_exceptions as
select * from hc_iteration_exceptions where score*1.0>0.0 and iteration*1.0 > 0
order by iteration*1.0 desc;


create view vw_scored_views as
select * from hc_iteration_views where score*1.0>0.0 and iteration*1.0 > 0
order by iteration*1.0 desc;


create view vw_common_exception_sites as
select site, count(distinct(package_name)) common_packages, count(*) as qtd
from hc_exception_sites_with_details
group by 1
order by 2 desc, 3 desc;


create view vw_score_evolution as
select * from (
select 'view_score_count' as score_category, package_name, iteration,
	(select count(distinct(package_name)) from hc_iteration_views b where score*1.0>0.0
	and a.iteration=b.iteration and a.package_name=b.package_name) as qtd_scored_apps
from hc_iteration_views a
group by 1,2,3
--order by iteration*1.0
union all
select 'exception_score_count' as score_category, package_name, iteration,
	(select count(distinct(package_name)) from hc_iteration_exceptions b where score*1.0>0.0
	and a.iteration=b.iteration  and a.package_name=b.package_name) as qtd_scored_apps
from hc_iteration_exceptions a
group by 1,2,3
--order by iteration*1.0
union all
select 'exception_site_score_count' as score_category, package_name, iteration,
	(select count(distinct(package_name)) from hc_iteration_exception_sites b where score*1.0>0.0
	and a.iteration=b.iteration  and a.package_name=b.package_name) as qtd_scored_apps
from hc_iteration_exception_sites a
group by 1,2,3
--order by iteration*1.0
)
order by score_category, iteration*1.0;


create view vw_new_exception_sites_per_iteration as
select iteration*1 as iteration, avg(len_new_set*1.0) as avg_new_items
from hc_iteration_exception_sites group by 1
order by iteration*1 asc;


create view vw_new_views_per_iteration as
select iteration*1 as iteration, avg(len_new_set*1.0) as avg_new_items
from hc_iteration_views group by 1
order by iteration*1 asc;


create view vw_new_exceptions_per_iteration as
select iteration*1 as iteration, avg(len_new_set*1.0) as avg_new_items
from hc_iteration_exceptions group by 1
order by iteration*1 asc;


create view vw_pkgs_with_exceptions_seen_and_not_seen as
select * from (
	select 'packages_with_exceptions_so_far' as category, iteration, qtd_pkgs_so_far
	from (
	select  iteration,
		(select count(distinct(package_name)) from hc_iteration_views) as qtd_packages,
		(select count(distinct(package_name)) from hc_iteration_exception_sites b where iterations.iteration>=b.iteration*1 and b.score*1.0>0.0) as qtd_pkgs_so_far
	from
	(select DISTINCT(iteration*1) as iteration from hc_iteration_views) iterations
	)
	union all
	select 'packages_without_any_exceptions' as category, iteration, qtd_packages-qtd_pkgs_so_far
	from (
	select  iteration,
		(select count(distinct(package_name)) from hc_iteration_views) as qtd_packages,
		(select count(distinct(package_name)) from hc_iteration_exception_sites b where iterations.iteration>=b.iteration*1 and b.score*1.0>0.0) as qtd_pkgs_so_far
	from
	(select DISTINCT(iteration*1) as iteration from hc_iteration_views) iterations
	)
) order by category, iteration;


create view vw_common_exceptions as
select exception_name, count(package_name) qtd_packages, sum(qtd_exceptions) ocurrences
from (
select exception_name, package_name, count(*) as qtd_exceptions from hc_exception_origins
group by exception_name, package_name
order by exception_name, qtd_exceptions desc
)
group by exception_name
order by qtd_packages desc;



create view vw_count_new_views_per_iteration as
select
	iteration*1 as iteration,
	(select sum(len_new_set)
	from hc_iteration_views a
	where a.iteration=iterations.iteration) as new_items
from (
select distinct(iteration) from hc_iteration_views ) as iterations
group by 1
order by 1;


create view vw_count_new_exception_sites_per_iteration as
select
	iteration*1 as iteration,
	(select sum(len_new_set)
	from hc_iteration_exception_sites a
	where a.iteration=iterations.iteration) as new_items
from (
select distinct(iteration) from hc_iteration_exception_sites ) as iterations
group by 1
order by 1;


create view vw_count_new_exceptions_per_iteration as
select
	iteration*1 as iteration,
	(select sum(len_new_set)
	from hc_iteration_exceptions a
	where a.iteration=iterations.iteration) as new_items
from (
select distinct(iteration) from hc_iteration_exceptions ) as iterations
group by 1
order by 1;

create view vw_saturation_new_items as
select * from (
select 'UI elements' as category, iteration, new_items from vw_count_new_views_per_iteration
union all
select 'Exception Sites' as category, iteration, new_items from vw_count_new_exception_sites_per_iteration
) order by 1,2;


create view vw_count_scored_exception_site_apps_per_iteration as
select
	iteration*1 as iteration,
	(select count(distinct(package_name))
	from hc_iteration_exception_sites a
	where a.iteration=iterations.iteration
	and a.score*1.0>0) as new_items
from (
select distinct(iteration) from hc_iteration_exception_sites ) as iterations
group by 1
order by 1;


create view vw_count_scored_view_apps_per_iteration as
select
	iteration*1 as iteration,
	(select count(distinct(package_name))
	from hc_iteration_views a
	where a.iteration=iterations.iteration
	and a.score*1.0>0) as new_items
from (
select distinct(iteration) from hc_iteration_views ) as iterations
group by 1
order by 1;


create view vw_count_scored_exception_apps_per_iteration as
select
	iteration*1 as iteration,
	(select count(distinct(package_name))
	from hc_iteration_exceptions a
	where a.iteration=iterations.iteration
	and a.score*1.0>0) as new_items
from (
select distinct(iteration) from hc_iteration_exceptions ) as iterations
group by 1
order by 1;

create view vw_saturation_scored_apps as
select * from (
select 'UI elements' as category, iteration, new_items from vw_count_scored_view_apps_per_iteration
union all
select 'Exception Sites' as category, iteration, new_items from vw_count_scored_exception_site_apps_per_iteration
) order by 1,2;


