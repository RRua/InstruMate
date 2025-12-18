CREATE TABLE tb_excluded_packages (
    package_name TEXT PRIMARY KEY
);

CREATE VIEW vw_completed_hc_variants as
select package_name, app_id, variant_maker_tag, variant_flag_str, level_flag_str, count(distinct(hc_attempt)) as qtd_attempts
from consolidated_all_success_apps a
where procedure_completed='True'
and package_name not in (select package_name from tb_excluded_packages)
group by package_name, app_id, variant_maker_tag, variant_flag_str, level_flag_str
having qtd_attempts in (select count(distinct(hc_attempt)) from consolidated_hc_results)
order by package_name, app_id, variant_maker_tag, hc_attempt;

CREATE VIEW vw_incomplete_hc_variants as
select package_name, app_id, variant_maker_tag, variant_flag_str, level_flag_str, count(distinct(hc_attempt)) as qtd_attempts
from consolidated_all_success_apps a
where procedure_completed='True'
and package_name not in (select package_name from tb_excluded_packages)
group by package_name, app_id, variant_maker_tag, variant_flag_str, level_flag_str
having qtd_attempts >0 and qtd_attempts < (select count(distinct(hc_attempt)) from consolidated_hc_results)
order by package_name, app_id, variant_maker_tag, hc_attempt;

CREATE VIEW vw_comparison_completed_hc_variants as
select * from comparison_iteration a
where exists (select 1 from vw_completed_hc_variants b where a.package_name=b.package_name and a.app_id=b.app_id)
and package_name not in (select package_name from tb_excluded_packages);

CREATE VIEW tmp_vw_healthy_compatible_variants as
select package_name, app_id, features_str, levels_str, maker_tag, original, new_ui_set, new_exception_sites_set, split_count, count(*) as qtd_zero_score
from vw_comparison_completed_hc_variants
where package_name not in (select package_name from tb_excluded_packages)
and ui_score*1.0=0.0 and exception_sites_score*1.0=0.0
group by package_name, app_id, features_str, levels_str, maker_tag, original, new_ui_set, new_exception_sites_set, split_count
having qtd_zero_score >= (select count(distinct(hc_attempt)) from consolidated_hc_results);

CREATE VIEW vw_comparison_not_completed_hc_variants as
select * from comparison_iteration a
where exists (select 1 from vw_incomplete_hc_variants b where a.package_name=b.package_name and a.app_id=b.app_id)
and package_name not in (select package_name from tb_excluded_packages);

CREATE VIEW tmp_vw_healthy_incompatible_variants as
select package_name, app_id, features_str, levels_str, maker_tag, original, new_ui_set, new_exception_sites_set, split_count, count(*) as qtd_zero_score
from vw_comparison_not_completed_hc_variants
where package_name not in (select package_name from tb_excluded_packages)
group by package_name, app_id, features_str, levels_str, maker_tag, original, new_ui_set, new_exception_sites_set, split_count;

create view vw_healthy_compatible_variants as
select distinct package_name, app_id, features_str, levels_str, maker_tag, original
from tmp_vw_healthy_compatible_variants
where package_name not in (select package_name from tb_excluded_packages);

create view vw_healthy_incompatible_variants as
select distinct package_name, app_id, features_str, levels_str, maker_tag, original
from tmp_vw_healthy_incompatible_variants;

create view vw_faulty_variants as
select * from comparison_expected_variants a where original='False'
and not exists (select 1 from vw_healthy_compatible_variants b where b.package_name=a.package_name and b.app_id=a.app_id)
and not exists (select 1 from vw_healthy_incompatible_variants b where b.package_name=a.package_name and b.app_id=a.app_id)
and package_name not in (select package_name from tb_excluded_packages);

create view vw_healthy_compatible_apps as
select distinct package_name from vw_healthy_compatible_variants
where package_name not in (select package_name from tb_excluded_packages);

create view vw_health_incompatible_apps as
select DISTINCT package_name from vw_healthy_incompatible_variants
where package_name not in (select package_name from vw_healthy_compatible_apps)
and package_name not in (select package_name from tb_excluded_packages);

create view vw_faulty_apps as
select DISTINCT package_name from vw_faulty_variants
where package_name not in (select package_name from vw_healthy_compatible_apps)
and package_name not in (select package_name from vw_health_incompatible_apps)
and package_name not in (select package_name from tb_excluded_packages);

create view vw_split_apps as
select DISTINCT package_name from comparison_expected_variants where split_count*1.0>0 and original='True'
and package_name not in (select package_name from tb_excluded_packages);

create view vw_statistics_healthy_compatible_variants as
select features_str, maker_tag, count(DISTINCT(package_name)) as qtd
from vw_healthy_compatible_variants
where package_name not in (select package_name from tb_excluded_packages)
GROUP by features_str, maker_tag;

create view vw_statistics_healthy_incompatible_variants as
select features_str, maker_tag, count(DISTINCT(package_name)) as qtd
from vw_healthy_incompatible_variants
where package_name not in (select package_name from tb_excluded_packages)
GROUP by features_str, maker_tag;

create view vw_statistics_faulty_variants as
select features_str, maker_tag, count(DISTINCT(package_name)) as qtd
from vw_faulty_variants
where package_name not in (select package_name from tb_excluded_packages)
GROUP by features_str, maker_tag;

create view vw_statistics_splits_healthy_compatible_variants as
select features_str, maker_tag, count(DISTINCT(package_name)) as qtd
from vw_healthy_compatible_variants
where package_name in (SELECT package_name from vw_split_apps)
and package_name not in (select package_name from tb_excluded_packages)
GROUP by features_str, maker_tag;

create view vw_statistics_splits_healthy_incompatible_variants as
select features_str, maker_tag, count(DISTINCT(package_name)) as qtd
from vw_healthy_incompatible_variants
where package_name in (SELECT package_name from vw_split_apps)
and package_name not in (select package_name from tb_excluded_packages)
GROUP by features_str, maker_tag;

create view vw_statistics_splits_faulty_variants as
select features_str, maker_tag, count(DISTINCT(package_name)) as qtd
from vw_faulty_variants
where package_name in (SELECT package_name from vw_split_apps)
and package_name not in (select package_name from tb_excluded_packages)
GROUP by features_str, maker_tag;


CREATE VIEW vw_possible_emulator_bugs as
select * from tmp_vw_healthy_incompatible_variants where qtd_zero_score>1;

CREATE VIEW vw_variants_with_catenated_ui_and_esites as
select package_name, app_id, features_str, maker_tag, 
group_concat(new_exception_sites_set, ';') as catenated_exception_sites, 
group_concat(new_ui_set) as catenated_ui_set
from comparison_iteration a
where package_name not in (select package_name from tb_excluded_packages)
group by package_name, app_id, features_str, maker_tag;

create view vw_healthy_compatible_variants_ui_and_esites as
select * from vw_variants_with_catenated_ui_and_esites a
where exists (select 1 from vw_healthy_compatible_variants b where a.package_name=b.package_name and a.app_id=b.app_id)
and package_name not in (select package_name from tb_excluded_packages);

create view vw_healthy_incompatible_variants_ui_and_esites as
select * from vw_variants_with_catenated_ui_and_esites a
where exists (select 1 from vw_healthy_incompatible_variants b where a.package_name=b.package_name and a.app_id=b.app_id)
and package_name not in (select package_name from tb_excluded_packages);

create view vw_faulty_variants_ui_and_esites as
select * from vw_variants_with_catenated_ui_and_esites a
where exists (select 1 from vw_healthy_incompatible_variants b where a.package_name=b.package_name and a.app_id=b.app_id)
and package_name not in (select package_name from tb_excluded_packages);


CREATE VIEW vw_single_split_apps as
select DISTINCT package_name from comparison_expected_variants where split_count*1.0=0 and original='True'
and package_name not in (select package_name from tb_excluded_packages);

CREATE VIEW vw_statistics_single_split_faulty_variants as
select features_str, maker_tag, count(DISTINCT(package_name)) as qtd
from vw_faulty_variants
where package_name in (SELECT package_name from vw_single_split_apps)
and package_name not in (select package_name from tb_excluded_packages)
GROUP by features_str, maker_tag;


CREATE VIEW vw_statistics_single_split_healthy_compatible_variants as
select features_str, maker_tag, count(DISTINCT(package_name)) as qtd
from vw_healthy_compatible_variants
where package_name in (SELECT package_name from vw_single_split_apps)
and package_name not in (select package_name from tb_excluded_packages)
GROUP by features_str, maker_tag;

CREATE VIEW vw_statistics_single_split_healthy_incompatible_variants as
select features_str, maker_tag, count(DISTINCT(package_name)) as qtd
from vw_healthy_incompatible_variants
where package_name in (SELECT package_name from vw_single_split_apps)
and package_name not in (select package_name from tb_excluded_packages)
GROUP by features_str, maker_tag;

CREATE VIEW vw_single_split_variants as
select DISTINCT features_str, maker_tag, count(*) from comparison_expected_variants where split_count*1.0=0 and original='False'
and package_name not in (select package_name from tb_excluded_packages)
group by features_str, maker_tag;


create view vw_faulty_analytics as
select features_str, maker_tag, package_name as qtd
from vw_faulty_variants
where package_name not in (select package_name from tb_excluded_packages);


create table tb_drop_view as
SELECT 'drop view '||name||';' drop_cmd FROM sqlite_master WHERE type = 'view';










