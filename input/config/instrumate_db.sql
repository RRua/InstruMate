create view vw_failed_tools_sintetic as
select tool_name, tool_description, count(DISTINCT(package_name)) failed_apps
from variant_maker_tool_executions
where tool_success='False'
GROUP by 1,2,3;

create view vw_failed_tools_analytic as
select tool_name, tool_description, package_name failed_apps
from variant_maker_tool_executions
where tool_success='False'
GROUP by 1,2,3;


create view vw_pkg_splits as
select
	package_name,
	CASE
	WHEN length(splits)>0 THEN LENGTH(splits) - LENGTH(REPLACE(splits, ',', '')) +1
	ELSE 0
	END
	AS splits_count
from app_info
where original='True';


create view vw_variants_overview as
select
level_flag, levels_str,
features_flag, features_str,
maker_tag,
count(*) as qtd_variants,
(select count(DISTINCT(app_id)) from app_info where original = 'True') as qtd_originals
from app_info
where original='False'
group by 1,2,3,4,5;

create view vw_variants_details as
select
package_name,
level_flag,
levels_str,
features_flag,
features_str,
count(*) as qtd_variants
from app_info
where original='False'
group by 1,2,3,4,5;


create view vw_confirmed_native as
select app_id, package_name, source, relative_path from (
select app_id, package_name, source, relative_path from apk_native_classes
union all
select app_id, package_name, source, relative_path from apk_native_fields
union all
select app_id, package_name, source, relative_path from apk_native_imports
union all
select app_id, package_name, source, relative_path from apk_native_methods
union ALL
select app_id, package_name, source, relative_path from apk_native_debug_information
)
GROUP by app_id, package_name, source, relative_path;

create table tb_derived_confirmed_dalvik as
select app_id, package_name, source, relative_path from (
select app_id, package_name, source, relative_path from apk_dex_classes
union all
select app_id, package_name, source, relative_path from apk_dex_fields
union all
select app_id, package_name, source, relative_path from apk_dex_imports
union all
select app_id, package_name, source, relative_path from apk_dex_methods
union ALL
select app_id, package_name, source, relative_path from apk_dex_debug_information
)
GROUP by app_id, package_name, source, relative_path;

create table tb_derived_confirmed_native as
select app_id, package_name, source, relative_path from (
select app_id, package_name, source, relative_path from apk_native_classes
union all
select app_id, package_name, source, relative_path from apk_native_fields
union all
select app_id, package_name, source, relative_path from apk_native_imports
union all
select app_id, package_name, source, relative_path from apk_native_methods
union ALL
select app_id, package_name, source, relative_path from apk_native_debug_information
)
GROUP by app_id, package_name, source, relative_path;

select app_id, package_name, source, relative_path from (
select app_id, package_name, source, relative_path from apk_dex_classes
union all
select app_id, package_name, source, relative_path from apk_dex_fields
union all
select app_id, package_name, source, relative_path from apk_dex_imports
union all
select app_id, package_name, source, relative_path from apk_dex_methods
union ALL
select app_id, package_name, source, relative_path from apk_dex_debug_information
)
GROUP by app_id, package_name, source, relative_path;


create table tb_derived_native_not_on_lib_dir as
select app_id, package_name, relative_path
from vw_confirmed_native
where relative_path not like 'lib/%'
group by app_id, package_name, relative_path
order by package_name, relative_path;