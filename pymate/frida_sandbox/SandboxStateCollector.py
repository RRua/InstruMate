from pymate.frida_sandbox.MessageHandler import MessageHandler


class SandboxStateCollector(MessageHandler):
    def __init__(self):
        self.observed_loaded_classes = 0
        self.observed_loaded_modules = 0
        self.observed_loaded_modules_with_exports = 0

    def can_handle(self, message_type):
        if message_type == 'INTERNAL_LOGGING':
            return True
        return False

    def handle_message(self, message_type, message):
        level = message["level"]
        message = message["message"]
        if level == "INFO":
            if message == "Enumeration: observing loaded classes":
                self.observed_loaded_classes = self.observed_loaded_classes + 1
            elif message == "Enumeration: observing modules and its exports":
                self.observed_loaded_modules_with_exports = self.observed_loaded_modules_with_exports + 1
            elif message == "Enumeration: observing modules":
                self.observed_loaded_modules = self.observed_loaded_modules + 1

    def stop(self):
        pass

    def get_observed_loaded_modules(self):
        return self.observed_loaded_modules

    def get_observed_loaded_classes(self):
        return self.observed_loaded_classes

    def get_observed_loaded_modules_with_exports(self):
        return self.observed_loaded_modules_with_exports

    def collect(self):
        return {
            "observed_loaded_modules": self.observed_loaded_modules,
            "observed_loaded_classes": self.observed_loaded_classes,
            "observed_loaded_modules_with_exports": self.observed_loaded_modules_with_exports,
        }
