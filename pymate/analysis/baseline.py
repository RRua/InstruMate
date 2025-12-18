import os
from pymate.utils import fs_utils, utils
from pathlib import Path
from pymate.csv_logger.SQLiteDBFastLogger import SQLiteDBFastLogger
from pymate.device_observer.logcat_observer import LogcatState
from pymate.analysis.sqlite_helper import execute_query


class HealthCheckIteration:
    def __init__(self, package_name, ui_actions, exceptions, logcat_stdout, logcat_stderr, exclude_android_sites=True,
                 exclude_common_exceptions=False):
        self.source_dir = None
        self.app_id = None
        self.maker_tag = None
        self.new_views = None
        self.new_views_score = None
        self.new_exceptions = None
        self.new_exceptions_score = None
        self.new_exception_sites = None
        self.new_exception_sites_score = None
        self.ui_actions_previous_set = set()
        self.exceptions_previous_set = set()
        self.exceptions_sites_previous_set = set()

        self.package_name = package_name
        self.ui_actions = ui_actions
        self.ui_actions_set = set()
        self.exceptions = exceptions
        self.exceptions_set = set()
        self.exceptions_and_sites = set()
        self.selected_view_classes = ["android.widget.Button", "android.widget.TextView", "android.widget.EditText",
                                      "android.widget.ImageButton", "android.widget.CheckBox",
                                      "android.widget.RadioButton", "android.widget.RadioGroup"]
        if exclude_android_sites:
            self.excluded_method_origins = ["com.google.", "com.android.", "android.os.", "libcore.io.", "java.",
                                            "android.", "androidx.", "com.facebook.ads.", "okhttp3.",
                                            "com.facebook.react.", "dalvik.system.", "aout.a", "Proxy.registerReceiverWithFeature"]
        else:
            self.excluded_method_origins = []
        if exclude_common_exceptions:
            self.excluded_exceptions = ["java.net.ConnectException",
                                        "java.net.SocketTimeoutException",
                                        "java.net.UnknownHostException",
                                        "java.net.SocketException",
                                        "java.net.UnknownServiceException",
                                        "android.os.DeadObjectException",
                                        "android.os.Parcel.readException",
                                        "android.os.Parcel.createException",
                                        "java.net.SocketTimeoutException",
                                        "3.newTimeoutException",
                                        "java.util.concurrent.TimeoutException",
                                        "java.io.EOFException",
                                        "org.json.JSONException",
                                        "org.json.JSONTokener.syntaxError",
                                        "com.google.gson.JsonSyntaxException",
                                        "kotlinx.serialization.json.internal.JsonExceptionsKt.JsonDecodingException",
                                        "com.google.gson.stream.MalformedJsonException",
                                        "com.google.gson.stream.JsonReader.unexpectedTokenError",
                                        "com.google.gson.stream.JsonReader.syntaxError",
                                        "javax.net.ssl.SSLException",
                                        "c.newTimeoutException",
                                        "com.amazonaws.mobileconnectors.remoteconfiguration.exceptions.NetworkException"

                                        ]
        else:
            self.excluded_exceptions = []
        self._parse_ui_actions()
        self._parse_exceptions()
        logcat_state = LogcatState(logcat_stdout, logcat_stderr)
        if "exception_origins" in logcat_state.state_dict:
            self.exception_origins = logcat_state.state_dict["exception_origins"]
        self._filter_exceptions_sites()

    def _is_excluded_exception(self, exception_name):
        is_excluded = False
        for excluded in self.excluded_exceptions:
            if exception_name == excluded:
                is_excluded = True
                break
        return is_excluded

    def _is_excluded_exception_site(self, exception_site):
        is_excluded = False
        for excluded_origin in self.excluded_method_origins:
            if exception_site.startswith(excluded_origin):
                is_excluded = True
                break
        return is_excluded

    def _filter_exceptions_sites(self):
        exceptions_and_sites = set()
        for item in self.exception_origins:
            if item["index"] == 0 or item["index"] == '0':
                is_excluded = self._is_excluded_exception_site(item["method_signature"])
                if not is_excluded:
                    is_excluded = self._is_excluded_exception(item["exception_name"])
                if not is_excluded:
                    exceptions_and_sites.add((item["exception_name"], item["method_signature"]))
        self.exceptions_and_sites = set(exceptions_and_sites)

    def _parse_ui_actions(self, append_labels=False, count_classes=True):
        strings = []
        cls_counter = {}
        for ui_action in self.ui_actions:
            cls = ui_action['cls']
            cls_counter_value = 1
            if cls not in cls_counter:
                cls_counter[cls] = cls_counter_value
            else:
                cls_counter_value = cls_counter[cls] + 1
                cls_counter[cls] = cls_counter_value

            if cls in self.selected_view_classes:
                if append_labels:
                    label = ui_action['label']
                else:
                    label = '<>'
                act_type = ui_action['type']
                if count_classes:
                    text = f"{cls}[{label}]:{act_type}:{cls_counter_value}"
                else:
                    text = f"{cls}[{label}]:{act_type}"
                if text not in strings:
                    strings.append(text)
        ordered_set = set(sorted(strings))
        self.ui_actions_set = ordered_set

    def _parse_exceptions(self):
        strings = []
        for exception in self.exceptions:
            text = exception['captured_exception_name']
            if not self._is_excluded_exception(text):
                if text not in strings:
                    strings.append(text)
        ordered_set = set(sorted(strings))
        self.exceptions_set = ordered_set

    def is_equal(self, other):
        return self.is_view_equal() and self.have_same_exceptions() and self.have_same_exception_sites()

    def is_view_equal(self, other):
        if self.package_name != other.package_name:
            raise RuntimeError(f"Cant compare different packages {self.package_name} with {other.package_name}")
        return self.ui_actions_set == other.ui_actions_set

    def have_same_exceptions(self, other):
        if self.package_name != other.package_name:
            raise RuntimeError(f"Cant compare different packages {self.package_name} with {other.package_name}")
        return self.exceptions_set == other.exceptions_set

    def have_same_exception_sites(self, other):
        if self.package_name != other.package_name:
            raise RuntimeError(f"Cant compare different packages {self.package_name} with {other.package_name}")
        return self.exceptions_and_sites == other.exceptions_and_sites

    def copy_to(self, dest, create_app_dir=True, named_with_app_id=False, named_with_maker_tag=False):
        if named_with_app_id:
            app_dir = f"{self.package_name}-{self.app_id}"
        else:
            app_dir = f"{self.package_name}"
        if named_with_maker_tag:
            if self.maker_tag is not None and len(self.maker_tag) > 0:
                app_dir = f"{app_dir}-{self.maker_tag}"
        dest_dir = os.path.join(dest, app_dir)
        if not os.path.exists(dest_dir):
            if create_app_dir:
                os.makedirs(dest_dir)
            else:
                raise RuntimeError(f"Dir does not exists {dest_dir}")
        if os.path.exists(self.source_dir):
            fs_utils.merge_dirs(self.source_dir, dest_dir)
        else:
            print(f"MISSING SOURCE DIR: {self.source_dir}")


class HealthCheck:
    def __init__(self, package_name, app_id=None, ui_actions=None, exceptions_and_sites=None, exceptions=None,
                 init_exceptions_set=False):
        self.iterations = []
        self.package_name = package_name
        self.app_id = app_id
        if ui_actions is None:
            self.ui_actions = set()
        else:
            self.ui_actions = ui_actions
        if exceptions is None:
            self.exceptions = set()
        else:
            self.exceptions = exceptions
        if exceptions_and_sites is None:
            self.exceptions_and_sites = set()
        else:
            self.exceptions_and_sites = exceptions_and_sites

        self.init_exceptions_set = {'com.google.firebase.installations.FirebaseInstallationsException',
                                    'java.util.concurrent.ExecutionException', 'java.io.IOException',
                                    'java.lang.IllegalStateException', 'java.lang.IllegalArgumentException'}
        if init_exceptions_set:
            self.exceptions.update(self.init_exceptions_set)

    def append_iteration(self, iteration: HealthCheckIteration):
        self.iterations.append(iteration)
        self.ui_actions = iteration.ui_actions_set.union(self.ui_actions)
        self.exceptions = iteration.exceptions_set.union(self.exceptions)
        self.exceptions_and_sites = iteration.exceptions_and_sites.union(self.exceptions_and_sites)

    def calc_view_score(self, iteration: HealthCheckIteration):
        set1 = self.ui_actions
        set2 = iteration.ui_actions_set
        set_union = set1.union(set2)
        set_diff = set2 - set1
        if len(set_union) > 0:
            score = len(set_diff) * 1.0 / len(set_union)
        else:
            score = 0.0
        iteration.new_views = set_diff
        iteration.new_views_score = score
        iteration.ui_actions_previous_set = set1
        return score

    def calc_exceptions_score(self, iteration: HealthCheckIteration):
        set1 = self.exceptions
        set2 = iteration.exceptions_set
        set_union = set1.union(set2)
        set_diff = set2 - set1
        if len(set_union) > 0:
            score = len(set_diff) * 1.0 / len(set_union)
        else:
            score = 0.0
        iteration.new_exceptions = set_diff
        iteration.new_exceptions_score = score
        iteration.exceptions_previous_set = set1
        return score

    def calc_exception_sites_score(self, iteration: HealthCheckIteration):
        set1 = self.exceptions_and_sites
        set2 = iteration.exceptions_and_sites
        set_union = set1.union(set2)
        set_diff = set2 - set1
        if len(set_union) > 0:
            score = len(set_diff) * 1.0 / len(set_union)
        else:
            score = 0.0
        iteration.new_exception_sites = set_diff
        iteration.new_exception_sites_score = score
        iteration.exceptions_sites_previous_set = set1
        return score

    def copy_to(self, dest_dir):
        for item in self.iterations:
            item.copy_to(dest_dir)


def _find_health_check_iterations(package_name, database, search_only_success_apps=True, exclude_android_sites=True):
    basedir = Path(database).parent
    if search_only_success_apps:
        query_app_id = f"select distinct app_id from vw_all_success_apps where package_name = '{package_name}'"
        result_app_id = [item[0] for item in execute_query(database, query_app_id)]
    else:
        query_app_id = f"select DISTINCT app_id from instrumate_checker_commands where package_name='{package_name}'"
        result_app_id = [item[0] for item in execute_query(database, query_app_id)]
    hc_items = []
    if len(result_app_id) > 0:
        for app_id in result_app_id:
            query_ui_actions = f"select * from view_state_action_units where package_name = '{package_name}' " \
                               f"and app_id = '{app_id}'"
            query_exceptions = f"select * from app_exceptions where package_name = '{package_name}' " \
                               f"and app_id = '{app_id}'"
            ui_actions = execute_query(database, query_ui_actions, format='dictionary')
            exceptions = execute_query(database, query_exceptions, format='dictionary')
            query_app_info = f"select DISTINCT package_name, app_version, app_id, is_variant, variant_maker_tag, " \
                             f"variant_flag, variant_flag_str, level_flag, level_flag_str from " \
                             f"instrumate_checker_commands where " \
                             f"package_name='{package_name}' and app_id='{app_id}'"
            app_info_dict = execute_query(database, query_app_info, format='dictionary')[0]
            health_check_folder = os.path.join(basedir, f"{package_name}-{app_id}")
            logcat_dir = os.path.join(health_check_folder, "logcat_observer")
            logcat_stdout = []
            logcat_stderr = []
            if os.path.exists(logcat_dir):
                json_files = fs_utils.list_files(directory_path=logcat_dir, extension="json")
                for json_file in json_files:
                    json_obj = utils.read_json_as_dict(json_file)
                    logcat_stdout.extend(json_obj["stdout"])
                    logcat_stderr.extend(json_obj["stderr"])
            # failed apps don't go to the database (bug)
            if not search_only_success_apps:
                if len(ui_actions) == 0:
                    ui_actions = []
                    view_observer_dir = os.path.join(health_check_folder, "view_observer")
                    if os.path.exists(view_observer_dir):
                        json_files = fs_utils.list_files(directory_path=view_observer_dir, extension="json")
                        for json_file in json_files:
                            json_obj = utils.read_json_as_dict(json_file)
                            view_signature = json_obj["signature"]
                            for item_act_unit_signature in json_obj["action_units"]:
                                item_act_unit = json_obj["action_units"][item_act_unit_signature]
                                ui_actions.append({
                                    "package_name": app_info_dict["package_name"],
                                    "app_version": app_info_dict["app_version"],
                                    "app_id": app_info_dict["app_id"],
                                    "is_variant": app_info_dict["is_variant"],
                                    "variant_maker_tag": app_info_dict["variant_maker_tag"],
                                    "variant_flag": app_info_dict["variant_flag"],
                                    "variant_flag_str": app_info_dict["variant_flag_str"],
                                    "level_flag": app_info_dict["level_flag"],
                                    "level_flag_str": app_info_dict["level_flag_str"],
                                    "view_signature": view_signature,
                                    "view_id": item_act_unit["view_id"],
                                    "cls": item_act_unit["cls"],
                                    "pkg": item_act_unit["pkg"],
                                    "label": item_act_unit["label"],
                                    "type": item_act_unit["type"]
                                })
                if len(exceptions) == 0:
                    exceptions = []
                    if os.path.exists(logcat_dir):
                        json_files = fs_utils.list_files(directory_path=logcat_dir, extension="json")
                        for json_file in json_files:
                            json_obj = utils.read_json_as_dict(json_file)
                            for item_exception in json_obj["exceptions"]:
                                exceptions.append({
                                    "package_name": app_info_dict["package_name"],
                                    "app_version": app_info_dict["app_version"],
                                    "app_id": app_info_dict["app_id"],
                                    "is_variant": app_info_dict["is_variant"],
                                    "variant_maker_tag": app_info_dict["variant_maker_tag"],
                                    "variant_flag": app_info_dict["variant_flag"],
                                    "variant_flag_str": app_info_dict["variant_flag_str"],
                                    "level_flag": app_info_dict["level_flag"],
                                    "level_flag_str": app_info_dict["level_flag_str"],
                                    "captured_exception_name": item_exception
                                })

            hc_item = HealthCheckIteration(package_name, ui_actions, exceptions, logcat_stdout, logcat_stderr,
                                           exclude_android_sites=exclude_android_sites)
            hc_item.app_id = app_id
            hc_item.maker_tag = app_info_dict["variant_maker_tag"]
            hc_item_path = os.path.join(basedir, f"{package_name}-{app_id}")
            if not os.path.exists(hc_item_path):
                print(f"Missing path {hc_item_path} - database {database}")
            hc_item.source_dir = hc_item_path
            hc_items.append(hc_item)
    else:
        print(f"Missing app id for {package_name} - database {database}")
    return hc_items


def _calc_baseline(databases_to_check, dataset_packages, output_dir, copy_to_output=False):
    apps_health_check = {}
    dest_dir = os.path.join(output_dir, "consolidated")
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    processed_apps = 0
    for selected_app in dataset_packages:
        app_health_check = HealthCheck(package_name=selected_app)
        i = 0
        for database in databases_to_check:
            hc_items = _find_health_check_iterations(selected_app, database)
            if len(hc_items) > 1:
                raise RuntimeError('To baseline creation, only one app id must be present')
            hc_item = hc_items[0]
            view_score = app_health_check.calc_view_score(hc_item)
            exceptions_score = app_health_check.calc_exceptions_score(hc_item)
            exception_sites_score = app_health_check.calc_exception_sites_score(hc_item)
            if i > len(databases_to_check) - 2:
                if view_score > 0.0 or exceptions_score > 0.0 or exception_sites_score > 0.0:
                    print(f"Iteration {i} -----------------------")
                if view_score > 0.0:
                    print(
                        f"[view] Package {selected_app}; view score: {view_score}; exceptions score: {exceptions_score}; exception sites score: {exception_sites_score}")
                if exceptions_score > 0.0:
                    print(
                        f"[exceptions] Package {selected_app}; view score: {view_score}; exceptions score: {exceptions_score}; exception sites score: {exception_sites_score}")
                if exception_sites_score > 0.0:
                    print(
                        f"[sites] Package {selected_app}; view score: {view_score}; exceptions score: {exceptions_score}; exception sites score: {exception_sites_score}")
            app_health_check.append_iteration(hc_item)
            if copy_to_output:
                app_health_check.copy_to(dest_dir)
            i = i + 1
        apps_health_check[selected_app] = app_health_check
        print(f"{processed_apps} ", end="")
        processed_apps = processed_apps + 1
    print("----")
    print("Finished apps processing...")
    return apps_health_check


def _save_baseline(baseline: dict, failed_databases: dict, fast_logger: SQLiteDBFastLogger):
    fast_logger.add_logger("hc_iteration_views",
                           ["package_name", "app_id", "iteration", "previous_set", "len_prev_set", "unique_set",
                            "new_items_set", "len_new_set",
                            "score"])
    fast_logger.add_logger("hc_iteration_exceptions",
                           ["package_name", "app_id", "iteration", "previous_set", "len_prev_set", "unique_set",
                            "new_items_set", "len_new_set",
                            "score"])
    fast_logger.add_logger("hc_iteration_exception_sites",
                           ["package_name", "app_id", "iteration", "previous_set", "len_prev_set", "unique_set",
                            "new_items_set", "len_new_set",
                            "score"])
    fast_logger.add_logger("hc_exception_origins",
                           ["package_name", "app_id", "iteration", "exception_name", "method_signature", "detail",
                            "exception_index", "raw_msg"])
    fast_logger.add_logger("hc_exception_sites_with_details",
                           ["package_name", "app_id", "pos", "exception_name", "site"])

    fast_logger.add_logger("hc_failed_databases",
                           ["database_path", "package_name"])

    for package_name in baseline:
        package_hc = baseline[package_name]
        pos = 0
        for iteration in package_hc.iterations:
            fast_logger.log_data("hc_iteration_views",
                                 [package_name, package_hc.app_id, pos, f"{iteration.ui_actions_previous_set}",
                                  len(iteration.ui_actions_previous_set),
                                  f"{iteration.ui_actions_set}",
                                  f"{iteration.new_views}", len(iteration.new_views), iteration.new_views_score])
            pos = pos + 1
        pos = 0
        for iteration in package_hc.iterations:
            fast_logger.log_data("hc_iteration_exceptions",
                                 [package_name, package_hc.app_id, pos, f"{iteration.exceptions_previous_set}",
                                  len(iteration.exceptions_sites_previous_set),
                                  f"{iteration.exceptions_set}",
                                  f"{iteration.new_exceptions}", len(iteration.new_exceptions),
                                  iteration.new_exceptions_score])
            pos = pos + 1
        pos = 0
        for iteration in package_hc.iterations:
            fast_logger.log_data("hc_iteration_exception_sites",
                                 [package_name, package_hc.app_id, pos, f"{iteration.exceptions_sites_previous_set}",
                                  len(iteration.exceptions_sites_previous_set),
                                  f"{iteration.exceptions_and_sites}",
                                  f"{iteration.new_exception_sites}", len(iteration.new_exception_sites),
                                  iteration.new_exception_sites_score])
            pos = pos + 1
        pos = 0
        for iteration in package_hc.iterations:
            for item in iteration.exception_origins:
                exception_name = item["exception_name"]
                method_signature = item["method_signature"]
                detail = item["detail"]
                index = item["index"]
                raw_msg = item["raw_msg"]
                fast_logger.log_data("hc_exception_origins",
                                     [package_name, package_hc.app_id, pos, exception_name, method_signature, detail,
                                      index, raw_msg])
            pos = pos + 1
        for iteration in package_hc.iterations:
            for exception_name, site in iteration.exceptions_and_sites:
                fast_logger.log_data("hc_exception_sites_with_details",
                                     [package_name, package_hc.app_id, pos, exception_name, site])
            pos = pos + 1

    for key_db_path in failed_databases:
        for failed_pkg_name in failed_databases[key_db_path]:
            fast_logger.log_data("hc_failed_databases",
                                 [key_db_path, failed_pkg_name])

    fast_logger.close()
    fast_logger.consolidate_database()
    fast_logger.exec_post_create("./input/config/baseline_db.sql")


def create_baseline_from_iterations(databases_to_check, dataset_packages, output_dir, failed_databases,
                                    copy_to_output=False):
    baseline = _calc_baseline(databases_to_check, dataset_packages, output_dir, copy_to_output)
    fast_logger = SQLiteDBFastLogger(basedir=output_dir)
    _save_baseline(baseline, failed_databases, fast_logger)


def compare_baseline_with_iterations(baseline, databases_to_check, dataset_packages, output_dir, copy_to_output=False):
    scored_items_dir = os.path.join(output_dir, "scored_items")
    not_scored_items_dir = os.path.join(output_dir, "not_scored_items")
    hc_iterations = []
    if not os.path.exists(scored_items_dir):
        os.makedirs(scored_items_dir)
    if not os.path.exists(not_scored_items_dir):
        os.makedirs(not_scored_items_dir)

    for selected_app in dataset_packages:
        app_baseline = baseline[selected_app]
        for database in databases_to_check:
            hc_items = _find_health_check_iterations(selected_app, database, search_only_success_apps=False,
                                                     exclude_android_sites=True)
            for hc_item in hc_items:
                hc_iterations.append(hc_item)
                view_score = app_baseline.calc_view_score(hc_item)
                exceptions_score = app_baseline.calc_exceptions_score(hc_item)
                exception_sites_score = app_baseline.calc_exception_sites_score(hc_item)
                if copy_to_output:
                    dest_dir = not_scored_items_dir
                    if view_score > 0.0 or exceptions_score > 0.0 or exception_sites_score > 0.0:
                        dest_dir = scored_items_dir
                    hc_item.copy_to(dest_dir, named_with_maker_tag=True)
    return hc_iterations


def _find_app_info(app_info_db, package_name, app_id):
    query_ui_actions = f"select app_id, package_name, original, features_flag, features_str, level_flag, levels_str, maker_tag, splits " \
                       f"from app_info where package_name = '{package_name}' and app_id='{app_id}'"
    app_info = execute_query(app_info_db, query_ui_actions, format='dictionary')
    if len(app_info) != 1:
        raise RuntimeError(f"App {package_name} with ID {app_id} has no consistent information - len {len(app_info)}")
    return app_info[0]


def _find_expected_variants(app_info_db):
    query_ui_actions = f"select app_id, package_name, original, features_flag, features_str, level_flag, levels_str, maker_tag, splits " \
                       f"from app_info"
    variants_info = execute_query(app_info_db, query_ui_actions, format='dictionary')
    return variants_info


def count_splits(s):
    if s is None:
        return 0
    if len(s) == 0:
        return 0
    return len(s.split(','))


def save_comparison_iterations(app_info_db, iterations, output_dir, expected_packages, databases):
    fast_logger = SQLiteDBFastLogger(basedir=output_dir)
    fast_logger.add_logger("comparison_expected_packages",
                           ["package_name"])

    for package in expected_packages:
        fast_logger.log_data("comparison_expected_packages", [package])

    fast_logger.add_logger("comparison_expected_variants",
                           ["package_name", "app_id", "features_flag", "features_str", "level_flag", "levels_str",
                            "maker_tag", "original", "split_count"])

    expected_variants = _find_expected_variants(app_info_db)
    for expected_variant in expected_variants:
        package_name = expected_variant["package_name"]
        app_id = expected_variant["app_id"]
        features_flag = expected_variant["features_flag"]
        features_str = expected_variant["features_str"]
        level_flag = expected_variant["level_flag"]
        levels_str = expected_variant["levels_str"]
        maker_tag = expected_variant["maker_tag"]
        original = expected_variant["original"]
        app_splits = count_splits(expected_variant["splits"])
        fast_logger.log_data("comparison_expected_variants",
                             [package_name, app_id, features_flag, features_str, level_flag, levels_str,
                              maker_tag, original, app_splits])

    fast_logger.add_logger("comparison_iteration",
                           ["package_name", "app_id", "features_flag", "features_str", "level_flag", "levels_str",
                            "maker_tag", "original", "split_count", "new_ui_set", "len_new_ui_set",
                            "new_exceptions_set",
                            "len_new_exceptions_set",
                            "new_exception_sites_set", "len_new_exception_sites_set", "ui_score", "exceptions_score",
                            "exception_sites_score"])
    for iteration in iterations:
        iteration: HealthCheckIteration
        app_info = _find_app_info(app_info_db, iteration.package_name, iteration.app_id)
        package_name = iteration.package_name
        app_id = iteration.app_id
        features_flag = app_info["features_flag"]
        features_str = app_info["features_str"]
        level_flag = app_info["level_flag"]
        levels_str = app_info["levels_str"]
        maker_tag = app_info["maker_tag"]
        original = app_info["original"]
        app_splits = count_splits(app_info["splits"])
        new_ui_set = iteration.new_views
        len_new_ui_set = len(iteration.new_views)
        new_exceptions_set = iteration.new_exceptions
        len_new_exceptions_set = len(iteration.new_exceptions)
        new_exception_sites_set = iteration.new_exception_sites
        len_new_exception_sites_set = len(iteration.new_exception_sites)
        ui_score = iteration.new_views_score
        exceptions_score = iteration.new_exceptions_score
        exception_sites_score = iteration.new_exception_sites_score
        fast_logger.log_data("comparison_iteration",
                             [package_name, app_id, features_flag, features_str, level_flag, levels_str,
                              maker_tag, original, app_splits, new_ui_set, len_new_ui_set, new_exceptions_set,
                              len_new_exceptions_set,
                              new_exception_sites_set, len_new_exception_sites_set, ui_score,
                              exceptions_score,
                              exception_sites_score])

    consolidated_hc_results = []
    for index, database in enumerate(databases):
        query_result_success = "select * from instrumate_checker_result"
        result_success = execute_query(database, query_result_success, format='dictionary')
        for item in result_success:
            item["hc_attempt"] = index
            item["database"] = database
            consolidated_hc_results.append(item)
    fast_logger.add_logger("consolidated_hc_results", [key for key in consolidated_hc_results[0]])
    for item in consolidated_hc_results:
        fast_logger.log_data("consolidated_hc_results", [item[key] for key in item])

    consolidated_all_success_apps = []
    for index, database in enumerate(databases):
        query_result_success = "select * from vw_all_success_apps"
        result_success = execute_query(database, query_result_success, format='dictionary')
        for item in result_success:
            item["hc_attempt"] = index
            item["database"] = database
            consolidated_all_success_apps.append(item)
    fast_logger.add_logger("consolidated_all_success_apps", [key for key in consolidated_all_success_apps[0]])
    for item in consolidated_all_success_apps:
        fast_logger.log_data("consolidated_all_success_apps", [item[key] for key in item])

    fast_logger.close()
    fast_logger.consolidate_database()
    fast_logger.exec_post_create("./input/config/comparison_db.sql")


def load_health_check_from_baseline_db(baseline_db, package_names, iteration_number):
    baseline = {}
    for package_name in package_names:
        query_ui_actions = f"select previous_set from hc_iteration_views where package_name = '{package_name}' and iteration='{iteration_number}'"
        ui_actions = execute_query(baseline_db, query_ui_actions)[0][0]
        query_ui_exceptions = f"select previous_set from hc_iteration_exceptions where package_name = '{package_name}' and iteration='{iteration_number}'"
        exceptions = execute_query(baseline_db, query_ui_exceptions)[0][0]
        query_ui_exception_sites = f"select previous_set from hc_iteration_exception_sites where package_name = '{package_name}' and iteration='{iteration_number}'"
        exception_sites = execute_query(baseline_db, query_ui_exception_sites)[0][0]
        hc = HealthCheck(package_name=package_name, ui_actions=eval(ui_actions),
                         exceptions_and_sites=eval(exception_sites), exceptions=eval(exceptions),
                         init_exceptions_set=False)
        baseline[package_name] = hc
    return baseline


def find_databases_with_tags(tags, input_dir, discard_db_with_failures=True, forced_apps_exclusion=[]):
    iteration_databases = {}
    all_success_apps = set()
    failed_databases = {}
    for tag in tags:
        tag_name = tag[0]
        tag_min = tag[1]
        tag_max = tag[2]
        for i in range(tag_min, tag_max):
            baseline_db_i = os.path.join(input_dir, f".\\{tag_name}-{i}\\instrumate_checker_log.db")
            if not os.path.exists(baseline_db_i):
                print(f"Path does not exists {baseline_db_i}. Skipping")
                continue
            iteration_success, iteration_failed = find_success_and_failed_apps_in_database(baseline_db_i)
            if discard_db_with_failures:
                unknown_failures = [item for item in iteration_failed if item not in forced_apps_exclusion]
                if len(unknown_failures):
                    print(f"Database discarded because of failiures: {baseline_db_i}")
                    failed_databases[baseline_db_i] = unknown_failures
                    continue
            if len(all_success_apps) == 0:
                all_success_apps.update(iteration_success)
            else:
                all_success_apps = all_success_apps.intersection(set(iteration_success))
            iteration_databases[f"{tag_name}-{i}"] = {
                "database": baseline_db_i,
                "success_apps": iteration_success,
                "failed_apps": iteration_failed
            }
    return iteration_databases, all_success_apps, failed_databases


def find_success_and_failed_apps_in_database(baseline_db):
    query_success_apps = "select package_name, app_id from vw_all_success_apps"
    success_apps = [item[0] for item in execute_query(baseline_db, query_success_apps)]
    query_failed_apps = "select package_name, app_id from vw_all_failed_apps"
    failed_apps = [item[0] for item in execute_query(baseline_db, query_failed_apps)]
    return success_apps, failed_apps


def find_databases_with_tags(tags, input_dir, discard_db_with_failures=True, forced_apps_exclusion=[]):
    iteration_databases = {}
    all_success_apps = set()
    failed_databases = {}
    for tag in tags:
        tag_name = tag[0]
        tag_min = tag[1]
        tag_max = tag[2]
        for i in range(tag_min, tag_max):
            baseline_db_i = os.path.join(input_dir, f".\\{tag_name}-{i}\\instrumate_checker_log.db")
            if not os.path.exists(baseline_db_i):
                baseline_db_i = os.path.join(input_dir, f".\\{tag_name}-{i}\\unfinished_instrumate_checker.db")
            if not os.path.exists(baseline_db_i):
                print(f"Path does not exists {baseline_db_i}. Skipping")
                continue
            iteration_success, iteration_failed = find_success_and_failed_apps_in_database(baseline_db_i)
            if discard_db_with_failures:
                unknown_failures = [item for item in iteration_failed if item not in forced_apps_exclusion]
                if len(unknown_failures):
                    print(f"Database discarded because of failiures: {baseline_db_i}")
                    failed_databases[baseline_db_i] = unknown_failures
                    continue
            if len(all_success_apps) == 0:
                all_success_apps.update(iteration_success)
            else:
                all_success_apps = all_success_apps.intersection(set(iteration_success))
            iteration_databases[f"{tag_name}-{i}"] = {
                "database": baseline_db_i,
                "success_apps": iteration_success,
                "failed_apps": iteration_failed
            }
    return iteration_databases, all_success_apps, failed_databases
