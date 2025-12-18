import argparse
import logging
import os
import time

from dotenv import load_dotenv

from pymate.MateConfig import DEFAULT_INPUT_CFG_DIR, DEFAULT_TMP_DIR, \
    DEFAULT_OUTPUT_DIR, DEFAULT_TOOLS_DIR
from pymate.accessories import DeviceAppsDownloader
from pymate.common import App, LEVEL_LABELS, VARIANT_LEVEL_MODIFY_MANIFEST, VARIANT_LEVEL_MODIFY_RESOURCES, \
    VARIANT_LEVEL_MODIFY_BEHAVIOUR
from pymate.device_link import DevicePool
from pymate.instrumate import InstruMate, DEFAULT_MAKERS, DEFAULT_ANALYZERS, STATIC_ANALYZERS, parse_variant_makers
from pymate.instrumate.instrumate_checker import InstrumateCheckerManager
from pymate.accessories.create_database import CreateDatabase
from pymate.utils import fs_utils, utils

load_dotenv()

MODE_ANALYZE = "analyze"
MODE_INSTRUMATE = "instrumate"
MODE_INSTALL_GOOGLE = "install_from_gp"
MODE_DOWNLOAD_DEVICE_APPS = "download_device_apps"
MODE_DEVICE_APP_DOWNLOADER = "device_app_downloader"
MODE_BASELINE_CREATION = "baseline"
MODE_HEALTH_CHECK = "healthcheck"
MODE_CREATE_DATABASE = "create_database"
MODES = [MODE_INSTALL_GOOGLE, MODE_DOWNLOAD_DEVICE_APPS, MODE_ANALYZE, MODE_INSTRUMATE, MODE_HEALTH_CHECK,
         MODE_CREATE_DATABASE]
DEFAULT_LEVELS = [LEVEL_LABELS[key] for key in LEVEL_LABELS]


def list_apps_from_dir(base_dir):
    apps = []
    try:
        with os.scandir(base_dir) as entries:
            for entry in entries:
                if entry.is_file() and fs_utils.get_file_extension(entry.path) == '.apk':
                    apps.append(App(apk_base_path=entry.path))
                elif entry.is_dir():
                    apk_items = fs_utils.list_files(directory_path=entry.path, extension="apk")
                    base = [apk_item for apk_item in apk_items if "base.apk" in apk_item][0]
                    splits = [apk_item for apk_item in apk_items if apk_item != base]
                    apps.append(App(apk_base_path=base, extra_split_pkgs=splits))
    except FileNotFoundError:
        raise RuntimeError(f"The directory {base_dir} does not exist.")
    except PermissionError:
        raise RuntimeError(f"Permission denied for accessing {base_dir}.")
    return apps


def list_apps_from_structured_dir(base_dir, skip_originals=False):
    apps = []
    try:
        with os.scandir(base_dir) as entries:
            for entry in entries:
                if entry.is_dir():
                    with os.scandir(entry.path) as variants_entries:
                        for v_entry in variants_entries:
                            if v_entry.is_dir():
                                installers_dir = os.path.join(v_entry.path, "installers")
                                app_json_file = os.path.join(v_entry.path, "app.json")
                                has_installers_dir = os.path.exists(installers_dir)
                                has_json_file = os.path.exists(app_json_file)
                                if has_json_file and has_installers_dir:
                                    app = App.load_from_dir(v_entry.path)
                                    if skip_originals:
                                        if app.is_variant():
                                            apps.append(app)
                                    else:
                                        apps.append(app)
                                else:
                                    print(f"can't load app from dir {v_entry.path}")
    except FileNotFoundError:
        raise RuntimeError(f"The directory {base_dir} does not exist.")
    except PermissionError:
        raise RuntimeError(f"Permission denied for accessing {base_dir}.")
    return apps


def parse_args():
    parser = argparse.ArgumentParser(description="Start ForensicMate to analyze an Android app.",
                                     formatter_class=argparse.RawTextHelpFormatter)
    # generic options
    parser.add_argument("-m", action="store", dest="mode", required=True,
                        help=f"Mode of operation. One of: {', '.join(MODES)}")
    parser.add_argument("-d", action="store", dest="device_serial", required=False,
                        help="The serial number of target device (use `adb devices` to find)")
    parser.add_argument("-a", action="store", dest="apk_path", required=False,
                        help="The file path to target APK")
    parser.add_argument("-A", action="store", dest="apk_dir", required=False,
                        help="The dir with APKs")
    parser.add_argument("-AS", action="store", dest="apk_dir_structured", required=False,
                        help="The dir with APKs - Structured dir (instrumented or analyzed)")
    parser.add_argument("-f", action="store", dest="app_pkg", required=False,
                        help="The app package ID")
    parser.add_argument("-F", action="store", dest="app_pkgs", required=False,
                        help="Comma separated list of packages or a file with the list of packages")
    parser.add_argument("-o", action="store", dest="output_dir", default=DEFAULT_OUTPUT_DIR, required=False,
                        help="output directory")

    # instrumate options
    parser.add_argument("-variant_makers", action="store", dest="variant_makers", default=",".join(DEFAULT_MAKERS),
                        required=False,
                        help="List of variant makers")
    parser.add_argument("-static_analyzers", action="store", dest="static_analyzers",
                        default=",".join(DEFAULT_ANALYZERS), required=False,
                        help="List of static analyzers")
    parser.add_argument("-variant_specs", action="store", dest="variant_specs",
                        default=",".join(DEFAULT_LEVELS), required=False,
                        help="List of static analyzers")

    parser.add_argument("-cfg_dir", action="store", dest="config_dir", default=DEFAULT_INPUT_CFG_DIR,
                        help="Input configuration")
    parser.add_argument("-tmp_dir", action="store", dest="tmp_dir", default=DEFAULT_TMP_DIR, required=False,
                        help="Tmp dir. Default is %s" % DEFAULT_TMP_DIR)
    parser.add_argument("-tools_dir", action="store", dest="tools_dir", default=DEFAULT_TOOLS_DIR, required=False,
                        help="Tools dir. Default is %s" % DEFAULT_TOOLS_DIR)
    parser.add_argument("-unfinished_mode", action="store", dest="unfinished_mode", default=None, required=False,
                        help="Any mode that did not finish %s" % ', '.join(MODES))
    parser.add_argument("--debug", action="store_true", dest="debug_mode",
                        help="Run in debug mode (dump debug messages).")
    parser.add_argument("--force", action="store_true", dest="force",
                        default=False, help="Destroy existing files")
    parser.add_argument("--all-devices-on-pool", action="store_true", dest="all_devices_on_pool",
                        default=True, help="Use all active devices on pool")
    parser.add_argument("-emulator_restore_snapshot", action="store", dest="emulator_restore_snapshot", default=None,
                        required=False,
                        help="Restore point to the emulator. Default is None.")
    parser.add_argument("-health_check_extra_attempts", action="store", dest="health_check_extra_attempts", default=3,
                        required=False,
                        help="Attempts extra N times failed apps before quitting. Default is 2 extra attempts.")
    parser.add_argument("-health_check_attempts_per_app", action="store", dest="health_check_attempts_per_app",
                        default=3,
                        required=False,
                        help="Attempts per app. Useful for non stable AVD environments.")
    parser.add_argument("--reboot-device-on-pool-release", action="store_true", dest="reboot_device_on_pool_release",
                        default=False, help="Reboot device before using (before released by the pool)")
    parser.add_argument("--skip_originals", action="store_true", dest="skip_originals",
                        default=False, help="Skip original apps from health checking")
    parser.add_argument("--recycle_emulator_with_kill", action="store_true", dest="recycle_emulator_with_kill",
                        default=False, help="When the device is returned to the pool it is killed. "
                                            "The system should restart it and the pool "
                                            "will wait for it to be available.")
    parser.add_argument("--hc_capture_failed_apps", action="store_true", dest="hc_capture_failed_apps",
                        default=False, help="During health check, capture logcat and view state from failed apps")
    parser.add_argument("--continue", action="store_true", dest="continue_previous",
                        default=False, help="Keep existing files and continue previous analysis")

    options = parser.parse_args()
    return options


def main():
    opts = parse_args()
    logging.basicConfig(level=logging.DEBUG if opts.debug_mode else logging.INFO)
    pkg_ids = []
    start_apps_load_time = time.time()
    print(f"Loading apps...")
    apps = []
    temp_apk_dir = opts.apk_dir if opts.apk_dir is not None else opts.apk_dir_structured
    if opts.output_dir is not None and temp_apk_dir is not None:
        if (opts.output_dir == temp_apk_dir
                or opts.output_dir == temp_apk_dir
                or opts.output_dir.rstrip(os.path.sep) == temp_apk_dir.rstrip(os.path.sep)):
            print(f"Output dir {opts.output_dir} seems to be also the input... check arguments...")
            exit(0)
    if opts.apk_path is not None:
        apps.append(App(apk_base_path=opts.apk_path))
    if opts.apk_dir is not None:
        if not os.path.exists(opts.apk_dir):
            raise RuntimeError(f"Apk dir does not exists: {opts.apk_dir}")
        apps.extend(list_apps_from_dir(opts.apk_dir))
    if opts.apk_dir_structured is not None:
        if not os.path.exists(opts.apk_dir_structured):
            raise RuntimeError(f"Apk dir does not exists: {opts.apk_dir_structured}")
        apps.extend(list_apps_from_structured_dir(opts.apk_dir_structured, skip_originals=opts.skip_originals))
    if opts.app_pkg is not None:
        if opts.app_pkg.endswith('.apk'):
            apps.append(App(apk_base_path=opts.app_pkg))
        else:
            pkg_ids.append(opts.app_pkg)
    if opts.app_pkgs is not None:
        if os.path.exists(opts.app_pkgs):
            lines = fs_utils.read_file_lines(opts.app_pkgs)
            pkg_ids.extend(lines)
        else:
            splited = opts.app_pkgs.split(',')
            pkg_ids.extend(splited)
    print(f"Apps loading took {time.time() - start_apps_load_time}s")
    mode = opts.mode
    config_dir = opts.config_dir
    tmp_dir = opts.tmp_dir
    output_dir = opts.output_dir
    tools_dir = opts.tools_dir
    force_delete = opts.force
    continue_previous = opts.continue_previous
    java_home, jdk8_home = utils.find_java_and_jdk8()
    if mode != MODE_CREATE_DATABASE:
        if os.path.exists(output_dir):
            if not force_delete and not continue_previous:
                raise RuntimeError(f"Output dir already exists {output_dir}. Use option --force to overwrite it")
            if force_delete:
                fs_utils.destroy_dir_files(output_dir)
                os.makedirs(output_dir)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    if os.path.exists(tmp_dir):
        if force_delete:
            fs_utils.destroy_dir_files(tmp_dir)
    else:
        os.makedirs(tmp_dir)

    if not os.path.exists(config_dir):
        raise RuntimeError("Config dir does not exists")

    # if mode == MODE_INSTALL_GOOGLE:
    #     device_link = DeviceLink()
    #     device_link.configure_device(serialno=opts.device_serial)
    #     gp_installer = GooglePlayInstaller(pkg_ids=pkg_ids, uninstall_installed=False, update_version=True,
    #                                        open_app=False, gui_timeout=10, install_timeout=10,
    #                                        retry_failed_apps_count=3, device_link=device_link)
    #     gp_installer.install_pkgs()
    #
    # if mode == MODE_DOWNLOAD_DEVICE_APPS:
    #     device_link = DeviceLink()
    #     device_link.configure_device(serialno=opts.device_serial)
    #     apps_downloader = DeviceAppsDownloader(device_link=device_link, download_pkg_ids=pkg_ids, output_dir=output_dir)
    #     apps_downloader.download_pkgs()

    if mode == MODE_DEVICE_APP_DOWNLOADER:
        devices_serial_no = None if opts.all_devices_on_pool else [opts.device_serial.split(',')]
        device_pool = DevicePool(serial_numbers=devices_serial_no,
                                 emulator_restore_snapshot=opts.emulator_restore_snapshot,
                                 reboot_device_on_release=opts.reboot_device_on_pool_release,
                                 recycle_emulator_with_kill=opts.recycle_emulator_with_kill)
        apps_downloader = DeviceAppsDownloader(apps=pkg_ids, device_pool=device_pool, output_dir=output_dir,
                                               config_dir=config_dir)
        apps_downloader.execute()

    if mode == MODE_ANALYZE:
        static_analyzers = [STATIC_ANALYZERS[key] for key in opts.static_analyzers.split(',')]
        variant_makers = []
        instrumate = InstruMate(config_dir=config_dir, tmp_dir=tmp_dir, output_dir=output_dir, tools_dir=tools_dir,
                                original_apps=apps,
                                static_analyzers=static_analyzers, variant_makers=variant_makers,
                                append_to_existing=continue_previous, jdk8_path=jdk8_home, jdk_path=java_home)
        instrumate.make_variants()

    if mode == MODE_INSTRUMATE:
        print(f"static analyzers: {opts.static_analyzers}")
        print(f"variant makers: {opts.variant_makers}")
        print(f"spec levels: {opts.variant_specs}")
        static_analyzers = [STATIC_ANALYZERS[key] for key in opts.static_analyzers.split(',')]
        variant_makers = parse_variant_makers(opts.variant_makers.split(','))
        spec_levels = opts.variant_specs.split(',')
        specs_modify_manifest = LEVEL_LABELS[VARIANT_LEVEL_MODIFY_MANIFEST] in spec_levels
        specs_modify_resources = LEVEL_LABELS[VARIANT_LEVEL_MODIFY_RESOURCES] in spec_levels
        specs_modify_behaviour = LEVEL_LABELS[VARIANT_LEVEL_MODIFY_BEHAVIOUR] in spec_levels
        specs_androlog = "androlog" in spec_levels
        specs_acvtool = "acvtool" in spec_levels
        specs_aspectj = "aspectj" in spec_levels
        specs_fridagadget = "fridagadget" in spec_levels
        specs_imcoverage = "imcoverage" in spec_levels
        if not specs_androlog and not specs_acvtool and not specs_aspectj and not specs_fridagadget and not specs_imcoverage:
            specs_acvtool = True
            specs_aspectj = True
            specs_androlog = True
            specs_fridagadget = True
            specs_imcoverage = True
        instrumate = InstruMate(config_dir=config_dir, tmp_dir=tmp_dir, output_dir=output_dir, tools_dir=tools_dir,
                                original_apps=apps,
                                static_analyzers=static_analyzers, variant_makers=variant_makers,
                                append_to_existing=continue_previous, jdk8_path=jdk8_home, jdk_path=java_home,
                                specs_modify_manifest=specs_modify_manifest,
                                specs_modify_resources=specs_modify_resources,
                                specs_modify_behaviour=specs_modify_behaviour,
                                specs_androlog=specs_androlog,
                                specs_acvtool=specs_acvtool,
                                specs_aspectj=specs_aspectj,
                                specs_fridagadget=specs_fridagadget,
                                specs_imcoverage=specs_imcoverage
                                )
        instrumate.make_variants()

    if mode == MODE_HEALTH_CHECK or mode == MODE_BASELINE_CREATION:
        devices_serial_no = None if opts.all_devices_on_pool else [opts.device_serial.split(',')]
        device_pool = DevicePool(serial_numbers=devices_serial_no,
                                 emulator_restore_snapshot=opts.emulator_restore_snapshot,
                                 reboot_device_on_release=opts.reboot_device_on_pool_release,
                                 recycle_emulator_with_kill=opts.recycle_emulator_with_kill)
        iterations = 1 if mode == MODE_HEALTH_CHECK else 9
        print(f"Mode: {mode}, iterations: {iterations}, capture failed apps: {opts.hc_capture_failed_apps}")
        checker_manager = InstrumateCheckerManager(config_dir=config_dir, output_dir=output_dir,
                                                   device_pool=device_pool, apps=apps,
                                                   iterations=iterations, monkey_events_per_iteration=500,
                                                   append_to_existing=False,
                                                   capture_failed_apps=opts.hc_capture_failed_apps,
                                                   extra_attempts_for_failed_apps=int(opts.health_check_extra_attempts),
                                                   attempts_per_app=int(opts.health_check_attempts_per_app))
        checker_manager.execute()

    if mode == MODE_CREATE_DATABASE:
        unfinished_mode = opts.unfinished_mode
        post_sql_file = None
        database_name = "unfinished_db.db"
        if unfinished_mode is not None:
            if unfinished_mode == MODE_DEVICE_APP_DOWNLOADER:
                post_sql_file = 'apps_downloader_db.sql'
                database_name = "unfinished_apps_downloader.db"
            if unfinished_mode == MODE_HEALTH_CHECK:
                post_sql_file = 'instrumate_checker_db.sql'
                database_name = "unfinished_instrumate_checker.db"
            if unfinished_mode == MODE_INSTRUMATE:
                post_sql_file = 'instrumate_db.sql'
                database_name = "unfinished_instrumate.db"

        sql_post_config_file = os.path.join(config_dir, 'config', post_sql_file)
        create_database = CreateDatabase(log_dir=output_dir, database_name=database_name,
                                         sql_post_config_file=sql_post_config_file)
        create_database.create_database()


if __name__ == "__main__":
    main()
    # apps1 = list_apps_from_dir("I:\\git\\forensicmate-results\\iterations\\5_instrumate-mime-type")
    # apps2 = list_apps_from_structured_dir("I:\\git\\forensicmate-results\\iterations\\327-s1-to-s3\\instrumate-1-of-2")
    # print(f"Loaded apps: {len(apps2)}")
