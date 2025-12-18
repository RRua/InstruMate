import sys,os
from pymate.frida_sandbox.FridaConnection import FridaConnection
from pymate.MateConfig import MateConfig
from pymate.Project import Project


def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <action> [arguments...]")
        return
    action = sys.argv[1]
    arguments = sys.argv[2:]
    print("Action:", action)
    print("Arguments:", arguments)
    config = MateConfig("./input/")
    if "--interceptors" in arguments:
        config.run_interceptors = True
    if "--enumerators" in arguments:
        config.run_enumerators = True
    if "--quiet" in arguments:
        config.quiet = True
    config.configure()
    if action == "monitor":
        app_package = arguments[0]
        monitor_path = os.path.join(".", "output", "MONITOR")
        project = Project(monitor_path, app_package, config)
        frida_connection = FridaConnection(project, app_package)
        frida_connection.start()






if __name__ == '__main__':
    main()