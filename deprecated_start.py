import argparse
import logging
import os

from pymate import MateConfig
from pymate.MateConfig import DEFAULT_INPUT_CFG_DIR, DEFAULT_EVENT_INTERVAL, DEFAULT_TIMEOUT, DEFAULT_TMP_DIR, \
    DEFAULT_OUTPUT_DIR, DEFAULT_TOOLS_DIR
from pymate.device_link import App
from pymate.device_link import DeviceLink
from pymate.device_link import ProcessMonitor
from pymate.device_link import AppBag
from pymate import Project
from dotenv import load_dotenv
from pymate.action_manager.ActionPolicy import ManualPolicy
from pymate.action_manager.telegram_policy.TelegramActionPolicy import TelegramActionPolicy
from pymate.action_manager.autodroid_policy.OpenAIActionPolicy import OpenAIActionPolicy
from pymate.action_manager.input_generator.InputGenerator import RandomInputGenerator
from pymate.action_manager.policy_strategy.PolicyStrategy import MoveNextPolicyStrategy

load_dotenv()

#Note about how to start profiling
#am start -n com.simplemobiletools.calendar.pro/.activities.SplashActivity --start-profiler -S -P /data/local/tmp/log2.trace

POLICIES = {
    ManualPolicy.__name__: ManualPolicy,
    TelegramActionPolicy.__name__: TelegramActionPolicy,
    OpenAIActionPolicy.__name__: OpenAIActionPolicy
}

STRATEGIES = {
    MoveNextPolicyStrategy.__name__: MoveNextPolicyStrategy
}


def list_action_policies():
    return [key for key in POLICIES]


def get_default_action_policy():
    return list_action_policies()[0]


def list_strategies():
    return [key for key in STRATEGIES]


def get_default_strategy():
    return list_strategies()[0]


def create_policies(policy_names):
    policies = []
    for key in policy_names:
        if key in POLICIES:
            cls = POLICIES[key]
            policy_obj = cls()
            policies.append(policy_obj)
        else:
            raise NotImplemented("ActionPolicy not found: %s " % key)
    return policies


INPUT_GENERATORS = {
    RandomInputGenerator.__name__: RandomInputGenerator
}


def list_input_generators():
    return [key for key in INPUT_GENERATORS]


def default_input_generator():
    return list_input_generators()[0]


def create_input_generator(input_generator):
    if input_generator in INPUT_GENERATORS:
        return INPUT_GENERATORS[input_generator]()
    else:
        raise NotImplemented("InputGenerator not found: %s " % input_generator)


def create_strategy(strategy_key, policies):
    if strategy_key in STRATEGIES:
        obj = STRATEGIES[strategy_key](policies)
        return obj
    else:
        raise NotImplemented("Strategy not found: %s " % strategy_key)


def parse_args():
    parser = argparse.ArgumentParser(description="Start ForensicMate to analyze an Android app.",
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-d", action="store", dest="device_serial", required=False,
                        help="The serial number of target device (use `adb devices` to find)")
    parser.add_argument("-a", action="store", dest="apk_path", required=False,
                        help="The file path to target APK")
    parser.add_argument("-A", action="store", dest="apk_dir", required=False,
                        help="The dir with APKs")
    parser.add_argument("-f", action="store", dest="app_pkg", required=False,
                        help="The app package to fork and start")
    parser.add_argument("-F", action="store", dest="app_pkgs", required=False,
                        help="Comma separated list of packages to fork and start")
    parser.add_argument("-p", action="store", dest="policies", required=False,
                        default=get_default_action_policy(),
                        help="Comma separated list of action policies. "
                             "For more then one policy, check max_errors_per_policy for moving to the next."
                             " Ex: " + (','.join(list_action_policies())))
    parser.add_argument("-s", action="store", dest="strategy", required=False,
                        default=get_default_strategy(),
                        help="The name of the policy strategy"
                             " One of: " + (','.join(list_strategies())))
    parser.add_argument("-o", action="store", dest="output_dir", default=DEFAULT_OUTPUT_DIR, required=False,
                        help="output directory")
    parser.add_argument("-i", action="store", dest="input_config_dir", default=DEFAULT_INPUT_CFG_DIR,
                        help="Input configuration")
    parser.add_argument("-t", action="store", dest="task", default="Explore Android app",
                        help="The task that is going to be performed: Create account, send message, etc.")
    parser.add_argument("-event_interval", action="store", dest="event_interval", default=DEFAULT_EVENT_INTERVAL,
                        type=int,
                        help="Interval in seconds between each two events. Default: %d" % DEFAULT_EVENT_INTERVAL)
    parser.add_argument("-timeout", action="store", dest="timeout", default=DEFAULT_TIMEOUT, type=int,
                        help="Timeout in seconds, -1 means unlimited. Default: %d" % DEFAULT_TIMEOUT)
    parser.add_argument("-input-generator", action="store", dest="input_enerator", required=False,
                        default=default_input_generator(),
                        help="One of: " + (','.join(list_input_generators())))
    parser.add_argument("-tmp_dir", action="store", dest="tmp_dir", default=DEFAULT_TMP_DIR, required=False,
                        help="Tmp dir. Default is %s" % DEFAULT_TMP_DIR)
    parser.add_argument("-tools_dir", action="store", dest="tools_dir", default=DEFAULT_TOOLS_DIR, required=False,
                        help="Tools dir. Default is %s" % DEFAULT_TOOLS_DIR)
    parser.add_argument("--debug", action="store_true", dest="debug_mode",
                        help="Run in debug mode (dump debug messages).")
    parser.add_argument("--clean-existing-project", action="store_true", dest="clean_existing_project",
                        default=False, help="Destroy existing files")
    parser.add_argument("--interceptors", action="store_true", dest="run_interceptors", default=True,
                        help="Use frida interceptors. Default: %d" % True)
    parser.add_argument("--enumerators", action="store_true", dest="run_enumerators", default=True,
                        help="Use frida enumerators. Default: %d" % True)
    parser.add_argument("--no_compile_ts", action="store_true", dest="no_compile_ts", default=False, required=False,
                        help="No compilation is done if the output file already exists. Default is %s" % False)
    parser.add_argument("--just_compile_ts", action="store_true", dest="just_compile_ts", default=False, required=False,
                        help="Just compile frida scripts. Default is %s" % False)
    parser.add_argument("--merge-multiple-apks", action="store_true", dest="merge_multiple_apks", required=False,
                        default=False,
                        help="Boolean: to merge splited APKs taken from device")
    parser.add_argument("--set-debuggable-flag", action="store_true", dest="set_debuggable_flag", required=False,
                        default=False,
                        help="Boolean: marks the APK as debuggable (needs repackaging)")
    parser.add_argument("--set-allow-backup-flag", action="store_true", dest="set_allow_backup_flag", required=False,
                        default=False,
                        help="Boolean: marks the APK to allow ADB backups (needs repackaging)")
    parser.add_argument("--install", action="store_true", dest="install", required=False,
                        default=False,
                        help="Will install apps from google play or from the installation package")
    parser.add_argument("--install-remove_existing", action="store_true", dest="install_remove_existing", required=False,
                        default=False,
                        help="Will remove existing installations and install new versions")
    options = parser.parse_args()
    return options


def main():
    opts = parse_args()
    apk_path = opts.apk_path
    pkg_name = opts.app_pkg

    logging.basicConfig(level=logging.DEBUG if opts.debug_mode else logging.INFO)

    config = MateConfig()
    config.configure(
        input_dir=opts.input_config_dir,
        output_dir=opts.output_dir,
        tmp_dir=opts.tmp_dir,
        tools_dir=opts.tools_dir,
        run_interceptors=opts.run_interceptors,
        run_enumerators=opts.run_enumerators,
        timeout=opts.timeout,
        event_interval=opts.event_interval,
        merge_multiple_apks=opts.merge_multiple_apks,
        set_debuggable_flag=opts.set_debuggable_flag,
        set_allow_backup_flag=opts.set_allow_backup_flag
    )
    device_link = DeviceLink()
    device_link.configure_device(serialno=opts.device_serial)

    install_apps = opts.install
    install_apps_remove_existing = opts.install_remove_existing
    single_apk = opts.apk_path
    apk_dir = opts.apk_dir

    single_app_pkg = opts.app_pkg
    multiple_app_pkgs = opts.app_pkgs.split(',')

    # apk_dir: str = None, apk_pkgs = []
    app_bag = AppBag(apk_path=opts.apk_path, apk_dir=opts.apk_dir, apk_pkg=opts.app_pkg,
                     apk_pkgs=opts.app_pkgs.split(','))

    if pkg_name is not None:
        apk_path = device_link.adb_pull_apk(pkg_name=pkg_name, destdir=tmp_dir)
    app = App(apk_path=apk_path)
    print(f"App identified {app.package_name}")
    print(f"App main {app.main_activity}")

    if opts.just_compile_ts:
        exit(0)
    process_monitor = ProcessMonitor(device_link=device_link)
    if not process_monitor.is_frida_running():
        print("Cant find frida process... did you start frida?...")
    else:
        print("Found frida process")
    policies = create_policies(opts.policies.split(','))
    strategy = create_strategy(opts.strategy, policies)
    assert len(policies) > 0
    assert strategy is not None
    project = Project(
        config=config,
        device_link=device_link,
        process_monitor=process_monitor,
        app=app,
        task=opts.task,
        policy_strategy=strategy,
        destroy_existing_files=opts.clean_existing_project)
    project.save_project()
    project.start()


if __name__ == "__main__":
    main()
