create view vw_stacked_bar_view_iterations as
select
	iteration,
	total_prev,
	total_new,
	total_prev*100.0/(total_prev + total_new) as total_prev_pct,
	total_new*100.0/(total_prev + total_new) as total_new_pct
from (
select iteration*1 as iteration,
	sum(len_prev_set) as total_prev,
	sum(len_new_set) as total_new
from hc_iteration_views
group by 1
)
order by iteration asc;

create view vw_stacked_bar_exceptions_iterations as
select
	iteration,
	total_prev,
	total_new,
	total_prev*100.0/(total_prev + total_new) as total_prev_pct,
	total_new*100.0/(total_prev + total_new) as total_new_pct
from (
select iteration*1 as iteration,
	sum(len_prev_set) as total_prev,
	sum(len_new_set) as total_new
from hc_iteration_exceptions
group by 1
)
order by iteration asc;


create view vw_stacked_bar_exception_sites_iterations as
select
	iteration,
	total_prev,
	total_new,
	total_prev*100.0/(total_prev + total_new) as total_prev_pct,
	total_new*100.0/(total_prev + total_new) as total_new_pct
from (
select iteration*1 as iteration,
	sum(len_prev_set) as total_prev,
	sum(len_new_set) as total_new
from hc_iteration_exception_sites
group by 1
)
order by iteration asc;


create view vw_views_discovery_per_package_per_iteration as
select
	iteration*1 as iteration,
	(select count(distinct(package_name))
	from hc_iteration_views a
	where a.iteration=iterations.iteration
	and len_new_set*1.0>0.0) as packages_with_new_items,
	(select count(distinct(package_name))
	from hc_iteration_views a
	where a.iteration=iterations.iteration) as total_packages
from (
select distinct(iteration) from hc_iteration_views ) as iterations
group by 1
order by 1;


create view vw_exception_sites_discovery_per_package_per_iteration as
select
	iteration*1 as iteration,
	(select count(distinct(package_name))
	from hc_iteration_exception_sites a
	where a.iteration=iterations.iteration
	and len_new_set*1.0>0.0) as packages_with_new_items,
	(select count(distinct(package_name))
	from hc_iteration_exception_sites a
	where a.iteration=iterations.iteration) as total_packages
from (
select distinct(iteration) from hc_iteration_exception_sites ) as iterations
group by 1
order by 1;


create view vw_exception_discovery_per_package_per_iteration as
select
	iteration*1 as iteration,
	(select count(distinct(package_name))
	from hc_iteration_exceptions a
	where a.iteration=iterations.iteration
	and len_new_set*1.0>0.0) as packages_with_new_items,
	(select count(distinct(package_name))
	from hc_iteration_exceptions a
	where a.iteration=iterations.iteration) as total_packages
from (
select distinct(iteration) from hc_iteration_exceptions ) as iterations
group by 1
order by 1;




create view vw_scored_exception_sites as
select * from hc_iteration_exception_sites where score*1.0>0.0 and iteration*1.0 > 0
order by iteration*1.0 desc;


create view vw_scored_exceptions as
select * from hc_iteration_exceptions where score*1.0>0.0 and iteration*1.0 > 0
order by iteration*1.0 desc;


create view vw_scored_views as
select * from hc_iteration_views where score*1.0>0.0 and iteration*1.0 > 0
order by iteration*1.0 desc;


create view vw_discovery_per_package_per_iteration as
select * from (
select 'UI Elements' as category, iteration, packages_with_new_items from vw_views_discovery_per_package_per_iteration
union ALL
select 'Exception-Sites' as category, iteration, packages_with_new_items from vw_exception_sites_discovery_per_package_per_iteration
)
order by category, iteration;