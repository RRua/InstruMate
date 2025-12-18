create view vw_failed_downloads as
select DISTINCT package_name from app_downloaded a where not exists (
select 1 from app_downloaded b where a.package_name=b.package_name
and b.success='True'
);

create view vw_detailed_failed_downloads as
select package_name, summary_msg, stdout,stderr, traceback_exception, max(attempt_index)+1 attempts, sum(total_secs) time_spent from app_downloaded a where not exists (
select 1 from app_downloaded b where a.package_name=b.package_name
and b.success='True'
)
group by package_name, summary_msg, stdout,stderr, traceback_exception order by time_spent desc;