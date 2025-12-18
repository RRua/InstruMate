from pymate.frida_sandbox.MessageHandler import MessageHandler
import threading


class LoadedModulesCollector(MessageHandler):
    def __init__(self, clear_on_collect=False):
        self.catalog = {}
        self.lock = threading.Lock()
        self.clear_on_collect = clear_on_collect

    def can_handle(self, message_type):
        if message_type == "MODULE_ENUMERATION":
            return True
        return False

    def handle_message(self, message_type, message):
        module_type = message["module_type"]
        if module_type == "native_module_exports":
            module_type = "native_module"
        module_name = message["module_name"]
        with self.lock:
            if module_type not in self.catalog:
                self.catalog[module_type] = set()
            self.catalog[module_type].add(module_name)

    def stop(self):
        pass

    def collect(self, clear=False):
        ret_val = {}
        with self.lock:
            for key in self.catalog:
                new_set = set(self.catalog[key])
                ret_val[key] = new_set
                if self.clear_on_collect or clear:
                    self.catalog[key].clear()
        return ret_val
