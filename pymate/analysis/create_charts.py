import os
from pymate.analysis.sqlite_helper import execute_query
from pymate.analysis.charts_utils import plot_stacked_bar_chart, plot_line_chart, combine_svgs_side_by_side


def main():
    base_logs_dir = "H:\\InstruMate\\InstrumateAnalysis\\baseline\\"
    saved_db = os.path.join(base_logs_dir, "main.db")
    vw_stacked_bar_exception_sites_iterations = execute_query(saved_db, "select iteration, total_prev, total_new_pct from vw_stacked_bar_exception_sites_iterations")
    plot_stacked_bar_chart(vw_stacked_bar_exception_sites_iterations, "Exception-Sites", base_logs_dir, "vw_stacked_bar_exception_sites_iterations.png")

    vw_stacked_bar_exceptions_iterations = execute_query(saved_db,
                                                              "select iteration, total_prev, total_new_pct from vw_stacked_bar_exceptions_iterations")
    plot_stacked_bar_chart(vw_stacked_bar_exceptions_iterations, "Exceptions", base_logs_dir,
                           "vw_stacked_bar_exceptions_iterations.png")

    vw_stacked_bar_view_iterations = execute_query(saved_db,
                                                         "select iteration, total_prev, total_new_pct from vw_stacked_bar_view_iterations")
    plot_stacked_bar_chart(vw_stacked_bar_view_iterations, "Views", base_logs_dir,
                           "vw_stacked_bar_view_iterations.png")

    packages_with_discovered_elements_tmp = execute_query(saved_db,
                                                f"select category, iteration, packages_with_new_items from vw_discovery_per_package_per_iteration ")
    packages_with_discovered_elements = [[item[0], int(item[1]), int(item[2])] for item in packages_with_discovered_elements_tmp]
    plot_line_chart(packages_with_discovered_elements, base_folder=base_logs_dir,
                    file_name=f"packages_with_discovered_elements", title=f"packages_with_discovered_elements")

    packages_with_discovered_elements_tmp = execute_query(saved_db,
                                                          f"select category, iteration, (select count(DISTINCT(package_name)) from hc_iteration_views) - packages_with_new_items as packages_hit from vw_discovery_per_package_per_iteration ")
    packages_with_discovered_elements = [[item[0], int(item[1]), int(item[2])] for item in
                                         packages_with_discovered_elements_tmp]
    plot_line_chart(packages_with_discovered_elements, base_folder=base_logs_dir,
                    file_name=f"packages_not_with_discovered_elements", title=f"packages_not_with_discovered_elements")

    query_line_chart_discovery = """select * from (
                            SELECT "Exception-Sites seen before" as category, iteration, total_prev from vw_stacked_bar_exception_sites_iterations
                            union ALL
                            SELECT "Exception-Sites discovered" as category, iteration, total_new from vw_stacked_bar_exception_sites_iterations
                            )
                            order by category, iteration"""
    line_chart_discovery_exception_sites_tmp = execute_query(saved_db, query_line_chart_discovery)
    line_chart_discovery_exception_sites = [[item[0], int(item[1]), int(item[2])] for item in line_chart_discovery_exception_sites_tmp]
    plot_line_chart(line_chart_discovery_exception_sites, base_folder=base_logs_dir,
                    file_name=f"line_chart_discovery_exception_sites", title=f"Discovered Exception-sites")

    query_line_chart_discovery = """select * from (
                                SELECT "UI-components seen before" as category, iteration, total_prev from vw_stacked_bar_view_iterations
                                union ALL
                                SELECT "UI-components discovered" as category, iteration, total_new from vw_stacked_bar_view_iterations
                                )
                                order by category, iteration"""
    line_chart_discovery_views_tmp = execute_query(saved_db, query_line_chart_discovery)
    line_chart_discovery_views = [[item[0], int(item[1]), int(item[2])] for item in
                                            line_chart_discovery_views_tmp]
    plot_line_chart(line_chart_discovery_views, base_folder=base_logs_dir,
                    file_name=f"line_chart_discovery_views",
                    title=f"Discovered UI-Elements")
    score_views_tmp = execute_query(saved_db,
                                    f"select package_name, iteration, score from hc_iteration_views order by package_name asc, CAST(iteration AS INTEGER) asc")
    summary_view_scores = [[item[0], int(item[1]), float(item[2])] for item in score_views_tmp]
    plot_line_chart(summary_view_scores, base_folder=base_logs_dir, file_name=f"summary_view_scores",
                    no_label=True,
                    title=f"View Items")


    summary_exception_scores_tmp = execute_query(saved_db,
                                                 f"select package_name, iteration, score from hc_iteration_exceptions order by package_name asc, CAST(iteration AS INTEGER) asc")
    summary_exception_scores = [[item[0], int(item[1]), float(item[2])] for item in summary_exception_scores_tmp]
    plot_line_chart(summary_exception_scores, base_folder=base_logs_dir,
                    file_name=f"summary_exception_score",
                    no_label=True,
                    title=f"Exceptions Items")

    summary_exception_sites_scores_tmp = execute_query(saved_db,
                                                       f"select package_name, iteration, score from hc_iteration_exception_sites order by package_name asc, CAST(iteration AS INTEGER) asc")
    summary_exception_sites_scores = [[item[0], int(item[1]), float(item[2])] for item in
                                      summary_exception_sites_scores_tmp]
    plot_line_chart(summary_exception_sites_scores, base_folder=base_logs_dir,
                    file_name=f"summary_exception_sites_scores",
                    no_label=True,
                    title=f"Exception Sites")

    # combine_svgs_side_by_side(os.path.join(base_logs_dir, "line_chart_discovery_views.svg"), os.path.join(base_logs_dir, "line_chart_discovery_exception_sites.svg"),
    #                          os.path.join(base_logs_dir, "discovery-exception-sites-and-views.svg"))


if __name__ == "__main__":
    main()
