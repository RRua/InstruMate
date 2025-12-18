create view vw_instrumate_checker_failed_results as
select * from instrumate_checker_result a where not exists
	(select 1 from instrumate_checker_result b where a.app_id=b.app_id and procedure_completed='True');


CREATE VIEW vw_instrumate_checker_failed_apps as
select distinct package_name, app_version, app_id, is_variant, variant_maker_tag,
	variant_flag, variant_flag_str, level_flag, level_flag_str, procedure_completed
	from instrumate_checker_result a where not exists
	(select 1 from instrumate_checker_result b where a.app_id=b.app_id and procedure_completed='True');


CREATE VIEW vw_instrumate_checker_fatal_errors as
select package_name, app_version, app_id, is_variant, variant_maker_tag,
	variant_flag, variant_flag_str, level_flag, level_flag_str, count(*)
	from logcat_messages
	where level='F'
group by  package_name, app_version, app_id, is_variant, variant_maker_tag,
	variant_flag, variant_flag_str, level_flag, level_flag_str
order by package_name;


CREATE VIEW vw_instrumate_checker_errors as
select package_name, app_version, app_id, is_variant, variant_maker_tag,
	variant_flag, variant_flag_str, level_flag, level_flag_str, count(*)
	from logcat_messages
	where level='E'
group by  package_name, app_version, app_id, is_variant, variant_maker_tag,
	variant_flag, variant_flag_str, level_flag, level_flag_str
order by package_name;


create view vw_failed_to_identify_package_pid as
select * from vw_instrumate_checker_failed_apps a where EXISTS(
select 1 from instrumate_checker_commands b where a.app_id=b.app_id and traceback_exception like '%Failed to identify PID for package%');


create view vw_apps_with_launcher_window as
select distinct package_name, app_version, app_id, is_variant, variant_maker_tag,
	variant_flag, variant_flag_str, level_flag, level_flag_str
from view_state_component_data where package='com.google.android.apps.nexuslauncher';


create view vw_other_failed_apps as
select * from vw_instrumate_checker_failed_apps a where not exists
(select 1 from vw_failed_to_identify_package_pid b where a.app_id=b.app_id);


drop view if EXISTS vw_all_success_apps;
CREATE VIEW vw_all_success_apps as
select package_name, app_version, app_id, is_variant, variant_maker_tag, variant_flag,
variant_flag_str, level_flag, level_flag_str, procedure_completed, failure_reason,
traceback_exception, total_secs from instrumate_checker_result a
where a.procedure_completed='True'
--and not exists(select 1 from vw_apps_with_launcher_window b where a.app_id=b.app_id)
--and not exists(select 1 from vw_other_failed_apps b where a.app_id=b.app_id)
--and not exists(select 1 from vw_instrumate_checker_fatal_errors b where a.app_id=b.app_id)
--and not exists(select 1 from vw_failed_to_identify_package_pid b where a.app_id=b.app_id)
;

drop view if exists vw_all_failed_apps;
CREATE VIEW vw_all_failed_apps as
select package_name, app_version, app_id, is_variant, variant_maker_tag, variant_flag,
variant_flag_str, level_flag, level_flag_str,
GROUP_CONCAT(procedure_completed,CHAR(10)||'----'||CHAR(10)) as procedure_completed ,
GROUP_CONCAT(failure_reason,CHAR(10)||'----'||CHAR(10)) as failure_reason,
GROUP_CONCAT(traceback_exception,CHAR(10)||'----'||CHAR(10)) as traceback_exception,
sum(total_secs) as total_secs from instrumate_checker_result a
where a.procedure_completed='False'
and not exists (select 1 from instrumate_checker_result b where a.app_id=b.app_id and b.procedure_completed='True')
--or exists(select 1 from vw_apps_with_launcher_window b where a.app_id=b.app_id)
--or exists(select 1 from vw_other_failed_apps b where a.app_id=b.app_id)
--or exists(select 1 from vw_instrumate_checker_fatal_errors b where a.app_id=b.app_id)
--or exists(select 1 from vw_failed_to_identify_package_pid b where a.app_id=b.app_id)
group by package_name, app_version, app_id, is_variant, variant_maker_tag, variant_flag,
variant_flag_str, level_flag, level_flag_str;

drop view if exists vw_all_checked_apps;
create view vw_all_checked_apps as
select package_name, app_version, app_id, is_variant, variant_maker_tag, variant_flag,
variant_flag_str, level_flag, level_flag_str,
GROUP_CONCAT(procedure_completed,CHAR(10)||'----'||CHAR(10)) as procedure_completed ,
GROUP_CONCAT(failure_reason,CHAR(10)||'----'||CHAR(10)) as failure_reason,
GROUP_CONCAT(traceback_exception,CHAR(10)||'----'||CHAR(10)) as traceback_exception,
sum(total_secs) as total_secs from instrumate_checker_result a
group by package_name, app_version, app_id, is_variant, variant_maker_tag, variant_flag,
variant_flag_str, level_flag, level_flag_str;

create view vw_action_units_per_app_instance as
select package_name, app_version,
view_signature, count(*) as qtd_views, count(app_id) as tested_apps
from view_state_action_units
group by package_name, app_version,
view_signature;

create view vw_components_per_app_instance as
select package_name, app_version,
signature, count(*) as qtd_views, count(app_id) as tested_apps
from view_state_component_data
group by package_name, app_version,
signature;


create view vw_instrumate_checker_result_completed as
select * from instrumate_checker_result a where procedure_completed='True'
and exists (
select * from vw_all_success_apps b where a.app_id=b.app_id
);


create view vw_instrumate_checker_result_completed_errors as
select * from instrumate_checker_result a where procedure_completed='False'
and exists (
select * from vw_all_success_apps b where a.app_id=b.app_id
);