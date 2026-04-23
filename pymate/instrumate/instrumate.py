import gc
import os
import time
import traceback
import logging
from datetime import datetime
from pymate.common.app import App
from pymate.common.app_variant import AppVariant, create_variant_specifications
from pymate.instrumate.instrumate_log import InstruMateLog
from pymate.instrumate.static_analyzers.AndroguardApkAnalyzer import AndroguardApkAnalyzer
from pymate.instrumate.static_analyzers.AndroguardCallGraphAnalyzer import AndroguardCallGraphAnalyzer
from pymate.instrumate.static_analyzers.AndroguardDEXAnalyzer import AndroguardDEXAnalyzer
from pymate.instrumate.static_analyzers.PossibleModificationsAnalyzer import PossibleModificationsAnalyzer
from pymate.instrumate.static_analyzers.TikaMimeTypeAnalyzer import TikaMimeTypeAnalyzer
from pymate.instrumate.variant_maker import VariantMaker
from pymate.instrumate.variant_makers.GenericApkEditorRepackager import GenericApkEditorRepackager
from pymate.instrumate.variant_makers.GenericZipRepackager import GenericZipRepackager
from pymate.instrumate.variant_makers.GenericApkToolRepackager import GenericApkToolRepackager
from pymate.instrumate.variant_makers.RepackagerByASPECTJWithApkTool import RepackagerByAspectjWithApkTool
from pymate.instrumate.variant_makers.RepackagerByASPECTJWithApkEditor import RepackagerByAspectjWithApkEditor
from pymate.instrumate.variant_makers.RepackagerByAcvTool import RepackagerByAcvTool
from pymate.instrumate.variant_makers.RepackagerByAndrolog import RepackagerByAndrolog
from pymate.instrumate.variant_makers.RepackagerByCOSMO import RepackagerByCOSMO
from pymate.instrumate.variant_makers.RepackagerByDroidfax import RepackagerByDroidfax
from pymate.instrumate.variant_makers.RepackagerByRVAndroid import RepackagerByRVAndroid
from pymate.instrumate.variant_makers.RepackagerByFridaGadgetWithApkTool import RepackagerByFridaGadgetWithApkTool
from pymate.instrumate.variant_makers.RepackagerByFridaGadgetWithApkEditor import RepackagerByFridaGadgetWithApkEditor
from pymate.instrumate.variant_makers.RepackagerByImCoverageWithApkTool import RepackagerByImCoverageWithApkTool
from pymate.instrumate.variant_makers.RepackagerByImCoverageWithApkEditor import RepackagerByImCoverageWithApkEditor
from pymate.utils import fs_utils

STATIC_ANALYZERS = {
    "basic": AndroguardApkAnalyzer(),
    "callgraph": AndroguardCallGraphAnalyzer(),
    "andex": AndroguardDEXAnalyzer(),
    "content": TikaMimeTypeAnalyzer(),
    "content+": TikaMimeTypeAnalyzer(expand_dex=True),
    "content++": TikaMimeTypeAnalyzer(expand_dex=True, expand_native=True),
    "possible_modifications": PossibleModificationsAnalyzer()
}

VARIANT_MAKERS = {
    "zip": [GenericZipRepackager()],
    "apkeditor": [GenericApkEditorRepackager()],
    "apktool": [GenericApkToolRepackager()],
    "acvtool": [RepackagerByAcvTool()],
    "androlog": [RepackagerByAndrolog()],
    "droidfax": [RepackagerByDroidfax()],
    "rvandroid": [RepackagerByRVAndroid()],
    "cosmo": [RepackagerByCOSMO()],
    "aspectj": [RepackagerByAspectjWithApkTool(), RepackagerByAspectjWithApkEditor()],
    "fridagadget": [RepackagerByFridaGadgetWithApkTool(), RepackagerByFridaGadgetWithApkEditor()],
    "imcoverage": [RepackagerByImCoverageWithApkTool(), RepackagerByImCoverageWithApkEditor()]
}


def parse_variant_makers(labels: list):
    variant_makers_tmp = [VARIANT_MAKERS.get(key, []) for key in labels]
    variant_makers = []
    for item in variant_makers_tmp:
        variant_makers.extend(item)
    return variant_makers


DEFAULT_ANALYZERS = ["basic", "content++"]
DEFAULT_MAKERS = ["zip", "apkeditor", "apktool", "androlog", "aspectj", "acvtool", "fridagadget", "imcoverage"]


class InstruMate:
    def __init__(self, config_dir: str = None, tmp_dir: str = None, output_dir: str = None, tools_dir: str = None,
                 original_apps=None,
                 static_analyzers=None, variant_makers=None, append_to_existing=False, jdk8_path=None, jdk_path=None,
                 specs_modify_manifest=False, specs_modify_resources=False, specs_modify_behaviour=False,
                 specs_androlog=True, specs_aspectj=True, specs_acvtool=True, specs_fridagadget=True,
                 specs_imcoverage=True):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.tmp_dir = tmp_dir
        self.output_dir = output_dir
        self.tools_dir = tools_dir
        self.original_apps = original_apps
        self.static_analyzers = static_analyzers
        self.variant_makers = variant_makers
        self.jdk8_path = jdk8_path
        self.jdk17_path = jdk_path
        self.append_to_existing = append_to_existing
        sql_post_config_file = os.path.join(config_dir, 'config', 'instrumate_db.sql')
        self.instrumate_log = InstruMateLog(log_dir=self.output_dir, sql_post_config_file=sql_post_config_file)
        self.specs_modify_manifest = specs_modify_manifest
        self.specs_modify_resources = specs_modify_resources
        self.specs_modify_behaviour = specs_modify_behaviour
        self.specs_androlog = specs_androlog
        self.specs_aspectj = specs_aspectj
        self.specs_acvtool = specs_acvtool
        self.specs_fridagadget = specs_fridagadget
        self.specs_imcoverage = specs_imcoverage
        for variant_maker in self.variant_makers:
            variant_maker.configure(tmp_dir=self.tmp_dir, output_dir=self.output_dir, tools_dir=self.tools_dir,
                                    instrumate_log=self.instrumate_log,
                                    force_overwrite=append_to_existing,
                                    jdk8_path=jdk8_path,
                                    jdk17_path=jdk_path)
        for static_analyzer in self.static_analyzers:
            static_analyzer.configure(tmp_dir=self.tmp_dir, output_dir=self.output_dir, tools_dir=self.tools_dir,
                                      instrumate_log=self.instrumate_log)

    def _is_app_already_analyzed(self, app: App, clean_unfinished_dir=True):
        final_app_dest_dir = self._get_app_output_dir(app)
        if os.path.exists(final_app_dest_dir):
            if app.exists_at_dir(final_app_dest_dir):
                return True
            else:
                if clean_unfinished_dir:
                    app_dir = self._get_app_output_dir(app)
                    fs_utils.destroy_dir_files(app_dir)
        return False

    def _static_analyze_app(self, app: App, move_files_when_saving=False):
        self.logger.info(f"Analyzing app: {app.get_base_pkg()}")
        success_count = len(self.static_analyzers)
        for static_analyzer in self.static_analyzers:
            start_time = datetime.now()
            tb_exception = None
            success = False
            try:
                # execution of static analyzer
                static_analyzer.analyze_app(app)
                success = True
                success_count = success_count - 1
                # this check must be done after the first static analyzer execution
                if self._is_app_already_analyzed(app=app, clean_unfinished_dir=True):
                    if not self.append_to_existing:
                        raise RuntimeError(
                            f"App dest dir already exists: {app.get_package_name()}. Quiting before it gets overwritten")
                    else:
                        self.logger.info(f"App: {app.get_base_pkg()} has already been analyzed")
                        return True
            except Exception:
                tb_exception = traceback.format_exc()
                self.logger.debug(tb_exception)
            end_time = datetime.now()
            total_secs = (end_time - start_time).total_seconds()
            if not app.is_variant():
                variant_flag = 0
                variant_flag_str = "original"
                variant_levels = 0
                variant_levels_str = "original"
            else:
                variant_flag = app.get_variant_bin_features()
                variant_flag_str = app.get_variant_feature_labels()
                variant_levels = app.get_variant_bin_levels()
                variant_levels_str = app.get_variant_level_labels()
            self.instrumate_log.log_static_analyzer_execution(static_analyzer.get_name(), app.get_package_name(),
                                                              app.get_base_pkg(), app.get_app_id(),
                                                              app.get_app_version_name(), variant_flag,
                                                              variant_flag_str,
                                                              variant_levels,
                                                              variant_levels_str,
                                                              success,
                                                              tb_exception, total_secs)
        if success_count == 0:
            app_dir = self._get_app_output_dir(app)
            app.save_to_dir(app_dir, move=move_files_when_saving)
            for static_analyzer in self.static_analyzers:
                static_analyzer.save_analysis(app)
            app.free_memory()
        gc.collect()
        return success_count == 0

    def _static_analyze_apps(self, list_to_analyze, move_files_when_saving=False):
        total_apps = len(list_to_analyze)
        total_time = 0
        current_app_index = 0
        self.logger.debug(f"Running {len(self.static_analyzers)} static analyzers on {total_apps} apps")
        okay_apps = set()
        not_okay_apps = set(list_to_analyze)
        for app in list_to_analyze:
            call_start_time = time.time()
            success = self._static_analyze_app(app, move_files_when_saving=move_files_when_saving)
            okay_apps.add(app)
            not_okay_apps.remove(app)
            call_end_time = time.time()
            call_duration = call_end_time - call_start_time
            total_time = total_time + call_duration
            time_spent_so_far = total_time
            average_time = time_spent_so_far / (current_app_index + 1)
            estimated_time_to_finish = average_time * (total_apps - (current_app_index + 1))
            self.logger.info("static analyzers: process perspective---------------------------")
            self.logger.info(
                f"App {current_app_index}: {app.get_package_name()} finished; Time so far {time_spent_so_far} seconds. "
                f"Time to finish {estimated_time_to_finish}s or {estimated_time_to_finish / 60.0} "
                f"minutes or {estimated_time_to_finish / (60.0 * 60.0)} hours. "
                f"Avg time per item {average_time} seconds")
            current_app_index = current_app_index + 1
        self.logger.debug(f"From {len(list_to_analyze)} apps to analzye {len(not_okay_apps)} failed")
        return okay_apps, not_okay_apps

    def _get_app_output_dir(self, app: App):
        variant_label = "original" if not app.is_variant() else "-".join(
            app.get_variant_feature_labels() + app.get_variant_level_labels())
        variant_maker_tag = "" if not app.is_variant() else "_" + app.get_variant_tag()
        app_parent_pkg = f"{app.get_package_name()}"
        app_dir = f"{app.get_package_name()}-{app.get_app_version_code()}_{variant_label}{variant_maker_tag}"
        app_output_dir = os.path.join(os.path.join(self.output_dir, app_parent_pkg), app_dir)
        return app_output_dir

    def _make_app_variants_for_spec(self, base_app: App, variant_spec: AppVariant):
        app_variants = []
        maker: VariantMaker
        input_app = base_app
        input_spec = variant_spec
        for maker in self.variant_makers:
            start_time = datetime.now()
            success = False
            try:
                self.logger.debug(f"Runing variant maker {maker.name}")
                if not maker.can_make(input_app, input_spec):
                    self.logger.debug(
                        f"{maker.name} can't make variant {input_spec.get_bin_features()} {str(input_spec.get_feature_labels())}/levels {str(input_spec.get_level_labels())} for app {input_app.get_package_name()}")
                    continue
                self.logger.debug(
                    f"{maker.name} is building variant {input_spec.get_bin_features()} {str(input_spec.get_feature_labels())}/levels {str(input_spec.get_level_labels())} for app {input_app.get_package_name()}")
                output_app = maker.make_variant(input_app=input_app, input_spec=input_spec)
                success = True
                self._static_analyze_app(output_app, move_files_when_saving=True)
                app_variants.append(output_app)
                self.logger.debug("success")
            except Exception:
                self.logger.debug(
                    f"{maker.name} failed to build variant {input_spec.get_bin_features()} {str(input_spec.get_feature_labels())}/levels {str(input_spec.get_level_labels())} for app {input_app.get_package_name()}")
                tb_exception = traceback.format_exc()
                self.logger.debug(tb_exception)
            end_time = datetime.now()
            total_secs = end_time - start_time
            total_secs = total_secs.total_seconds()
            self.logger.info(f"Variant maker {maker.name} took {total_secs} seconds")

        return app_variants

    def _make_app_variants(self, base_app: App):
        app_variants = []
        specs = create_variant_specifications(modify_manifest=self.specs_modify_manifest,
                                              modify_resources=self.specs_modify_resources,
                                              modify_behaviour=self.specs_modify_behaviour,
                                              behaviour_androlog=self.specs_androlog,
                                              behaviour_acvtool=self.specs_acvtool,
                                              behaviour_aspectj=self.specs_aspectj,
                                              behaviour_fridagadget=self.specs_fridagadget,
                                              behaviour_imcoverage=self.specs_imcoverage)
        for spec in specs:
            variants_for_spec = self._make_app_variants_for_spec(base_app=base_app, variant_spec=spec)
            app_variants = app_variants + variants_for_spec
        return app_variants

    def make_variants(self):
        okay_original_apps, not_okay_original_apps = self._static_analyze_apps(self.original_apps)
        if len(not_okay_original_apps) > 0:
            failed_apps = ", ".join([item.get_package_name() for item in not_okay_original_apps])
            self.logger.warning(f"Apps that failed during the static analysis phase: {failed_apps}")
        current_app_index = 0
        total_apps = len(okay_original_apps)
        start_time = time.time()
        total_time = 0
        total_variants = 0
        for app in okay_original_apps:
            call_start_time = time.time()
            variants = self._make_app_variants(base_app=app)
            total_variants += len(variants)
            call_end_time = time.time()
            call_duration = call_end_time - call_start_time
            total_time = total_time + call_duration
            time_spent_so_far = total_time
            average_time = time_spent_so_far / (current_app_index + 1)
            estimated_time_to_finish = average_time * (total_apps - (current_app_index + 1))
            self.logger.info(
                f"app: {app.get_package_name()} with {len(app.get_split_pkgs())} splits produced {len(variants)} variants")
            self.logger.info("Variant makers: process perspective---------------------------")
            self.logger.info(
                f"App {current_app_index}: {app.get_package_name()} finished; Time so far {time_spent_so_far} seconds. "
                f"Time to finish {estimated_time_to_finish}s or {estimated_time_to_finish / 60.0} "
                f"minutes or {estimated_time_to_finish / (60.0 * 60.0)} hours. "
                f"Avg time per item {average_time} seconds")
            current_app_index = current_app_index + 1
        self.instrumate_log.close_logs()
        self.logger.info("end")
        return total_variants


def main():
    import os
    fs_utils.destroy_dir_files('.\\output\\instrumate\\')
    fs_utils.destroy_dir_files(".\\tmp\\")
    app1 = App(apk_base_path="./input/apk/whatsapp.apk")
    base_pkg = "I:\\git\\forensicmate-static-analysis\\input\\apk\\merge"
    app2 = App(apk_base_path=os.path.join(base_pkg, 'br.com.brainweb.ifood.apk'),
               extra_split_pkgs=[os.path.join(base_pkg, 'br.com.brainweb.ifood-split-1.apk'),
                                 os.path.join(base_pkg, 'br.com.brainweb.ifood-split-2.apk'),
                                 os.path.join(base_pkg, 'br.com.brainweb.ifood-split-3.apk')])
    app3 = App(apk_base_path="./input/apk/calendar.apk")
    app4 = App(apk_base_path=".\\input\\apk\\com.forensicmate.referenceapp.mini.apk")
    app5 = App(apk_base_path=".\\input\\apk\\com.taxis99-base.apk",
               extra_split_pkgs=[".\\input\\apk\\com.taxis99-split-0.apk",
                                 ".\\input\\apk\\com.taxis99-split-1.apk"]
               )
    app6 = App(apk_base_path=".\\input\\apk\\sdk21-droidmate.apk")
    app7 = App(apk_base_path=".\\input\\apk\\cryptoapp.apk")
    base_pkg = '.\\input\\apk\\caixa\\'
    app8 = App(apk_base_path=os.path.join(base_pkg, 'br.com.gabba.Caixa.apk'),
               extra_split_pkgs=[os.path.join(base_pkg, 'br.com.gabba.Caixa-split-1.apk'),
                                 os.path.join(base_pkg, 'br.com.gabba.Caixa-split-2.apk'),
                                 os.path.join(base_pkg, 'br.com.gabba.Caixa-split-3.apk')])
    original_apps = [app8]  # [app1, app2, app3, app4, app5, app6]  # [app1, app2]
    from pymate.instrumate.static_analyzers.AndroguardApkAnalyzer import AndroguardApkAnalyzer
    static_analyzers = [AndroguardApkAnalyzer(),
                        # AndroguardCallGraphAnalyzer(tmp_dir=".\\tmp\\"),
                        # AndroguardDEXAnalyzer(tmp_dir=".\\tmp\\"),
                        # TikaMimeTypeAnalyzer(tmp_dir=".\\tmp\\", tools_dir=".\\tools\\misc")
                        ]
    variant_makers = [
        # GenericApkToolRepackager(),
        # RepackagerByAcvTool(),
        RepackagerByAndrolog(),
        # RepackagerByDroidfax(),
        # RepackagerByRVAndroid(),
        # RepackagerByCOSMO()
    ]
    instrumate = InstruMate(
        tmp_dir=".\\tmp\\",
        tools_dir=".\\tools\\",
        output_dir='.\\output\\instrumate\\',
        original_apps=original_apps,
        static_analyzers=static_analyzers,
        variant_makers=variant_makers,
        append_to_existing=True,
        jdk8_path="C:\\Program Files\\Java\\jdk1.8.0_251",
        jdk_path="C:\\Program Files\\Java\\jdk-17.0.11"
    )
    instrumate.make_variants()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)
    main()
