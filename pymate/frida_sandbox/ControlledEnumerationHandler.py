from pymate.frida_sandbox.MessageHandler import MessageHandler
from pymate.frida_sandbox.CSVMessageHandler import CSVMessageHandler
from pymate.frida_sandbox.JsonToColumnsConverter import ModuleConverter
from pymate.frida_sandbox.SandboxStateCollector import SandboxStateCollector

ENUMERATION_THRESHOLD = 1


class ControlledEnumerationHandler(MessageHandler):
    def __init__(self, base_dir, sandbox_state_collector: SandboxStateCollector):
        self.csv_msg_handler = CSVMessageHandler(base_dir=base_dir, handled_msg_type="MODULE_ENUMERATION",
                                                 columns_converter=ModuleConverter())
        self.sandbox_state_collector = sandbox_state_collector
        self.observed_loaded_classes = 0
        self.observed_loaded_modules = 0
        self.observed_loaded_modules_with_exports = 0
        self.finished = False

    def can_handle(self, message_type):
        return self.csv_msg_handler.can_handle(message_type)

    def handle_message(self, message_type, message):
        if not self.finished:
            self.csv_msg_handler.handle_message(message_type, message)
            if self.has_reached_observations():
                self.finished = True
                self.csv_msg_handler.stop()

    def has_reached_observations(self):
        qtd_cls = self.sandbox_state_collector.get_observed_loaded_classes() - self.observed_loaded_classes
        qtd_exports = self.sandbox_state_collector.get_observed_loaded_modules_with_exports() - self.observed_loaded_modules_with_exports
        qtd_modules = self.sandbox_state_collector.get_observed_loaded_modules() - self.observed_loaded_modules
        if qtd_cls >= ENUMERATION_THRESHOLD and qtd_exports >= ENUMERATION_THRESHOLD and qtd_modules >= ENUMERATION_THRESHOLD:
            return True
        return False

    def stop(self):
        self.csv_msg_handler.stop()
